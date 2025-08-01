import sys, os, json
from neo4j import GraphDatabase
# ensure project root in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..','..')))
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

# Connect
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def ingest_email(tx, email):
    tx.run(
        "MERGE (s:Person {email:$sender})\n"
        "MERGE (r:Person {email:$receiver})\n"
        "MERGE (s)-[rel:SENT {subject:$subject, timestamp:$timestamp}]->(r)",
        sender=email['sender'], receiver=email['receiver'],
        subject=email['subject'], timestamp=email['timestamp']
    )

if __name__ == '__main__':
    data_path = os.path.join(os.path.dirname(__file__), 'email_data.json')
    emails = json.load(open(data_path))
    with driver.session() as session:
        for e in emails:
            session.execute_write(ingest_email, e)
    print(f"Ingested {len(emails)} emails.")