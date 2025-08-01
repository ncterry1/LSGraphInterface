import sys, os
# Ensure project root is in path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

# Connect to Neo4j
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session() as s:
    # Retrieve a few SENT relationships between Person nodes
    for r in s.run(
        "MATCH (p:Person)-[r:SENT]->(q:Person) RETURN p.email AS sender, r.subject AS subject LIMIT 5"
    ):
        print(r["sender"], r["subject"])

        '''RESULTS
        alice@finance.company.com Budget Report
        carol@hr.company.com Hiring Update
        bob@it.company.com System Downtime
        
        '''