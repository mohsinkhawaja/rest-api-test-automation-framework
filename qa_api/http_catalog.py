import json
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener
from uuid import UUID

from pydantic import TypeAdapter, ValidationError

from .contracts import Product
from .domain import DomainError

PRODUCTS = TypeAdapter(list[Product])


class HttpCatalog:
    """Resolve an atomic catalog snapshot through the split service's internal API."""

    def __init__(self, origin: str, timeout: float = 2):
        self._url = origin.rstrip("/") + "/internal/v1/products/snapshot"
        self._timeout = timeout
        self._opener = build_opener(ProxyHandler({}))

    def snapshot(self, product_ids: list[UUID]) -> dict[UUID, Product]:
        request = Request(
            self._url,
            data=json.dumps([str(item) for item in product_ids]).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                products = PRODUCTS.validate_json(response.read())
        except HTTPError as error:
            with error:
                if error.code == 404:
                    raise DomainError("product_not_found", "Product does not exist") from None
            raise DomainError(
                "catalog_unavailable", "Catalog could not supply a snapshot"
            ) from None
        except (URLError, TimeoutError, ValidationError):
            raise DomainError(
                "catalog_unavailable", "Catalog could not supply a snapshot"
            ) from None
        snapshot = {product.id: product for product in products}
        if set(snapshot) != set(product_ids):
            raise DomainError("catalog_unavailable", "Catalog supplied an incomplete snapshot")
        return snapshot
