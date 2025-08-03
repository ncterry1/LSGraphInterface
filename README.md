# LSGraphInterface – Docker & Neo4j Full Setup Guide

> This document details every step to build and run the LSGraphInterface project: from host prep, to Docker/Neo4j, Python environment, data ingestion, and interactive graph frontend.

---

## 0 Prerequisites

- **OS:** Ubuntu 22.04 LTS (or similar) with Bash
- **Python:** 3.10+ (`python3 --version`)
- **Git:** latest
- **Docker Engine:** ≥ 24.x
- **Browser:** modern (Chrome, Firefox)

**Project root:** `~/LSGraphInterface`

---

## 1 Prepare the Host & Install Docker (Terminal 1)

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl gnupg lsb-release
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io
sudo systemctl enable docker && sudo systemctl start docker
sudo usermod -aG docker "$USER"   # then re-log or run: newgrp docker

docker info   # should show client+server info
```

> **Troubleshoot** “Cannot connect to the Docker daemon”:\
> `sudo systemctl status docker` → `sudo systemctl start docker` → `newgrp docker` or prefix with `sudo`.

---

## 2 Clone & Scaffold the Project (Terminal 1)

```bash
mkdir -p ~/LSGraphInterface && cd ~/LSGraphInterface
git init
touch __init__.py

# Create directory structure
dirs=(frontend ai_functions neo4j_project/scripts tests utils results)
for d in "${dirs[@]}"; do mkdir -p "$d"; done

# Neo4j external data
echo "export NEO4J_DATA_ROOT=\"$HOME/neo4j_dbs/lsgraphinterface\"" >> ~/.bashrc
source ~/.bashrc
mkdir -p "$NEO4J_DATA_ROOT"

# .gitignore
echo -e ".venv/\n.env\nneo4j_dbs/\n__pycache__/\n*.py[cod]\n*.log\n.vscode/\n.idea/\n.DS_Store\ndocker-compose.override.yml" > .gitignore
```

---

## 3 Python Virtual Environment & Dependencies (Terminal 2)

```bash
cd ~/LSGraphInterface
python3 -m venv .venv
source .venv/bin/activate

echo -e "fastapi\nuvicorn\nneo4j\npython-dotenv\nopenai" > requirements.txt
pip install -r requirements.txt
```

### 3.1 Create `.env`

```bash
cat > .env << 'ENV'
# LLM / API
LLM_API_KEY=
LLM_BASE_URL=
LLM_DEFAULT_MODEL=gpt-3.5-turbo

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=StrongPassword!
NEO4J_DATA_ROOT=${HOME}/neo4j_dbs/lsgraphinterface
ENV
```

---

## 4 Docker & Neo4j Setup (Terminal 1)

### 4-A Pull & Initial Password

```bash
docker pull neo4j:5.18
docker run --rm neo4j:5.18 neo4j-admin dbms set-initial-password 'StrongPassword!'
```

### 4-B Run Neo4j Container

```bash
docker run -d --name lsgraph_neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/StrongPassword! \
  -v "$NEO4J_DATA_ROOT:/data" \
  neo4j:5.18
```

### 4-C Optional `docker-compose.yml`

```yaml
services:
  neo4j:
    image: neo4j:5.18
    container_name: lsgraph_neo4j
    restart: unless-stopped
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/StrongPassword!
    volumes:
      - ${NEO4J_DATA_ROOT}:/data
```

```bash
docker compose up -d
```

---

## 5 Verification Steps

### 5-A Check Container

```bash
docker ps
docker logs lsgraph_neo4j | head -n 20
```

### 5-B Neo4j Browser

Open [http://localhost:7474](http://localhost:7474) and log in:

- **Username:** neo4j
- **Password:** StrongPassword!

### 5-C Cypher Shell

```bash
docker exec -it lsgraph_neo4j cypher-shell -u neo4j -p StrongPassword!
MATCH (n) RETURN n LIMIT 5;
```

---

## 6 Data Ingestion Script

Place `email_data.json` in `neo4j_project/scripts/` and run:

```bash
python neo4j_project/scripts/load_emails.py
```

This merges `Person` nodes and `:SENT` relationships.

---

## 7 Python Connectivity Test (Optional)

Create `tests/test_neo4j.py`:

```python
from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
with driver.session() as session:
    print(session.run("RETURN 'Hello Neo4j' AS msg").single()["msg"])
