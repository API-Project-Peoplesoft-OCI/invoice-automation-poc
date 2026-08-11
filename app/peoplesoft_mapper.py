from typing import Any


def map_invoice_to_peoplesoft(
    document: dict[str, Any],
) -> dict[str, Any]:
    if document.get("processing_status") != "APPROVED":
        raise ValueError(
            "Only APPROVED invoices can be mapped to PeopleSoft."
        )

    invoice = document["invoice"]

    peoplesoft_payload = {
        "business_unit": None,
        "vendor_id": None,
        "vendor_location": None,

        "invoice_id": invoice.get("invoice_number"),
        "invoice_date": invoice.get("invoice_date"),
        "po_number": invoice.get("po_number"),

        "currency_code": invoice.get("currency_code"),

        "gross_amount": invoice.get("gross_amount"),
        "tax_amount": invoice.get("tax_amount"),
        "freight_amount": invoice.get("freight_amount"),
        "discount_amount": invoice.get("discount_amount"),
        "misc_charge_amount": invoice.get(
            "misc_charge_amount"
        ),

        "payment_terms": invoice.get("payment_terms"),
        "due_date": invoice.get("due_date"),

        "supplier": {
            "name": invoice.get("supplier_name"),
            "tax_id": invoice.get("supplier_tax_id"),
            "remit_to_address": invoice.get(
                "remit_to_address"
            ),
        },

        "lines": [],
    }

    for line in invoice.get("line_items", []):
        peoplesoft_payload["lines"].append(
            {
                "line_number": line.get("line_number"),
                "item_id": line.get("item_id"),
                "description": line.get("description"),
                "quantity": line.get("quantity"),
                "unit_of_measure": line.get(
                    "unit_of_measure"
                ),
                "unit_price": line.get("unit_price"),
                "line_amount": line.get("line_amount"),
                "po_line_number": line.get(
                    "po_line_number"
                ),
            }
        )

    return peoplesoft_payload