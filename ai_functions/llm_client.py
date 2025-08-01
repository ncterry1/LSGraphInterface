# ai_functions/llm_client.py
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load Neo4j connection from env
load_dotenv()
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

# Initialize Neo4j driver once
_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def configure(*args, **kwargs):
    # No-op; driver is already configured
    pass

def ask(prompt: str, model: str | None = None):
    """
    Executes the prompt as a Cypher query against Neo4j and returns a list of records.
    """
    with _driver.session() as session:
        # Interpret user input as Cypher
        result = session.run(prompt)
        # Convert each record to a dict
        return [record.data() for record in result]
