# Code Invariant

This directory must contain a valid Python uv project (`pyproject.toml`) with a FastAPI web server (`app.py`) exposing `POST /add` and `POST /subtract` endpoints. Both endpoints must accept a JSON body with numeric fields `a` and `b`, and respond with `{"result": <computed value>}` where the result is the sum (for `/add`) or difference (for `/subtract`) of `a` and `b`. The test suite must pass with no failures when run via `uv run pytest` from within this directory.
