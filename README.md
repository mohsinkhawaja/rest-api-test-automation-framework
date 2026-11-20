# REST API Test Automation Framework

[![API quality gate](https://github.com/mohsinkhawaja/rest-api-test-automation-framework/actions/workflows/quality.yml/badge.svg)](https://github.com/mohsinkhawaja/rest-api-test-automation-framework/actions/workflows/quality.yml)

A FastAPI mock backend and an independent HTTP regression suite for a product catalog and shopping carts. The suite checks CRUD, validation boundaries, and state changes across resources. Each test boots a clean server on a loopback port and uses Requests to call it over HTTP.

## Architecture

```text
JSON and CSV cases ── pytest + Requests ── HTTP ── FastAPI routes
                                                ├─ Catalog
                                                └─ Carts ── product snapshots
                      └─ JUnit and Allure results ── CI artifacts
```

- `qa_api/contracts.py` defines typed payloads and response models.
- `qa_api/domain.py` owns inventory and cart behavior. The catalog protects its SKU index and products under the same lock. Cart replacement validates all lines before publishing the new state.
- `qa_api/app.py` defines the HTTP boundary, maps domain errors to status codes, and wires fresh state through an app factory.
- `tests/` contains HTTP scenarios, reusable setup, and curated JSON and CSV cases. See the [test plan](docs/TEST_PLAN.md).

This is one process with separate catalog and cart components. Storage is in memory and resets on restart. Carts snapshot price at creation and replacement. Products can be removed without making previously priced carts unreadable. Cart writes check current stock without reserving or decrementing inventory. Authentication, persistence and multi-worker deployment are outside the scope of this mock service.

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
