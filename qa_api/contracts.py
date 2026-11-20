from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ProductInput(InputModel):
    sku: Annotated[str, Field(min_length=3, max_length=24, pattern="^[A-Z0-9-]+$")]
    name: Annotated[str, Field(min_length=1, max_length=80)]
    price_cents: Annotated[int, Field(strict=True, ge=1, le=1_000_000)]
    stock: Annotated[int, Field(strict=True, ge=0, le=10_000)]

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class Product(ProductInput):
    id: UUID


class CartItemInput(InputModel):
    product_id: UUID
    quantity: Annotated[int, Field(strict=True, ge=1, le=20)]


class CartInput(InputModel):
    items: Annotated[tuple[CartItemInput, ...], Field(min_length=1, max_length=10)]


class CartItem(CartItemInput):
    unit_price_cents: int
    line_total_cents: int


class Cart(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    items: tuple[CartItem, ...]
    total_cents: int


class ProductPage(BaseModel):
    items: list[Product]
    total: int
    offset: int
    limit: int
