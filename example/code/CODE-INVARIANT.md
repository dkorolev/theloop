# Code Invariant

This directory must contain a valid Python uv project (`pyproject.toml`) with a FastAPI web server (`app.py`) exposing `POST /add` and `POST /subtract` endpoints. Both endpoints must accept a JSON body with numeric fields `a` and `b`, and respond with `{"result": <computed value>}` where the result is the sum (for `/add`) or difference (for `/subtract`) of `a` and `b`. The test suite must pass with no failures when run via `uv run pytest` from within this directory.

The test suite in `test_app.py` must contain exactly the following test cases:

- `test_add_integers` — POST /add with `{"a": 10, "b": 5}` returns `{"result": 15.0}`
- `test_add_negative` — POST /add with `{"a": -3, "b": 7}` returns `{"result": 4.0}`
- `test_add_floats` — POST /add with `{"a": 1.5, "b": 2.5}` returns `{"result": 4.0}`
- `test_subtract_integers` — POST /subtract with `{"a": 10, "b": 3}` returns `{"result": 7.0}`
- `test_subtract_negative_result` — POST /subtract with `{"a": 3, "b": 10}` returns `{"result": -7.0}`
- `test_subtract_floats` — POST /subtract with `{"a": 5.5, "b": 2.5}` returns `{"result": 3.0}`
- `test_add_missing_field` — POST /add with `{"a": 5}` (missing `b`) returns HTTP 422
- `test_add_wrong_type` — POST /add with `{"a": "hello", "b": 1}` (string instead of number) returns HTTP 422
- `test_subtract_empty_body` — POST /subtract with `{}` returns HTTP 422
- `test_add_2_and_3` — POST /add 2+3 to match 5