# Test plan

The target is version 1 of the mock commerce API. Test requests run against isolated Uvicorn instances. Test data is synthetic. The API requires no external services or credentials.

| Area | Technique | Expected behavior | Automated coverage |
| --- | --- | --- | --- |
| Product and cart lifecycle | State transition | Create returns 201 and a Location header. Reads and replacements return 200. Deletes return 204 and subsequent reads return 404. | Product/cart lifecycle tests |
| Product input | Boundary values | SKU 3–24 characters, name 1–80 after trimming, price 1–1,000,000 cents and stock 0–10,000. | P-101 through P-120 |
| Validation partitioning | Equivalence partitioning | Missing values, malformed UUIDs, unexpected fields, numeric strings, booleans and nulls produce 422 where applicable. | Product fixtures, required-field tests, ID tests and quantity type tests |
| Cart line constraints | Boundary values | Quantity 1–20 and 1–10 distinct lines. | C-101 through C-107 and line-count tests |
| Conflicts | Decision table and concurrency | Duplicate SKU, duplicate lines and quantity above stock produce conflict codes. A concurrent duplicate create results in one product. | SKU conflict, cart conflict, stock and race tests |
| Pagination | Boundary values | Limit 1–100, offset at least 0, stable insertion order, empty page at the end. | Pagination tests |
| Cart price snapshots | State transition | A product price update leaves an existing quote intact. A valid PUT reprices. Failed replacement leaves the old cart intact. | Snapshot and replacement test |
| Service and contract | Smoke | Health is OK and the OpenAPI paths advertise expected CRUD methods. | Health and OpenAPI test |

Run the whole suite when changing a contract or domain rule. Separate test cases should fail with the API response or state involved. When filing a defect, record the case ID, commit, runtime, method/path, synthetic input, expected status/body, actual status/body, and related CI artifact.
