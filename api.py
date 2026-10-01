from fastapi import FastAPI, HTTPException
from main import BLOCK_LIMIT, REVIEW_LIMIT, VELOCITY_WINDOW_SEC, VELOCITY_LIMIT, HISTORY_TTL, score, add_history, client_exists, save_transaction
from pydantic import BaseModel,Field, AwareDatetime

class Transaction(BaseModel):
    id: int = Field(gt=0)
    client_id: int = Field(gt=0)
    amount: int = Field(ge=0)
    city: str | None = None
    occurred_at: AwareDatetime

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/settings")
def settings():
    return {
        "block_limit": BLOCK_LIMIT,
        "review_limit": REVIEW_LIMIT,
        "velocity_window_sec": VELOCITY_WINDOW_SEC,
        "velocity_limit": VELOCITY_LIMIT,
        "history_ttl": HISTORY_TTL
    }

@app.post("/transactions/score")
def score_transaction(tx: Transaction):
    data = tx.model_dump()
    if not client_exists(data["client_id"]):
        raise HTTPException(404,detail="Client not found")
    result = score(data)
    add_history(data)
    save_transaction(data,result)
    return {"decision": result}