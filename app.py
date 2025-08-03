import os
from fastapi import FastAPI                # Web framework for defining API routes
from pydantic import BaseModel             # Data validation for request bodies
from contextlib import asynccontextmanager  # Manage startup/shutdown events
from fastapi.staticfiles import StaticFiles # Serve static frontend files
from fastapi.responses import JSONResponse # Return custom JSON responses
import openai                              # OpenAI Python SDK for LLM calls

from neo4j import GraphDatabase            # Official Neo4j driver for Python
from config import (                       # Configuration values imported from config.py
    LLM_API_KEY,          # OpenAI API key
    LLM_BASE_URL,         # OpenAI API base URL (for proxy or custom endpoint)
    LLM_MODELS,           # Allowed list of LLM model identifiers
    LLM_DEFAULT_MODEL,    # Fallback model if none specified or invalid
    NEO4J_URI,            # Bolt URI for Neo4j connection (e.g., bolt://localhost:7687)
    NEO4J_USER,           # Username for Neo4j authentication
    NEO4J_PASSWORD        # Password for Neo4j authentication
)

# -----------------------------------------------------------------------------
# Helper to configure external clients at application startup
# -----------------------------------------------------------------------------
# Set up the OpenAI client using credentials and endpoint from config. Ensures all subsequent openai.* calls use the correct API key and base URL.
def configure_clients():
    openai.api_key = LLM_API_KEY
    openai.api_base = LLM_BASE_URL

# -----------------------------------------------------------------------------
# Initialize and manage database connections
# -----------------------------------------------------------------------------
# Create a single, thread-safe Neo4j driver instance for the lifetime of the app.
driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USER, NEO4J_PASSWORD)
)

# -----------------------------------------------------------------------------
# Define application lifespan to run initialization logic before serving requests
# -----------------------------------------------------------------------------
# Configure the OpenAI client once on startup. (Optional) could close or cleanup resources here on shutdown.
@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_clients()
    yield

# Instantiate FastAPI with the custom lifespan manager
app = FastAPI(lifespan=lifespan)

# -----------------------------------------------------------------------------
# Data model for the /api/ask endpoint
# -----------------------------------------------------------------------------
# Schema for incoming chat requests: prompt (text) and optional model (string).
class AskRequest(BaseModel):
    prompt: str
    model: str | None = None

# -----------------------------------------------------------------------------
# Health check endpoint
# -----------------------------------------------------------------------------
# Simple liveness endpoint that returns status=ok. Useful for uptime monitors and load balancers.
@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

# -----------------------------------------------------------------------------
# Chat completion endpoint
# -----------------------------------------------------------------------------
"""
Accepts a JSON body with 'prompt' and optional 'model'.
Validates the model; falls back to default if not in LLM_MODELS.
Sends the prompt to OpenAI Chat Completions and returns the response text.
"""
@app.post("/api/ask")
async def api_ask(req: AskRequest):
    model = req.model if req.model in LLM_MODELS else LLM_DEFAULT_MODEL
    resp = openai.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": req.prompt}]
    )
    return {"response": resp.choices[0].message.content}

# -----------------------------------------------------------------------------
# Graph data retrieval endpoint
# -----------------------------------------------------------------------------
# Returns a combined list of graph nodes and edges in Cytoscape.js format.
# - Nodes: Person nodes with id and email properties
# - Edges: SENT relationships with subject and timestamp metadata
@app.get("/api/graph")
async def get_graph():
    node_query = "MATCH (p:Person) RETURN id(p) AS id, p.email AS email"
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

# -----------------------------------------------------------------------------
# Static frontend mounting
# -----------------------------------------------------------------------------
# Serve files from the 'frontend' directory at the root URL. Falls back to index.html for single-page app routing.
app.mount(
    "/",
    StaticFiles(directory="frontend", html=True),
    name="frontend"
)
