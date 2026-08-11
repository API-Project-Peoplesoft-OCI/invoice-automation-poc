from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
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
    Find an OCI key-value field by its label and return its normalized value.
    If OCI does not provide a normalized value, return the visible text.
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

    This is useful for dates because OCI may normalize an ambiguous date
    differently from how we want to interpret it.
    """
    for field in fields:
        label = field.get("field_label") or {}

        if label.get("name") != field_name:
            continue

        value_data = field.get("field_value") or {}

        text = value_data.get("text")

        if text is None:
            return None

        return str(text).strip()

    return None


def field_confidence(
    fields: list[dict[str, Any]],
    field_name: str,
) -> float | None:
    """
    Return OCI's confidence for a field label.
    """
    for field in fields:
        label = field.get("field_label") or {}

        if label.get("name") == field_name:
            confidence = label.get("confidence")

            if confidence is None:
                return None

            return float(confidence)

    return None


def parse_amount(value: Any) -> Decimal:
    """
    Convert OCI money values into Decimal.

    Handles examples such as:
        2500
        2500.00
        "$2,500.00"
        "$2 500.00"
        "€1 250.50"
        "£500.00"
        "(250.00)"
        "-$250.00"

    Invalid or missing values return Decimal("0").
    """
    if value is None:
        return Decimal("0")

    if isinstance(value, Decimal):
        return value

    if isinstance(value, (int, float)):
        return Decimal(str(value))

    text = str(value).strip()

    if not text:
        return Decimal("0")

    negative_parentheses = (
        text.startswith("(")
        and text.endswith(")")
    )

    text = (
        text.replace("$", "")
        .replace("€", "")
        .replace("£", "")
        .replace(",", "")
        .replace(" ", "")
        .strip()
    )

    if negative_parentheses:
        text = "-" + text[1:-1]

    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return Decimal("0")


def parse_quantity(value: Any) -> Decimal | None:
    """
    Convert a quantity to Decimal.

    Unlike money, an unrecognized quantity returns None instead of zero.
    """
    if value is None:
        return None

    if isinstance(value, Decimal):
        return value

    if isinstance(value, (int, float)):
        return Decimal(str(value))

    text = str(value).strip()

    if not text:
        return None

    text = (
        text.replace(",", "")
        .replace(" ", "")
    )

    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def parse_invoice_date(
    raw_text: str | None,
    *,
    day_first: bool = True,
) -> str | None:
    """
    Convert invoice dates to ISO YYYY-MM-DD.

    Supports formats such as:
        11/02/2019
        11-02-2019
        2019-02-11
        Aug 31, 2013
        August 31, 2013
        Sep 30, 2013

    For numeric ambiguous dates:
        day_first=True means 11/02/2019 -> 2019-02-11
    """
    if not raw_text:
        return None

    raw_text = raw_text.strip()

    formats: list[str] = []

    if day_first:
        formats.extend(
            [
                "%d/%m/%Y",
                "%d-%m-%Y",
                "%d.%m.%Y",
            ]
        )
    else:
        formats.extend(
            [
                "%m/%d/%Y",
                "%m-%d-%Y",
                "%m.%d.%Y",
            ]
        )

    formats.extend(
        [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%b %d, %Y",
            "%B %d, %Y",
            "%b %d %Y",
            "%B %d %Y",
            "%d %b %Y",
            "%d %B %Y",
        ]
    )

    for date_format in formats:
        try:
            parsed = datetime.strptime(
                raw_text,
                date_format,
            )
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

    Note:
    Dollar-sign inference is only suitable for a POC because "$"
    is not uniquely USD.
    """
    all_text = " ".join(
        line.get("text", "")
        for page in raw_result.get("pages", [])
        for line in page.get("lines", [])
    )

    upper_text = all_text.upper()

    # Prefer explicit currency codes if they appear.
    if " USD " in f" {upper_text} ":
        return "USD", False

    if " EUR " in f" {upper_text} ":
        return "EUR", False

    if " GBP " in f" {upper_text} ":
        return "GBP", False

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

    Important:
    OCI may sometimes classify summary tables as invoice line items.
    These values are therefore validated later using arithmetic checks.
    """
    line_items: list[dict[str, Any]] = []

    for field in fields:
        label = field.get("field_label") or {}

        if label.get("name") != "Items":
            continue

        group_value = field.get("field_value") or {}
        oci_items = group_value.get("items") or []

        for line_number, oci_item in enumerate(
            oci_items,
            start=1,
        ):
            item_value = (
                oci_item.get("field_value") or {}
            )

            item_fields = (
                item_value.get("items") or []
            )

            extracted: dict[str, Any] = {}

            for item_field in item_fields:
                item_label = (
                    item_field.get("field_label") or {}
                )

                item_label_name = (
                    item_label.get("name")
                )

                item_field_value = (
                    item_field.get("field_value") or {}
                )

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

            quantity = parse_quantity(
                extracted.get("Quantity")
            )

            unit_price_raw = (
                extracted.get("UnitPrice")
                or extracted.get("UnitPriceAmount")
            )

            line_amount_raw = (
                extracted.get("Amount")
                or extracted.get("Price")
                or extracted.get("LineTotal")
            )

            unit_price = (
                parse_amount(unit_price_raw)
                if unit_price_raw is not None
                else None
            )

            line_amount = parse_amount(
                line_amount_raw
            )

            line_items.append(
                {
                    "line_number": line_number,
                    "item_id": (
                        extracted.get("ProductCode")
                        or extracted.get("ItemId")
                    ),
                    "description": str(description).strip(),
                    "quantity": quantity,
                    "unit_of_measure": (
                        extracted.get("Unit")
                        or extracted.get("UnitOfMeasure")
                    ),
                    "unit_price": unit_price,
                    "line_amount": line_amount,
                    "po_line_number": (
                        extracted.get("POLine")
                        or extracted.get("PurchaseOrderLine")
                    ),
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

    invoice_date_text = field_text(
        fields,
        "InvoiceDate",
    )

    due_date_text = field_text(
        fields,
        "DueDate",
    )

    currency_code, currency_inferred = (
        extract_currency(raw_result)
    )

    normalized = {
        "supplier_name": field_value(
            fields,
            "VendorName",
        ),
        "supplier_tax_id": field_value(
            fields,
            "VendorTaxId",
        ),
        "remit_to_address": field_value(
            fields,
            "VendorAddress",
        ),
        "invoice_number": field_value(
            fields,
            "InvoiceId",
        ),
        "invoice_date": parse_invoice_date(
            invoice_date_text,
            day_first=True,
        ),
        "po_number": field_value(
            fields,
            "PurchaseOrder",
        ),
        "currency_code": currency_code,
        "gross_amount": parse_amount(
            field_value(
                fields,
                "InvoiceTotal",
            )
        ),
        "tax_amount": parse_amount(
            field_value(
                fields,
                "TotalTax",
            )
        ),
        "freight_amount": parse_amount(
            field_value(
                fields,
                "ShippingCost",
            )
        ),
        "discount_amount": parse_amount(
            field_value(
                fields,
                "Discount",
            )
        ),
        "misc_charge_amount": Decimal("0"),
        "payment_terms": field_value(
            fields,
            "PaymentTerm",
        ),
        "due_date": parse_invoice_date(
            due_date_text,
            day_first=True,
        ),
        "line_items": extract_line_items(
            fields
        ),
    }

    review = {
        "requires_review": False,
        "warnings": [],
        "field_metadata": {
            "supplier_name": {
                "confidence": field_confidence(
                    fields,
                    "VendorName",
                ),
                "inferred": False,
            },
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
            "due_date": {
                "confidence": field_confidence(
                    fields,
                    "DueDate",
                ),
                "source_text": due_date_text,
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
            "tax_amount": {
                "confidence": field_confidence(
                    fields,
                    "TotalTax",
                ),
                "inferred": False,
            },
            "currency_code": {
                "confidence": None,
                "inferred": currency_inferred,
            },
        },
    }

    # Currency warning
    if currency_inferred:
        review["warnings"].append(
            "Currency was inferred from the currency symbol."
        )

    # Gross amount confidence
    invoice_total_confidence = (
        field_confidence(
            fields,
            "InvoiceTotal",
        )
    )

    if (
        invoice_total_confidence is not None
        and invoice_total_confidence < 0.85
    ):
        review["warnings"].append(
            "Invoice total has low extraction confidence."
        )

    # Supplier confidence
    supplier_confidence = field_confidence(
        fields,
        "VendorName",
    )

    if (
        supplier_confidence is not None
        and supplier_confidence < 0.85
    ):
        review["warnings"].append(
            "Supplier name has low extraction confidence."
        )

    # Date parsing warnings
    if (
        invoice_date_text
        and normalized["invoice_date"] is None
    ):
        review["warnings"].append(
            (
                "Invoice date was detected but could not "
                f"be parsed: {invoice_date_text}"
            )
        )

    if (
        due_date_text
        and normalized["due_date"] is None
    ):
        review["warnings"].append(
            (
                "Due date was detected but could not "
                f"be parsed: {due_date_text}"
            )
        )

    # Numeric slash dates can be ambiguous.
    if (
        invoice_date_text
        and "/" in invoice_date_text
    ):
        review["warnings"].append(
            "Invoice date format was interpreted as DD/MM/YYYY."
        )

    # Calculate line total
    line_total = sum(
        (
            parse_amount(
                item.get("line_amount")
            )
            for item in normalized["line_items"]
        ),
        Decimal("0"),
    )

    expected_total = (
        line_total
        + normalized["tax_amount"]
        + normalized["freight_amount"]
        + normalized["misc_charge_amount"]
        - normalized["discount_amount"]
    )

    actual_total = normalized["gross_amount"]

    # Arithmetic comparison
    difference = abs(
        expected_total - actual_total
    )

    if (
        normalized["line_items"]
        and difference > Decimal("0.01")
    ):
        review["warnings"].append(
            (
                "Invoice arithmetic does not balance: "
                f"calculated {expected_total:.2f}, "
                f"invoice total {actual_total:.2f}."
            )
        )

    # Validate line items individually
    for item in normalized["line_items"]:
        line_number = item["line_number"]

        if not item.get("description"):
            review["warnings"].append(
                (
                    f"Line {line_number} is missing "
                    "a description."
                )
            )

        quantity = item.get("quantity")
        unit_price = item.get("unit_price")
        line_amount = item.get("line_amount")

        if (
            quantity is not None
            and unit_price is not None
            and line_amount is not None
        ):
            calculated_line_amount = (
                quantity * unit_price
            )

            if (
                abs(
                    calculated_line_amount
                    - line_amount
                )
                > Decimal("0.01")
            ):
                review["warnings"].append(
                    (
                        f"Line {line_number} does not balance: "
                        f"quantity × unit price = "
                        f"{calculated_line_amount:.2f}, "
                        f"line amount = {line_amount:.2f}."
                    )
                )

    # Required fields
    required_fields = [
        "supplier_name",
        "invoice_number",
        "invoice_date",
        "gross_amount",
    ]

    for required_field in required_fields:
        value = normalized.get(
            required_field
        )

        if value in (
            None,
            "",
        ):
            review["warnings"].append(
                (
                    "Required field is missing: "
                    f"{required_field}."
                )
            )

    # Gross amount should normally be positive
    if normalized["gross_amount"] <= Decimal("0"):
        review["warnings"].append(
            "Gross amount is missing or not greater than zero."
        )

    review["requires_review"] = bool(
        review["warnings"]
    )

    return normalized, review