```

Run:

```bash
python tests/test_neo4j.py   # should print Hello Neo4j
```

---

## 8 Interactive Graph Frontend & LLM Integration

1. \*\*Add \*\*\`\` in `app.py` to serve Cytoscape elements.
2. **Include Cytoscape.js** in `frontend/index.html`, render nodes/edges, enable tap‐selection for two nodes, and an **Analyze Selection** button.
3. **Build prompt** including selected nodes, incident edges, and neighboring nodes.
4. **POST** to `/api/ask` and display the LLM’s response.

(See Appendix for full file contents.)

---

## Appendix: Core File Listings

### config.py

```python
import os
from dotenv import load_dotenv
load_dotenv()

LLM_API_KEY       = os.getenv("LLM_API_KEY")
LLM_BASE_URL      = os.getenv("LLM_BASE_URL")
LLM_MODELS        = ["gpt-3.5-turbo", "gpt-4"]
LLM_DEFAULT_MODEL = os.getenv("LLM_DEFAULT_MODEL", "gpt-3.5-turbo")

NEO4J_URI       = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER      = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD  = os.getenv("NEO4J_PASSWORD", "StrongPassword!")
NEO4J_DATA_ROOT = os.getenv("NEO4J_DATA_ROOT", os.path.expanduser("~/neo4j_dbs/lsgraphinterface"))
```

### app.py

```python
import openai
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
from neo4j import GraphDatabase
from config import (LLM_API_KEY, LLM_BASE_URL, LLM_MODELS, LLM_DEFAULT_MODEL,
                    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

def configure_clients():
    openai.api_key = LLM_API_KEY
    openai.api_base = LLM_BASE_URL

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_clients()
    yield

app = FastAPI(lifespan=lifespan)

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

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
    node_q = "MATCH (p:Person) RETURN id(p) AS id, p.email AS email"
    edge_q = ("MATCH (p:Person)-[r:SENT]->(q:Person) "
              "RETURN id(p) AS source, id(q) AS target, r.subject AS subject, r.timestamp AS timestamp")
    elems = []
    with driver.session() as s:
        for r in s.run(node_q):
            elems.append({"data": {"id": str(r['id']), "email": r['email']}})
        for r in s.run(edge_q):
            elems.append({"data": {"source": str(r['source']), "target": str(r['target']),
                                    "subject": r['subject'], "timestamp": r['timestamp']}})
    return JSONResponse({"elements": elems})

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
```

### docker-compose.yml

```yaml
services:
  neo4j:
    image: neo4j:5.18
    container_name: lsgraph_neo4j
    restart: unless-stopped
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/StrongPassword!
    volumes:
      - ${NEO4J_DATA_ROOT}:/data
```

### neo4j\_project/scripts/load\_emails.py

```python
import os, sys, json
from neo4j import GraphDatabase
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..','..')))
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def ingest_email(tx, email):
    tx.run(
        "MERGE (s:Person {email:$sender})"
        " MERGE (r:Person {email:$receiver})"
        " MERGE (s)-[rel:SENT {subject:$subject, timestamp:$timestamp}]->(r)",
        sender=email['sender'], receiver=email['receiver'],
        subject=email['subject'], timestamp=email['timestamp']
    )

if __name__ == '__main__':
    path = os.path.join(os.path.dirname(__file__), 'email_data.json')
    with open(path) as f:
        emails = json.load(f)
    with driver.session() as session:
        for e in emails:
            session.execute_write(ingest_email, e)
    print(f"Ingested {len(emails)} emails.")
```

### neo4j\_project/scripts/email\_data.json

```json
[
  {"sender":"alice@finance.company.com","receiver":"bob@it.company.com","subject":"Budget Report","timestamp":"2024-07-29T09:00:00"},
  {"sender":"carol@hr.company.com","receiver":"dave@finance.company.com","subject":"Hiring Update","timestamp":"2024-07-29T10:00:00"},
  {"sender":"bob@it.company.com","receiver":"carol@hr.company.com","subject":"System Downtime","timestamp":"2024-07-29T11:00:00"}
]
```

### tests/query\_emails.py

```python
import os, sys
from neo4j import GraphDatabase
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
with driver.session() as session:
    for r in session.run(
        "MATCH (p:Person)-[r:SENT]->(q:Person) RETURN p.email AS sender, r.subject AS subject LIMIT 5"
    ):
        print(r['sender'], r['subject'])
```

### frontend/index.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LSGraphInterface</title>
  <script src="https://unpkg.com/cytoscape/dist/cytoscape.min.js"></script>
  <style>
    #analysis { white-space: pre-wrap; word-wrap: break-word; max-width:800px; overflow-x:auto; }
    .selected { border-width:3; border-color:#FFD700; border-style:solid; }
  </style>
</head>
<body>
  <div id="cy" style="width:800px; height:600px;"></div>
  <button id="analyzeBtn" disabled>Analyze Selection</button>
  <pre id="analysis"></pre>
  <script>
    let cy; const selectedNodeIds = [];
    fetch('/api/graph').then(r=>r.json()).then(data=>{
      cy=cytoscape({container:document.getElementById('cy'), elements:data.elements,
        style:[{selector:'node',style:{'content':'data(email)'}},
               {selector:'edge',style:{'curve-style':'bezier','target-arrow-shape':'triangle','label':'data(subject)'}},
               {selector:'.selected',style:{'border-width':3,'border-color':'#FFD700','border-style':'solid'}}],
        layout:{name:'cose'}});
      cy.on('tap','node',e=>{
        const n=e.target, id=n.id(), idx=selectedNodeIds.indexOf(id);
        if(idx===-1){selectedNodeIds.push(id);n.addClass('selected');}
        else{selectedNodeIds.splice(idx,1);n.removeClass('selected');}
        document.getElementById('analyzeBtn').disabled=selectedNodeIds.length!==2;
      });
    });
    document.getElementById('analyzeBtn').onclick=async()=>{
      const infos=selectedNodeIds.map(id=>{
        const n=cy.getElementById(id);return `Node ${id}: ${n.data('email')}`;}).join('\n');
      const incident=cy.edges().filter(e=>selectedNodeIds.includes(e.data('source'))||selectedNodeIds.includes(e.data('target')));
      const relInfo=incident.map(e=>`Edge ${e.id()} from ${e.data('source')} to ${e.data('target')}: subject="${e.data('subject')}", timestamp=${e.data('timestamp')}`).join('\n')||'No incident edges.';
      const neighbors=incident.map(e=>[e.source(),e.target()]).flat();
      const uniqueN=neighbors.filter((n,i,a)=>a.findIndex(m=>m.id()===n.id())===i).filter(n=>!selectedNodeIds.includes(n.id()));
      const neighborInfo=uniqueN.map(n=>`Node ${n.id()}: ${n.data('email')}`).join('\n')||'No neighboring nodes.';
      const prompt=`Here is the graph context for analysis:\n\nSelected Nodes:\n${infos}\n\nIncident Edges:\n${relInfo}\n\nNeighboring Nodes:\n${neighborInfo}`;
      const res=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt})}).then(r=>r.json());
      document.getElementById('analysis').textContent=res.response;
    };
  </script>
</body>
</html>
```

## 9 .gitignore Recommendations

Add this to your project root’s `` to keep secrets, caches, and large artifacts out of Git:

```gitignore
# Python virtual env
.venv/

# Secrets / local config
.env

# Local Neo4j data (external path)
neo4j_dbs/

# Byte‑code & caches
__pycache__/
*.py[cod]
*$py.class

# Logs / scratch output
*.log
results/

# IDE / editor junk
.vscode/
.idea/
.DS_Store

# Local docker‑compose overrides
docker-compose.override.yml
```

---

## 10 Replicating the Environment on Another VM

1. **Clone the repo** on the new VM:
   ```bash
   git clone <repo-url> LSGraphInterface && cd LSGraphInterface
   ```
2. **Copy non‑tracked files** from the original VM:
   ```bash
   scp user@old-vm:~/LSGraphInterface/.env       .
   scp -r user@old-vm:~/neo4j_dbs/lsgraphinterface ~/neo4j_dbs/
   ```
3. **Re‑export **`` in the new shell:
   ```bash
   echo "export NEO4J_DATA_ROOT=$HOME/neo4j_dbs/lsgraphinterface" >> ~/.bashrc
   source ~/.bashrc
   ```
4. **Re‑create the venv & install deps:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
5. **Start Neo4j** (Docker) mounting the copied data, or run the ingest script if you chose a fresh DB.
6. **Run FastAPI:**
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000 --reload
   ```

---

## 11 Cleaning Accidental Secrets from Git History

If GitHub push‑protection flags a secret (e.g., OpenAI key in `.env`) you need to:

```bash
# 1 Add to .gitignore & untrack
echo ".env" >> .gitignore
git rm --cached .env

# 2 Commit the change
git commit -m "Stop tracking .env"

# 3 Rewrite history to purge old blobs (easiest via GitHub UI)
#   → GitHub repo ▸ Settings ▸ Code security ▸ Secret scanning ▸ View alert ▸ 'Remove secret'
#   or locally with git filter-repo / BFG, then force‑push:
git push --force
```

---

## 12 Branch House‑Keeping Quick Ref

| Task                      | Command                                      |
| ------------------------- | -------------------------------------------- |
| Create & switch           | `git checkout -b feature/my-branch`          |
| Push first time           | `git push -u origin feature/my-branch`       |
| Delete local branch       | `git branch -d feature/my-branch`            |
| Force‑delete local branch | `git branch -D feature/my-branch`            |
| Delete remote branch      | `git push origin --delete feature/my-branch` |

*End of guide.*
