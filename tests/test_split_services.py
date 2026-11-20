from contextlib import ExitStack
from uuid import uuid4

import allure

from qa_api.app import create_cart_app, create_catalog_app

PRODUCT = {"sku": "SPLIT-01", "name": "Test hub", "price_cents": 2500, "stock": 3}


@allure.feature("Service boundary")
def test_cart_prices_from_catalog_over_http(serve, send):
    with serve(create_catalog_app()) as catalog, serve(create_cart_app(catalog)) as cart:
        catalog_path = f"{catalog}/api/v1/products"
        cart_path = f"{cart}/api/v1/carts"
        created = send("POST", catalog_path, json=PRODUCT)
        assert created.status_code == 201
        product_id = created.json()["id"]
        request = {"items": [{"product_id": product_id, "quantity": 2}]}
        response = send("POST", cart_path, json=request)
        assert response.status_code == 201
        assert response.json()["total_cents"] == 5000
        changed = {**PRODUCT, "price_cents": 3000}
        assert send("PUT", f"{catalog_path}/{product_id}", json=changed).status_code == 200
        update = send("PUT", cart + response.headers["Location"], json=request)
        assert update.status_code == 200
        assert update.json()["total_cents"] == 6000
        missing = {"items": [{"product_id": str(uuid4()), "quantity": 1}]}
        error = send("POST", cart_path, json=missing)
        assert error.status_code == 404
        assert error.json()["detail"]["code"] == "product_not_found"


@allure.feature("Service boundary")
def test_catalog_outage_leaves_cart_untouched(serve, send):
    with ExitStack() as cart_stack:
        with serve(create_catalog_app()) as catalog:
            cart = cart_stack.enter_context(serve(create_cart_app(catalog)))
            created = send("POST", f"{catalog}/api/v1/products", json=PRODUCT)
            assert created.status_code == 201
            product_id = created.json()["id"]
            original = {"items": [{"product_id": product_id, "quantity": 1}]}
            response = send("POST", f"{cart}/api/v1/carts", json=original)
            assert response.status_code == 201
            path = cart + response.headers["Location"]
        change = {"items": [{"product_id": product_id, "quantity": 2}]}
        rejected = send("PUT", path, json=change)
        assert rejected.status_code == 503
        assert rejected.json()["detail"]["code"] == "catalog_unavailable"
        assert send("GET", path).json() == response.json()
