from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InvoiceLine(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    line_number: int = Field(
        default=1,
        ge=1,
        description="Sequential invoice line number",
    )

    item_id: Optional[str] = Field(
        default=None,
        max_length=100,
    )

    description: str = Field(
        default="",
        max_length=500,
    )

    quantity: Optional[Decimal] = Field(
        default=None,
        ge=0,
    )

    unit_of_measure: Optional[str] = Field(
        default=None,
        max_length=20,
    )

    unit_price: Optional[Decimal] = Field(
        default=None,
        ge=0,
    )

    line_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
    )

    po_line_number: Optional[int] = Field(
        default=None,
        ge=1,
    )


class Invoice(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    supplier_name: str = Field(
        default="",
        max_length=255,
    )

    supplier_tax_id: Optional[str] = Field(
        default=None,
        max_length=100,
    )

    remit_to_address: Optional[str] = Field(
        default=None,
        max_length=1000,
    )

    invoice_number: str = Field(
        default="",
        max_length=100,
    )

    invoice_date: Optional[date] = None

    po_number: Optional[str] = Field(
        default=None,
        max_length=100,
    )

    currency_code: str = Field(
        default="",
        min_length=0,
        max_length=3,
    )

    gross_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
    )

    tax_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
    )

    freight_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
    )

    discount_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
    )

    misc_charge_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
    )

    payment_terms: Optional[str] = Field(
        default=None,
        max_length=255,
    )

    due_date: Optional[date] = None

    line_items: list[InvoiceLine] = Field(
        default_factory=list,
    )

    @field_validator("currency_code")
    @classmethod
    def normalize_currency_code(cls, value: str) -> str:
        return value.upper()

    @field_validator("due_date")
    @classmethod
    def validate_due_date(
        cls,
        due_date: Optional[date],
    ) -> Optional[date]:
        return due_date