# REST API Test Automation Framework

[![API quality gate](https://github.com/mohsinkhawaja/rest-api-test-automation-framework/actions/workflows/quality.yml/badge.svg)](https://github.com/mohsinkhawaja/rest-api-test-automation-framework/actions/workflows/quality.yml)

A FastAPI mock backend and an independent HTTP regression suite for a product catalog and shopping carts. The suite checks CRUD, validation boundaries, and state changes across resources. It boots clean servers on loopback ports and uses Requests to exercise both local and split service modes.

## Architecture

```text
JSON and CSV cases ── pytest + Requests ── HTTP ── Catalog service
                                           └───── Cart service ── HTTP snapshot ── Catalog
                      └─ JUnit and Allure results ── CI artifacts
```

- `qa_api/contracts.py` defines typed payloads and response models.
- `qa_api/domain.py` owns inventory and cart behavior. The catalog protects its SKU index and products under the same lock. Cart replacement validates all lines before publishing the new state.
- `qa_api/app.py` defines the HTTP routes, maps domain errors to status codes, and exposes independent app factories for each service.
- `qa_api/http_catalog.py` obtains catalog snapshots over HTTP in split mode. The cart keeps its previous state when the catalog is unavailable.
- `tests/` contains HTTP scenarios, reusable setup, and curated JSON and CSV cases. See the [test plan](docs/TEST_PLAN.md).

In split mode the catalog and cart run independently and exchange a product snapshot over HTTP. The default mode serves both components from one process for quick exploration. Storage is in memory and resets on restart. Carts snapshot price at creation and replacement. Products can be removed without making previously priced carts unreadable. Cart writes check current stock without reserving or decrementing inventory.

## Run locally

Install Python 3.14. From the project root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-test.txt
python -m pytest --junitxml=artifacts/junit.xml --alluredir=artifacts/allure-results --clean-alluredir
```

In Windows PowerShell, use `./.venv/Scripts/Activate.ps1` in place of `source`, or run the commands with `./.venv/Scripts/python.exe`.

The test suite starts its own server. To explore the API manually, run `python -m uvicorn qa_api.app:app` and open [Swagger UI](http://127.0.0.1:8000/docs).

To run independently, start these in two terminals from the project root. The cart service uses the catalog at port 8001 by default. Set `QA_CATALOG_URL` if you choose a different address.

```bash
python -m uvicorn qa_api.app:create_catalog_app --factory --host 127.0.0.1 --port 8001
python -m uvicorn qa_api.app:create_cart_app --factory --host 127.0.0.1 --port 8002
```

Catalog Swagger UI is on port 8001 and cart Swagger UI is on port 8002. The catalog snapshot route is internal to this local lab. Split mode assumes one instance per service and stores synthetic data only.

| Resource | Methods |
| --- | --- |
| `/health` | GET |
| `/api/v1/products` | GET with limit/offset, POST |
| `/api/v1/products/{product_id}` | GET, PUT, DELETE |
| `/api/v1/carts` | POST |
| `/api/v1/carts/{cart_id}` | GET, PUT, DELETE |

## Reports and CI

GitHub Actions runs Ruff and pytest on every push and pull request. A failed test fails the job. Open a run and download **api-quality-evidence** to inspect `junit.xml`, the Allure result files, and the generated HTML report.

Generate the same Allure HTML locally with Java and the [Allure command-line tool](https://allurereport.org/docs/v2/install/):

```bash
allure generate --clean artifacts/allure-results -o artifacts/allure-report
allure open artifacts/allure-report
```

See [local execution evidence](docs/EXECUTION.md) and the [QA interview practice guide](docs/INTERVIEW-PREP.md).
