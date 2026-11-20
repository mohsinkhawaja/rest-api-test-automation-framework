from os import environ
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, FastAPI, Query, Request, Response, status
from fastapi.responses import JSONResponse

from .contracts import Cart, CartInput, Product, ProductInput, ProductPage
from .domain import Carts, Catalog, DomainError
from .http_catalog import HttpCatalog


def _service(title: str) -> FastAPI:
    app = FastAPI(title=title, version="1.0.0")
    error_codes = {"product_not_found": 404, "cart_not_found": 404, "catalog_unavailable": 503}

    @app.exception_handler(DomainError)
    async def domain_error(_request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=error_codes.get(exc.code, 409),
            content={"detail": {"code": exc.code, "message": str(exc)}},
        )

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def _catalog_routes(catalog: Catalog) -> APIRouter:
    router = APIRouter(prefix="/api/v1/products", tags=["catalog"])

    @router.post("", status_code=status.HTTP_201_CREATED)
    def create_product(data: ProductInput, response: Response) -> Product:
        product = catalog.create(data)
        response.headers["Location"] = f"/api/v1/products/{product.id}"
        return product

    @router.get("")
    def list_products(
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> ProductPage:
        return catalog.page(offset, limit)

    @router.get("/{product_id}")
    def read_product(product_id: UUID) -> Product:
        return catalog.read(product_id)

    @router.put("/{product_id}")
    def replace_product(product_id: UUID, data: ProductInput) -> Product:
        return catalog.replace(product_id, data)

    @router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_product(product_id: UUID) -> Response:
        catalog.delete(product_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router


def _cart_routes(carts: Carts) -> APIRouter:
    router = APIRouter(prefix="/api/v1/carts", tags=["cart"])

    @router.post("", status_code=status.HTTP_201_CREATED)
    def create_cart(data: CartInput, response: Response) -> Cart:
        cart = carts.create(data)
        response.headers["Location"] = f"/api/v1/carts/{cart.id}"
        return cart

    @router.get("/{cart_id}")
    def read_cart(cart_id: UUID) -> Cart:
        return carts.read(cart_id)

    @router.put("/{cart_id}")
    def replace_cart(cart_id: UUID, data: CartInput) -> Cart:
        return carts.replace(cart_id, data)

    @router.delete("/{cart_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_cart(cart_id: UUID) -> Response:
        carts.delete(cart_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router


def create_app() -> FastAPI:
    app = _service("Mock Commerce API")
    catalog = Catalog()
    app.include_router(_catalog_routes(catalog))
    app.include_router(_cart_routes(Carts(catalog)))
    return app


def create_catalog_app() -> FastAPI:
    app = _service("Catalog service")
    catalog = Catalog()
    app.include_router(_catalog_routes(catalog))

    @app.post("/internal/v1/products/snapshot", include_in_schema=False)
    def snapshot(
        product_ids: Annotated[list[UUID], Body(min_length=1, max_length=10)],
    ) -> list[Product]:
        return list(catalog.snapshot(product_ids).values())

    return app


def create_cart_app(catalog_url: str | None = None) -> FastAPI:
    app = _service("Cart service")
    url = catalog_url or environ.get("QA_CATALOG_URL", "http://127.0.0.1:8001")
    app.include_router(_cart_routes(Carts(HttpCatalog(url))))
    return app


app = create_app()
