from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_add_integers():
    r = client.post("/add", json={"a": 10, "b": 5})
    assert r.status_code == 200
    assert r.json() == {"result": 15.0}


def test_add_negative():
    r = client.post("/add", json={"a": -3, "b": 7})
    assert r.status_code == 200
    assert r.json() == {"result": 4.0}


def test_add_floats():
    r = client.post("/add", json={"a": 1.5, "b": 2.5})
    assert r.status_code == 200
    assert r.json() == {"result": 4.0}


def test_subtract_integers():
    r = client.post("/subtract", json={"a": 10, "b": 3})
    assert r.status_code == 200
    assert r.json() == {"result": 7.0}


def test_subtract_negative_result():
    r = client.post("/subtract", json={"a": 3, "b": 10})
    assert r.status_code == 200
    assert r.json() == {"result": -7.0}


def test_subtract_floats():
    r = client.post("/subtract", json={"a": 5.5, "b": 2.5})
    assert r.status_code == 200
    assert r.json() == {"result": 3.0}


def test_add_missing_field():
    r = client.post("/add", json={"a": 5})
    assert r.status_code == 422


def test_add_wrong_type():
    r = client.post("/add", json={"a": "hello", "b": 1})
    assert r.status_code == 422


def test_subtract_empty_body():
    r = client.post("/subtract", json={})
    assert r.status_code == 422


def test_add_2_and_3():
    r = client.post("/add", json={"a": 2, "b": 3})
    assert r.status_code == 200
    assert r.json() == {"result": 5.0}
