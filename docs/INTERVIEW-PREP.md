# QA and SDET interview practice

Use the project code and reports to explain tradeoffs about testability and CI. Describe only results that you observed.

| Topic | Practice exercise |
| --- | --- |
| Boundary value analysis | Pick the cart quantity range of 1–20. Explain why 0, 1, 20 and 21 cover the two boundaries. Then combine quantity with available stock. |
| Equivalence partitioning | Partition a product ID into existing UUID, valid missing UUID, and malformed value. Explain the expected 200, 404 and 422 responses for a GET. |
| Decision table testing | Derive expected outcomes for a cart line from valid input, product existence, quantity versus stock, and duplicate-line status. Decide which checks take precedence and why. |
| Python live coding | Create a function that parses JSON log lines and returns errors. Demonstrate how you handle malformed input. Write a pytest parameterized test for the parser and one HTTP assertion with Requests. |
| Linux fundamentals | Start a foreground process, inspect it with `ps`, follow logs with `tail -f`, filter them with `grep`, and explain read, write and execute permissions. |
| CI/CD quality gates | Walk through a push from checkout through linting, regression and artifact upload. Explain how a failed test affects the job and why results should remain available. |
| Behavioral preparation | Prepare short STAR examples from work you actually did. Cover finding a defect's cause, agreeing sprint scope with developers, and improving a QA practice. Explain the observable outcome and any tradeoff. |

## References for practice

- [pytest parameterization](https://docs.pytest.org/en/stable/how-to/parametrize.html)
- [FastAPI tutorial](https://fastapi.tiangolo.com/tutorial/)
- [GitHub Actions documentation](https://docs.github.com/en/actions)
- [Allure for pytest](https://allurereport.org/docs/pytest/)
