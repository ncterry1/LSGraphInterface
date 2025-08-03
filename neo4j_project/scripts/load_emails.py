import sys, os, json
from neo4j import GraphDatabase
# ensure project root in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..','..')))
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
import json, pathlib


DATA_FILE = pathlib.Path(__file__).with_name("email_data.json")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session() as session:
    emails = json.loads(DATA_FILE.read_text())
    for mail in emails:
        sender, to, subject, ts = mail["from"], mail["to"], mail["subject"], mail["timestamp"]
        session.run("MERGE (p:Person {email:$sender})", sender=sender)
        session.run("MERGE (q:Person {email:$to})", to=to)
        session.run("""
            MATCH (p:Person {email:$sender}), (q:Person {email:$to})
            MERGE (p)-[:SENT {subject:$subject, timestamp:$ts}]->(q)
        """, sender=sender, to=to, subject=subject, ts=ts)