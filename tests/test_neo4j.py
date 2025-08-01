from neo4j import GraphDatabase
URI  = "bolt://localhost:7687"
AUTH = ("neo4j", "StrongPassword!")

def hello(tx):
    result = tx.run("RETURN 'Hello Neo4j' AS msg")
    return result.single()["msg"]

if __name__ == '__main__':
    driver = GraphDatabase.driver(URI, auth=AUTH)
    with driver.session() as sess:
        msg = sess.execute_read(hello)
        print(msg)