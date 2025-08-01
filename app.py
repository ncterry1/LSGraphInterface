
## app.py

import os
from fastapi import FastAPI
from pydantic import BaseModel
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import openai

from neo4j import GraphDatabase
from config import (
    LLM_API_KEY, LLM_BASE_URL, LLM_MODELS, LLM_DEFAULT_MODEL,
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
)

# Configure OpenAI client using values from config.py
def configure_clients():
    openai.api_key = LLM_API_KEY
    openai.api_base = LLM_BASE_URL

# Initialize Neo4j driver
driver = GraphDatabase.driver(
    NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_clients()
    yield

app = FastAPI(lifespan=lifespan)

class AskRequest(BaseModel):
    prompt: str
    model: str | None = None

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

@app.post("/api/ask")
async def api_ask(req: AskRequest):
    model = req.model if req.model in LLM_MODELS else LLM_DEFAULT_MODEL
    resp = openai.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": req.prompt}]
    )
    return {"response": resp.choices[0].message.content}

@app.get("/api/graph")
async def get_graph():
    # Fetch all Person nodes with their emails
    node_query = "MATCH (p:Person) RETURN id(p) AS id, p.email AS email"
    # Fetch SENT relationships with subject and timestamp
    edge_query = (
        "MATCH (p:Person)-[r:SENT]->(q:Person) "
        "RETURN id(p) AS source, id(q) AS target, r.subject AS subject, r.timestamp AS timestamp"
    )
    nodes = []
    edges = []
    with driver.session() as session:
        for rec in session.run(node_query):
            nodes.append({"data": {"id": str(rec["id"]), "email": rec["email"]}})
        for rec in session.run(edge_query):
            edges.append({"data": {"source": str(rec["source"]), "target": str(rec["target"]), "subject": rec["subject"], "timestamp": rec["timestamp"]}})
    return JSONResponse({"elements": nodes + edges})

# Serve frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
