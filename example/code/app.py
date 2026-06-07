from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Operands(BaseModel):
    a: float
    b: float


@app.post("/add")
def add(operands: Operands):
    return {"result": operands.a + operands.b}


@app.post("/subtract")
def subtract(operands: Operands):
    return {"result": operands.a - operands.b}
