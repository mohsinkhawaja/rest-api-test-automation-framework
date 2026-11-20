import csv
from pathlib import Path

import allure
import pytest

PRODUCTS = "/api/v1/products"
CARTS = "/api/v1/carts"
MISSING = "00000000-0000-0000-0000-000000000000"
with (Path(__file__).parent / "data" / "cart-quantities.csv").open(
    encoding="utf-8", newline=""
) as file:
    CASES = list(csv.DictReader(file))


def seed_product(client, *, sku="WIRE", stock=25, price=350):
    response = client(
        "POST",
        PRODUCTS,
        json={"name": "Cable", "sku": sku, "price_cents": price, "stock": stock},
    )
    assert response.status_code == 201
    return response.json()


def cart_payload(product_id, quantity):
    return {"items": [{"product_id": product_id, "quantity": quantity}]}


@allure.feature("Carts")
@pytest.mark.parametrize("case", CASES, ids=lambda row: f"{row['id']}-{row['description']}")
def test_cart_quantity_classes(client, case):
    product = seed_product(client, stock=int(case["stock"]))
    response = client("POST", CARTS, json=cart_payload(product["id"], int(case["quantity"])))
    assert response.status_code == int(case["status"])
    if case["status"] == "201":
        assert response.json()["total_cents"] == product["price_cents"] * int(case["quantity"])
    elif case["error"]:
        assert response.json()["detail"]["code"] == case["error"]


@allure.feature("Carts")
def test_cart_lifecycle_and_totals(client):
    first = seed_product(client)
    second = seed_product(client, sku="OTHER", price=100)
    payload = {
        "items": [
            {"product_id": first["id"], "quantity": 2},
            {"product_id": second["id"], "quantity": 3},
        ]
    }
    created = client("POST", CARTS, json=payload)
    assert created.status_code == 201
    instance = created.json()
    path = f"{CARTS}/{instance['id']}"
    assert created.headers["Location"] == path
    assert instance == {
        "id": instance["id"],
        "total_cents": 1000,
        "items": [
            {
                "product_id": first["id"],
                "quantity": 2,
                "unit_price_cents": 350,
                "line_total_cents": 700,
            },
            {
                "product_id": second["id"],
                "quantity": 3,
                "unit_price_cents": 100,
                "line_total_cents": 300,
            },
        ],
    }
    assert client("GET", path).json() == instance
    new_payload = cart_payload(second["id"], 4)
    replacement = client("PUT", path, json=new_payload)
    assert replacement.status_code == 200
    assert replacement.json() == client("GET", path).json()
    assert replacement.json()["total_cents"] == 400
    assert client("PUT", path, json=new_payload).json() == replacement.json()
    updated_stock = client("GET", f"{PRODUCTS}/{second['id']}").json()["stock"]
    assert updated_stock == second["stock"]
    deleted = client("DELETE", path)
    assert deleted.status_code == 204 and deleted.content == b""
    assert client("GET", path).status_code == 404


@allure.feature("Carts")
def test_cart_price_snapshot_and_atomic_replacement(client):
    product = seed_product(client)
    product_path = f"{PRODUCTS}/{product['id']}"
    request = cart_payload(product["id"], 2)
    cart = client("POST", CARTS, json=request).json()
    path = f"{CARTS}/{cart['id']}"
    updated = {key: value for key, value in product.items() if key != "id"}
    assert client("PUT", product_path, json={**updated, "price_cents": 400}).status_code == 200
    assert client("GET", path).json()["total_cents"] == 700
    assert client("PUT", path, json=request).json()["total_cents"] == 800
    assert client("DELETE", product_path).status_code == 204
    rejected = client("PUT", path, json=request)
    assert rejected.status_code == 404
    assert rejected.json()["detail"]["code"] == "product_not_found"
    assert client("GET", path).json()["total_cents"] == 800


@pytest.mark.parametrize("method", ["GET", "PUT", "DELETE"])
@pytest.mark.parametrize(("identifier", "status_code"), [(MISSING, 404), ("bad-id", 422)])
def test_cart_id_errors(client, method, identifier, status_code):
    kwargs = {"json": cart_payload(MISSING, 1)} if method == "PUT" else {}
    response = client(method, f"{CARTS}/{identifier}", **kwargs)
    assert response.status_code == status_code
    if status_code == 404:
        assert response.json()["detail"]["code"] == "cart_not_found"


@pytest.mark.parametrize("count", [0, 10, 11])
def test_cart_line_count(client, count):
    ids = [seed_product(client, sku=f"SKU-{item}")["id"] for item in range(count)]
    payload = {"items": [{"product_id": item, "quantity": 1} for item in ids]}
    response = client("POST", CARTS, json=payload)
    assert response.status_code == (201 if count == 10 else 422)
    if count == 10:
        assert len(response.json()["items"]) == 10
        assert response.json()["total_cents"] == 3500


def test_duplicate_cart_lines(client):
    product_id = seed_product(client)["id"]
    payload = cart_payload(product_id, 1)
    payload["items"].append({"product_id": product_id, "quantity": 2})
    response = client("POST", CARTS, json=payload)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "duplicate_item"


def test_unknown_product_returns_domain_error(client):
    response = client("POST", CARTS, json=cart_payload(MISSING, 1))
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "product_not_found"


@pytest.mark.parametrize("value", ["1", True, 1.5, None])
def test_quantity_requires_integer(client, value):
    response = client("POST", CARTS, json=cart_payload(MISSING, value))
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "items", 0, "quantity"]
