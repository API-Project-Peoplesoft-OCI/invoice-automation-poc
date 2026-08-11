import oci

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)

from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
)

from app.config import settings
from app.oci_client import OCIInvoiceClient

from app.storage import (
    load_normalized_invoice,
    save_normalized_invoice,
    save_uploaded_invoice,
)

from app.validator import (
    validate_invoice,
    validate_totals,
)




router = APIRouter(
    prefix="/invoices",
    tags=["Invoices"],
)

oci_client = OCIInvoiceClient()


# ---------------------------------------------------------
# UPLOAD INVOICE
# ---------------------------------------------------------

@router.post("/upload")
async def upload_invoice(
    invoice_file: UploadFile = File(...),
):
    try:
        # 1. Save uploaded invoice locally
        document_id, saved_path = await save_uploaded_invoice(
            invoice_file
        )

        # 2. Upload original invoice to OCI Object Storage
        object_name = oci_client.upload_invoice(
            file_path=saved_path,
            object_name=saved_path.name,
        )

        # 3. Analyze invoice and create normalized JSON
        output_name, final_document = (
            oci_client.analyze_invoice(object_name)
        )

        # 4. Save normalized JSON locally
        save_normalized_invoice(
            document_id,
            final_document,
        )

        # 5. Return processing result
        return {
            "status": final_document["processing_status"],
            "document_id": document_id,
            "original_filename": invoice_file.filename,
            "saved_filename": saved_path.name,
            "oci_input_bucket": settings.input_bucket,
            "oci_input_object": object_name,
            "oci_output_bucket": settings.output_bucket,
            "oci_output_object": output_name,
            "result": final_document,
        }

    except oci.exceptions.ServiceError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "OCI request failed.",
                "oci_status": exc.status,
                "oci_code": exc.code,
                "oci_message": exc.message,
                "request_id": exc.request_id,
            },
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Invoice processing failed: {exc}",
        ) from exc


# ---------------------------------------------------------
# REVIEW INVOICE
# ---------------------------------------------------------

@router.get(
    "/{document_id}/review",
    response_class=HTMLResponse,
)
async def review_invoice(
    request: Request,
    document_id: str,
):
    try:
        document = load_normalized_invoice(
            document_id
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    source_object = document["source"]["object_name"]

    image_url = f"/uploads/{source_object}"

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="review.html",
        context={
            "document": document,
            "image_url": image_url,
        },
    )


# ---------------------------------------------------------
# APPROVE INVOICE
# ---------------------------------------------------------

@router.post("/{document_id}/approve")
async def approve_invoice(
    request: Request,
    document_id: str,

    supplier_name: str = Form(...),
    invoice_number: str = Form(...),
    invoice_date: str = Form(...),

    po_number: str | None = Form(None),
    currency_code: str = Form(...),

    gross_amount: float = Form(...),
    tax_amount: float = Form(0),
    freight_amount: float = Form(0),
    discount_amount: float = Form(0),

    payment_terms: str | None = Form(None),
    due_date: str | None = Form(None),
    remit_to_address: str | None = Form(None),
):
    try:
        document = load_normalized_invoice(
            document_id
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    invoice = document["invoice"]

    # -----------------------------------------------------
    # Update header fields
    # -----------------------------------------------------

    invoice["supplier_name"] = supplier_name.strip()

    invoice["invoice_number"] = invoice_number.strip()

    invoice["invoice_date"] = invoice_date

    invoice["po_number"] = (
        po_number.strip()
        if po_number
        else None
    )

    invoice["currency_code"] = (
        currency_code.strip().upper()
    )

    invoice["gross_amount"] = gross_amount
    invoice["tax_amount"] = tax_amount
    invoice["freight_amount"] = freight_amount
    invoice["discount_amount"] = discount_amount

    invoice["payment_terms"] = (
        payment_terms.strip()
        if payment_terms
        else None
    )

    invoice["due_date"] = (
        due_date
        if due_date
        else None
    )

    invoice["remit_to_address"] = (
        remit_to_address.strip()
        if remit_to_address
        else None
    )

    # -----------------------------------------------------
    # Update line items
    # -----------------------------------------------------

    form_data = await request.form()

    for line in invoice.get("line_items", []):
        line_number = line["line_number"]

        description = form_data.get(
            f"description_{line_number}"
        )

        quantity = form_data.get(
            f"quantity_{line_number}"
        )

        uom = form_data.get(
            f"uom_{line_number}"
        )

        unit_price = form_data.get(
            f"unit_price_{line_number}"
        )

        line_amount = form_data.get(
            f"line_amount_{line_number}"
        )

        line["description"] = (
            description.strip()
            if description
            else ""
        )

        line["quantity"] = (
            float(quantity)
            if quantity
            else None
        )

        line["unit_of_measure"] = (
            uom.strip()
            if uom
            else None
        )

        line["unit_price"] = (
            float(unit_price)
            if unit_price
            else None
        )

        line["line_amount"] = (
            float(line_amount)
            if line_amount
            else 0
        )

    # -----------------------------------------------------
    # Validate corrected invoice
    # -----------------------------------------------------

    errors = (
        validate_invoice(invoice)
        + validate_totals(invoice)
    )

    if errors:
        document["processing_status"] = "REVIEW_REQUIRED"

        document["validation"]["warnings"] = errors

        # Save user's corrections locally even when validation fails
        save_normalized_invoice(
            document_id,
            document,
        )

        # Save corrected REVIEW_REQUIRED version to OCI too
        oci_client.save_normalized_document(
            document_id,
            document,
        )

        # Return user to review screen instead of raw JSON
        return RedirectResponse(
            url=f"/invoices/{document_id}/review",
            status_code=303,
        )

    # -----------------------------------------------------
    # Approval successful
    # -----------------------------------------------------

    document["processing_status"] = "APPROVED"

    document["validation"]["warnings"] = []

    # Save locally
    save_normalized_invoice(
        document_id,
        document,
    )

    # Update same JSON in OCI
    oci_client.save_normalized_document(
        document_id,
        document,
    )

    return RedirectResponse(
        url=f"/invoices/{document_id}/review",
        status_code=303,
    )


# ---------------------------------------------------------
# REJECT INVOICE
# ---------------------------------------------------------

@router.post("/{document_id}/reject")
async def reject_invoice(
    document_id: str,
):
    try:
        document = load_normalized_invoice(
            document_id
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    document["processing_status"] = "REJECTED"

    document["validation"]["warnings"] = [
        "Invoice was rejected during manual review."
    ]

    # Save rejected state locally
    save_normalized_invoice(
        document_id,
        document,
    )

    # Save rejected state to same OCI JSON
    oci_client.save_normalized_document(
        document_id,
        document,
    )

    return RedirectResponse(
        url=f"/invoices/{document_id}/review",
        status_code=303,
    )