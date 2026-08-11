from typing import Any


def validate_invoice(
    invoice: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    if not invoice.get("supplier_name"):
        errors.append("Supplier name is required.")

    if not invoice.get("invoice_number"):
        errors.append("Invoice number is required.")

    if not invoice.get("invoice_date"):
        errors.append("Invoice date is required.")

    if not invoice.get("currency_code"):
        errors.append("Currency code is required.")

    if float(invoice.get("gross_amount") or 0) <= 0:
        errors.append(
            "Gross amount must be greater than zero."
        )

    return errors


def validate_totals(
    invoice: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    line_total = sum(
        float(line.get("line_amount") or 0)
        for line in invoice.get("line_items", [])
    )

    tax_amount = float(
        invoice.get("tax_amount") or 0
    )

    freight_amount = float(
        invoice.get("freight_amount") or 0
    )

    misc_charge_amount = float(
        invoice.get("misc_charge_amount") or 0
    )

    discount_amount = float(
        invoice.get("discount_amount") or 0
    )

    calculated_total = (
        line_total
        + tax_amount
        + freight_amount
        + misc_charge_amount
        - discount_amount
    )

    invoice_total = float(
        invoice.get("gross_amount") or 0
    )

    if abs(calculated_total - invoice_total) > 0.01:
        errors.append(
            (
                "Invoice total does not balance. "
                f"Calculated {calculated_total:.2f}, "
                f"invoice total {invoice_total:.2f}."
            )
        )

    return errors