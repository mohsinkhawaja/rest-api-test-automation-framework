from threading import RLock
from typing import Protocol
from uuid import UUID, uuid4

from .contracts import Cart, CartInput, CartItem, Product, ProductInput, ProductPage


class DomainError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class ProductSnapshots(Protocol):
    def snapshot(self, product_ids: list[UUID]) -> dict[UUID, Product]: ...


class Catalog:
    def __init__(self):
        self._products: dict[UUID, Product] = {}
        self._skus: dict[str, UUID] = {}
        self._lock = RLock()

    def create(self, data: ProductInput) -> Product:
        with self._lock:
            self._check_sku(data.sku)
            product = Product(id=uuid4(), **data.model_dump())
            self._products[product.id] = product
            self._skus[product.sku] = product.id
            return product

    def read(self, product_id: UUID) -> Product:
        with self._lock:
            try:
                return self._products[product_id]
            except KeyError:
                raise DomainError("product_not_found", "Product does not exist") from None

    def page(self, offset: int, limit: int) -> ProductPage:
        with self._lock:
            products = list(self._products.values())
        return ProductPage(
            items=products[offset : offset + limit],
            total=len(products),
            offset=offset,
            limit=limit,
        )

    def replace(self, product_id: UUID, data: ProductInput) -> Product:
        with self._lock:
            old = self.read(product_id)
            self._check_sku(data.sku, product_id)
            updated = Product(id=product_id, **data.model_dump())
            self._products[product_id] = updated
            del self._skus[old.sku]
            self._skus[updated.sku] = product_id
            return updated

    def delete(self, product_id: UUID) -> None:
        with self._lock:
            product = self.read(product_id)
            del self._products[product_id]
            del self._skus[product.sku]

    def snapshot(self, product_ids: list[UUID]) -> dict[UUID, Product]:
        with self._lock:
            return {product_id: self.read(product_id) for product_id in product_ids}

    def _check_sku(self, sku: str, product_id: UUID | None = None) -> None:
        existing = self._skus.get(sku)
        if existing is not None and existing != product_id:
            raise DomainError("duplicate_sku", "SKU is already in use")


class Carts:
    def __init__(self, catalog: ProductSnapshots):
        self._catalog = catalog
        self._carts: dict[UUID, Cart] = {}
        self._lock = RLock()

    def create(self, data: CartInput) -> Cart:
        with self._lock:
            cart = self._price(uuid4(), data)
            self._carts[cart.id] = cart
            return cart

    def read(self, cart_id: UUID) -> Cart:
        with self._lock:
            try:
                return self._carts[cart_id]
            except KeyError:
                raise DomainError("cart_not_found", "Cart does not exist") from None

    def replace(self, cart_id: UUID, data: CartInput) -> Cart:
        with self._lock:
            self.read(cart_id)
            updated = self._price(cart_id, data)
            self._carts[cart_id] = updated
            return updated

    def delete(self, cart_id: UUID) -> None:
        with self._lock:
            self.read(cart_id)
            del self._carts[cart_id]

    def _price(self, cart_id: UUID, data: CartInput) -> Cart:
        ids = [item.product_id for item in data.items]
        if len(ids) != len(set(ids)):
            raise DomainError("duplicate_item", "A product may appear once per cart")
        products = self._catalog.snapshot(ids)
        lines = []
        for item in data.items:
            product = products[item.product_id]
            if item.quantity > product.stock:
                raise DomainError("insufficient_stock", "Requested quantity exceeds stock")
            lines.append(
                CartItem(
                    **item.model_dump(),
                    unit_price_cents=product.price_cents,
                    line_total_cents=product.price_cents * item.quantity,
                )
            )
        return Cart(
            id=cart_id, items=tuple(lines), total_cents=sum(line.line_total_cents for line in lines)
        )
