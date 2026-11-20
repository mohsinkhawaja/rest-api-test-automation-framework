import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import UUID

import allure
import pytest

PRODUCTS = "/api/v1/products"
MISSING = "00000000-0000-0000-0000-000000000000"
PRODUCT = {"sku": "CABLE-001", "name": "USB cable", "price_cents": 899, "stock": 25}
CASES = json.loads((Path(__file__).parent / "data" / "product-cases.json").read_text("utf-8"))


@allure.feature("Catalog")
@pytest.mark.parametrize("case", CASES, ids=lambda row: f"{row['id']}-{row['description']}")
def test_product_input_classes(client, case):
    payload = {**PRODUCT, **case["overrides"]}
    response = client("POST", PRODUCTS, json=payload)
    assert response.status_code == case["status"]
    if case["status"] == 201:
        expected = {**payload, "name": payload["name"].strip()}
        actual = response.json()
        assert {key: actual[key] for key in expected} == expected
        assert UUID(actual["id"])
    else:
        assert response.json()["detail"][0]["loc"][0] == "body"
        assert client("GET", PRODUCTS).json()["total"] == 0


@allure.feature("Catalog")
def test_product_lifecycle(client):
    created = client("POST", PRODUCTS, json=PRODUCT)
    assert created.status_code == 201
    product_id = created.json()["id"]
    resource = f"{PRODUCTS}/{product_id}"
    assert created.headers["Location"] == resource
    read = client("GET", resource)
    assert read.status_code == 200
    assert read.json() == {"id": product_id, **PRODUCT}
    changes = {**PRODUCT, "sku": "NEW-001", "price_cents": 1000}
    updated = client("PUT", resource, json=changes)
    assert updated.status_code == 200
    assert updated.json() == client("GET", resource).json() == {"id": product_id, **changes}
    assert client("POST", PRODUCTS, json=PRODUCT).status_code == 201
    deleted = client("DELETE", resource)
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert client("GET", resource).status_code == 404
    assert client("POST", PRODUCTS, json=changes).status_code == 201


@allure.feature("Catalog")
def test_duplicate_sku_create_and_update_do_not_change_products(client):
    original = client("POST", PRODUCTS, json=PRODUCT).json()
    other = {**PRODUCT, "sku": "OTHER"}
    second = client("POST", PRODUCTS, json=other).json()
    duplicate_create = client("POST", PRODUCTS, json=PRODUCT)
    duplicate_update = client("PUT", f"{PRODUCTS}/{second['id']}", json=PRODUCT)
    for response in (duplicate_create, duplicate_update):
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "duplicate_sku"
    assert client("GET", PRODUCTS).json()["items"] == [original, second]


@allure.feature("Catalog")
def test_concurrent_duplicate_sku_creates_one_record(client):
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(
            pool.map(lambda _: client("POST", PRODUCTS, json=PRODUCT).status_code, range(2))
        )
    assert sorted(outcomes) == [201, 409]
    found = client("GET", PRODUCTS).json()
    assert found["total"] == 1
    assert found["items"][0]["sku"] == PRODUCT["sku"]


@pytest.mark.parametrize("method", ["GET", "PUT", "DELETE"])
@pytest.mark.parametrize(("identifier", "status_code"), [(MISSING, 404), ("malformed", 422)])
def test_product_id_errors(client, method, identifier, status_code):
    kwargs = {"json": PRODUCT} if method == "PUT" else {}
    response = client(method, f"{PRODUCTS}/{identifier}", **kwargs)
    assert response.status_code == status_code
    if status_code == 404:
        assert response.json()["detail"]["code"] == "product_not_found"


@pytest.mark.parametrize("params", [{"offset": -1}, {"limit": 0}, {"limit": 101}, {"limit": "x"}])
def test_invalid_pagination(client, params):
    response = client("GET", PRODUCTS, params=params)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][0] == "query"


def test_pagination(client):
    assert client("GET", PRODUCTS).json() == {"items": [], "total": 0, "offset": 0, "limit": 20}
    products = [
        client("POST", PRODUCTS, json={**PRODUCT, "sku": f"PAGE-{index}"}).json()
        for index in range(3)
    ]
    assert client("GET", PRODUCTS, params={"limit": 1, "offset": 1}).json() == {
        "items": [products[1]],
        "total": 3,
        "offset": 1,
        "limit": 1,
    }
    assert client("GET", PRODUCTS, params={"limit": 100}).json()["items"] == products
    assert client("GET", PRODUCTS, params={"offset": 3}).json()["items"] == []


@pytest.mark.parametrize("key", PRODUCT)
def test_required_product_fields(client, key):
    product = {name: value for name, value in PRODUCT.items() if name != key}
    response = client("POST", PRODUCTS, json=product)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", key]


def test_health_and_openapi(client):
    assert client("GET", "/health").json() == {"status": "ok"}
    paths = client("GET", "/openapi.json").json()["paths"]
    assert set(paths[PRODUCTS]) == {"get", "post"}
    assert set(paths[f"{PRODUCTS}/{{product_id}}"]) == {"get", "put", "delete"}
    assert {"post"} == set(paths["/api/v1/carts"])
    assert {"get", "put", "delete"} == set(paths["/api/v1/carts/{cart_id}"])
