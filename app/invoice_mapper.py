from __future__ import annotations

from datetime import datetime
from typing import Any


def get_document_fields(
    raw_result: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Return all OCI document fields from all pages.
    """
    fields: list[dict[str, Any]] = []

    for page in raw_result.get("pages", []):
        fields.extend(page.get("document_fields") or [])

    return fields


def field_value(
    fields: list[dict[str, Any]],
    field_name: str,
) -> Any:
    """
    Find an OCI key-value field by its label and return its value.
    """
    for field in fields:
        label = field.get("field_label") or {}

        if label.get("name") != field_name:
            continue

        value_data = field.get("field_value") or {}

        if value_data.get("value") is not None:
            return value_data["value"]

        return value_data.get("text")

    return None


def field_text(
    fields: list[dict[str, Any]],
    field_name: str,
) -> str | None:
    """
    Return the original visible text for a field.
    This is useful for dates because OCI normalization may interpret
    ambiguous dates incorrectly.
    """
    for field in fields:
        label = field.get("field_label") or {}

        if label.get("name") != field_name:
            continue

        value_data = field.get("field_value") or {}
        return value_data.get("text")

    return None


def field_confidence(
    fields: list[dict[str, Any]],
    field_name: str,
) -> float | None:
    """
    Return OCI's confidence for the field label.
    """
    for field in fields:
        label = field.get("field_label") or {}

        if label.get("name") == field_name:
            return label.get("confidence")

    return None


def parse_invoice_date(
    raw_text: str | None,
    *,
    day_first: bool = True,
) -> str | None:
    """
    Convert invoice dates to ISO YYYY-MM-DD.

    For the current POC, day_first=True interprets:
    11/02/2019 as 2019-02-11.
    """
    if not raw_text:
        return None

    raw_text = raw_text.strip()

    formats = (
        ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"]
        if day_first
        else ["%m/%d/%Y", "%m-%d-%Y", "%m.%d.%Y"]
    )

    formats.extend(
        [
            "%Y-%m-%d",
            "%Y/%m/%d",
        ]
    )

    for date_format in formats:
        try:
            parsed = datetime.strptime(raw_text, date_format)
            return parsed.date().isoformat()
        except ValueError:
            continue

    return None


def extract_currency(
    raw_result: dict[str, Any],
) -> tuple[str | None, bool]:
    """
    Infer currency from visible invoice text.

    Returns:
        currency code
        whether the value was inferred
    """
    all_text = " ".join(
        line.get("text", "")
        for page in raw_result.get("pages", [])
        for line in page.get("lines", [])
    )

    if "$" in all_text:
        return "USD", True

    if "€" in all_text:
        return "EUR", True

    if "£" in all_text:
        return "GBP", True

    return None, False


def extract_line_items(
    fields: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Convert OCI's Items LINE_ITEM_GROUP into the application schema.
    """
    line_items: list[dict[str, Any]] = []

    for field in fields:
        label = field.get("field_label") or {}

        if label.get("name") != "Items":
            continue

        group_value = field.get("field_value") or {}
        oci_items = group_value.get("items") or []

        for line_number, oci_item in enumerate(oci_items, start=1):
            item_value = oci_item.get("field_value") or {}
            item_fields = item_value.get("items") or []

            extracted: dict[str, Any] = {}

            for item_field in item_fields:
                item_label = item_field.get("field_label") or {}
                item_label_name = item_label.get("name")

                item_field_value = item_field.get("field_value") or {}

                value = item_field_value.get("value")

                if value is None:
                    value = item_field_value.get("text")

                if item_label_name:
                    extracted[item_label_name] = value

            description = (
                extracted.get("Description")
                or extracted.get("Name")
                or ""
            )

            line_items.append(
                {
                    "line_number": line_number,
                    "item_id": extracted.get("ProductCode"),
                    "description": description,
                    "quantity": extracted.get("Quantity"),
                    "unit_of_measure": extracted.get("Unit"),
                    "unit_price": extracted.get("UnitPrice"),
                    "line_amount": (
                        extracted.get("Amount")
                        or extracted.get("Price")
                        or 0
                    ),
                    "po_line_number": None,
                }
            )

    return line_items


def normalize_invoice(
    raw_result: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Convert the raw OCI result into:
      1. normalized invoice JSON
      2. review metadata
    """
    fields = get_document_fields(raw_result)

    invoice_date_text = field_text(fields, "InvoiceDate")
    due_date_text = field_text(fields, "DueDate")

    currency_code, currency_inferred = extract_currency(raw_result)

    normalized = {
        "supplier_name": field_value(fields, "VendorName"),
        "supplier_tax_id": field_value(fields, "VendorTaxId"),
        "remit_to_address": field_value(fields, "VendorAddress"),
        "invoice_number": field_value(fields, "InvoiceId"),
        "invoice_date": parse_invoice_date(
            invoice_date_text,
            day_first=True,
        ),
        "po_number": field_value(fields, "PurchaseOrder"),
        "currency_code": currency_code,
        "gross_amount": field_value(fields, "InvoiceTotal") or 0,
        "tax_amount": field_value(fields, "TotalTax") or 0,
        "freight_amount": field_value(fields, "ShippingCost") or 0,
        "discount_amount": field_value(fields, "Discount") or 0,
        "misc_charge_amount": 0,
        "payment_terms": field_value(fields, "PaymentTerm"),
        "due_date": parse_invoice_date(
            due_date_text,
            day_first=True,
        ),
        "line_items": extract_line_items(fields),
    }

    review = {
        "requires_review": False,
        "warnings": [],
        "field_metadata": {
            "invoice_number": {
                "confidence": field_confidence(
                    fields,
                    "InvoiceId",
                ),
                "inferred": False,
            },
            "invoice_date": {
                "confidence": field_confidence(
                    fields,
                    "InvoiceDate",
                ),
                "source_text": invoice_date_text,
                "inferred": False,
            },
            "po_number": {
                "confidence": field_confidence(
                    fields,
                    "PurchaseOrder",
                ),
                "inferred": False,
            },
            "gross_amount": {
                "confidence": field_confidence(
                    fields,
                    "InvoiceTotal",
                ),
                "inferred": False,
            },
            "currency_code": {
                "confidence": None,
                "inferred": currency_inferred,
            },
        },
    }

    if currency_inferred:
        review["warnings"].append(
            "Currency was inferred from the currency symbol."
        )

    invoice_total_confidence = field_confidence(
        fields,
        "InvoiceTotal",
    )

    if (
        invoice_total_confidence is not None
        and invoice_total_confidence < 0.85
    ):
        review["warnings"].append(
            "Invoice total has low extraction confidence."
        )

    if invoice_date_text and "/" in invoice_date_text:
        review["warnings"].append(
            "Invoice date format was interpreted as DD/MM/YYYY."
        )

    line_total = sum(
        float(item.get("line_amount") or 0)
        for item in normalized["line_items"]
    )

    expected_total = (
        line_total
        + float(normalized["tax_amount"] or 0)
        + float(normalized["freight_amount"] or 0)
        + float(normalized["misc_charge_amount"] or 0)
        - float(normalized["discount_amount"] or 0)
    )

    actual_total = float(normalized["gross_amount"] or 0)

    if abs(expected_total - actual_total) > 0.01:
        review["warnings"].append(
            (
                "Invoice arithmetic does not balance: "
                f"calculated {expected_total:.2f}, "
                f"invoice total {actual_total:.2f}."
            )
        )

    required_fields = [
        "supplier_name",
        "invoice_number",
        "invoice_date",
        "gross_amount",
    ]

    for required_field in required_fields:
        if not normalized.get(required_field):
            review["warnings"].append(
                f"Required field is missing: {required_field}."
            )

    review["requires_review"] = bool(review["warnings"])

    return normalized, review