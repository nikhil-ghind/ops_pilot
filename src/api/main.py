from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.agent.ops_agent import run_agent

app = FastAPI(title="OpsPilot API")


class QueryRequest(BaseModel):
    query: str
    stream: bool = False


@app.post("/query")
async def query(req: QueryRequest):
    if req.stream:
        return StreamingResponse(
            (chunk for chunk in run_agent(req.query)),
            media_type="text/plain",
        )
    response = "".join(run_agent(req.query))
    return {"response": response}


@app.get("/health")
def health():
    return {"status": "ok"}
