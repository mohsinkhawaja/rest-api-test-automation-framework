from typing import Annotated
from uuid import UUID

from fastapi import FastAPI, Query, Request, Response, status
from fastapi.responses import JSONResponse

from .contracts import Cart, CartInput, Product, ProductInput, ProductPage
from .domain import Carts, Catalog, DomainError


def create_app() -> FastAPI:
    app = FastAPI(title="Mock Commerce API", version="1.0.0")
    catalog = Catalog()
    carts = Carts(catalog)

    @app.exception_handler(DomainError)
    async def domain_error(_request: Request, exc: DomainError) -> JSONResponse:
        code = 404 if exc.code in {"product_not_found", "cart_not_found"} else 409
        return JSONResponse(
            status_code=code, content={"detail": {"code": exc.code, "message": str(exc)}}
        )

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/v1/products", status_code=status.HTTP_201_CREATED, tags=["catalog"])
    def create_product(data: ProductInput, response: Response) -> Product:
        product = catalog.create(data)
        response.headers["Location"] = f"/api/v1/products/{product.id}"
        return product

    @app.get("/api/v1/products", tags=["catalog"])
    def list_products(
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> ProductPage:
        return catalog.page(offset, limit)

    @app.get("/api/v1/products/{product_id}", tags=["catalog"])
    def read_product(product_id: UUID) -> Product:
        return catalog.read(product_id)

    @app.put("/api/v1/products/{product_id}", tags=["catalog"])
    def replace_product(product_id: UUID, data: ProductInput) -> Product:
        return catalog.replace(product_id, data)

    @app.delete(
        "/api/v1/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["catalog"]
    )
    def delete_product(product_id: UUID) -> Response:
        catalog.delete(product_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post("/api/v1/carts", status_code=status.HTTP_201_CREATED, tags=["cart"])
    def create_cart(data: CartInput, response: Response) -> Cart:
        cart = carts.create(data)
        response.headers["Location"] = f"/api/v1/carts/{cart.id}"
        return cart

    @app.get("/api/v1/carts/{cart_id}", tags=["cart"])
    def read_cart(cart_id: UUID) -> Cart:
        return carts.read(cart_id)

    @app.put("/api/v1/carts/{cart_id}", tags=["cart"])
    def replace_cart(cart_id: UUID, data: CartInput) -> Cart:
        return carts.replace(cart_id, data)

    @app.delete("/api/v1/carts/{cart_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["cart"])
    def delete_cart(cart_id: UUID) -> Response:
        carts.delete(cart_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app


app = create_app()
