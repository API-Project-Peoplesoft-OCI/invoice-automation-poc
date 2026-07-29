import oci
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings
from app.oci_client import OCIInvoiceClient
from app.storage import save_uploaded_invoice


router = APIRouter(
    prefix="/invoices",
    tags=["Invoices"],
)

oci_client = OCIInvoiceClient()


@router.post("/upload")
async def upload_invoice(
    invoice_file: UploadFile = File(...),
):
    try:
        # 1. Save the uploaded invoice locally
        document_id, saved_path = await save_uploaded_invoice(
            invoice_file
        )

        # 2. Upload the invoice to OCI Object Storage
        object_name = oci_client.upload_invoice(
            file_path=saved_path,
            object_name=saved_path.name,
        )

        # 3. Analyze and normalize the invoice
        output_name, final_document = (
            oci_client.analyze_invoice(object_name)
        )

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