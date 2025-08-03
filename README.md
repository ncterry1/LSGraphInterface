# LSGraphInterface – Full Setup & Usage Guide (Snapshot v1)

This snapshot captures the fully working version of the guide with detailed instructions and complete code blocks. Use this as the source of truth.

---

## Table of Contents

1. Overview
2. Prepare the Host & Install Docker
3. Project Skeleton
4. Python venv & Requirements
5. Docker & Neo4j Setup
6. Verification Steps
7. Data Ingestion Script
8. Python Connectivity Test (Optional)
9. Backend (`app.py`)
10. Frontend (`frontend/index.html`)
11. Advanced Email Loader
12. Advanced Email Dataset
13. Running the Application (Uvicorn & localhost)
14. Next Steps
15. Complete File Manifest

---

## 1 Overview

**Goal:** Build an interactive browser-based UI to explore an email-derived knowledge graph in Neo4j, with LLM-powered analysis.

**Components:**

- **Neo4j 5.18** (Docker)
- **FastAPI** backend (`/api/graph`, `/api/ask`)
- **Cytoscape.js** frontend
- **OpenAI-compatible** LLM client

---

## 2 Prepare the Host & Install Docker *(Terminal 1)*

**Step 1: System Update & Essential Tools**

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl gnupg lsb-release
```

**Step 2: Add Docker’s Official GPG Key & Repository**

```bash
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

**Step 3: Install Docker Engine & Compose**

```bash
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl enable docker && sudo systemctl start docker
sudo usermod -aG docker "$USER"   # then re-login or run: newgrp docker
```

**Step 4: Verify Installation**

```bash
docker info    # should display client & server info
docker run hello-world  # test container run
```

**Troubleshooting**: If you see “Cannot connect to the Docker daemon”:

```bash
sudo systemctl status docker    # check service
sudo systemctl start docker     # start if needed
newgrp docker                   # re-evaluate group membership
```

---

## 3 Project Skeleton *(Terminal 1)*

**Instructions:** Initialize the Git repo, create the full directory tree (including utility folders), and configure the external Neo4j data folder.

```bash
# Go to project root and initialize
mkdir -p ~/LSGraphInterface && cd ~/LSGraphInterface
git init
# Optional: create a Python package marker
touch __init__.py

# Create directory structure
dirs=(frontend ai_functions neo4j_project/scripts tests utils results)
for d in "${dirs[@]}"; do
  mkdir -p "$d"
done

# Neo4j external data (keep DB out of Git)
echo "export NEO4J_DATA_ROOT=\"$HOME/neo4j_dbs/lsgraphinterface\"" >> ~/.bashrc
source ~/.bashrc
mkdir -p "$NEO4J_DATA_ROOT"

# .gitignore – exclude venv, env, and others
cat > .gitignore <<'EOF'
.venv/
.env
neo4j_dbs/
__pycache__/
*.py[cod]
*.log
.vscode/
.idea/
.DS_Store
docker-compose.override.yml
EOF
```

---

## 4 Python venv & Requirements *(Terminal 2 – VS Code venv)*

Set up Python environment and dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
cat > requirements.txt <<'REQ'
fastapi
uvicorn[standard]
neo4j
openai
python-dotenv
REQ
pip install -r requirements.txt
```

Create `.env` with the following environment variables and data root configuration:

```bash
cat > .env << 'ENV'
# LLM / API settings
LLM_API_KEY=
LLM_BASE_URL=
LLM_DEFAULT_MODEL=gpt-3.5-turbo

# Neo4j configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=StrongPassword!
NEO4J_DATA_ROOT=${HOME}/neo4j_dbs/lsgraphinterface
ENV
```

---

## 5 Docker & Neo4j Setup *(Terminal 1)*

### 5-A Pull Image & Set Initial Password

```bash
docker pull neo4j:5.18
# Set the initial password (one-time)
docker run --rm neo4j:5.18 neo4j-admin dbms set-initial-password 'StrongPassword!'
```

### 5-B Run Neo4j Container Directly

```bash
docker run -d --name lsgraph_neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/StrongPassword! \
  -v "$NEO4J_DATA_ROOT:/data" \
  neo4j:5.18
```

*Confirm it’s running:* `docker ps`

### 5-C Optional: Docker Compose

> Use Compose if you prefer YAML configuration or want to add more services (e.g., backend) later.

Create or update `docker-compose.yml` at project root:

```yaml
version: "3.8"
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

Start with Compose:

```bash
docker compose up -d
```

*Verify:* Browse to [http://localhost:7474](http://localhost:7474) and log in with `neo4j` / `StrongPassword!`.

---

## 6 Verification Steps *(Terminal 1)*

### 6-A Check Container

```bash
docker ps
docker logs lsgraph_neo4j | head -n 20
```

### 6-B Neo4j Browser

Open `http://localhost:7474` and log in:

```
Username: neo4j
Password: StrongPassword!
```

### 6-C Cypher Shell

```bash
docker exec -it lsgraph_neo4j cypher-shell -u neo4j -p StrongPassword!
MATCH (n) RETURN n LIMIT 5;
```

---

## 7 Data Ingestion Script *(Terminal 2)*

**Instructions:** Place `email_data.json` in `neo4j_project/scripts/` and run:

```bash
python neo4j_project/scripts/load_emails.py
```

This merges `Person` nodes and `:SENT` relationships.

---

## 8 Python Connectivity Test (Optional)

**Instructions:** Create `tests/test_neo4j.py` with the following, using the modern transaction function API:

```python
from neo4j import GraphDatabase

URI  = "bolt://localhost:7687"
AUTH = ("neo4j", "StrongPassword!")

def hello(tx):
    result = tx.run("RETURN 'Hello Neo4j' AS msg")
    return result.single()["msg"]

if __name__ == "__main__":
    driver = GraphDatabase.driver(URI, auth=AUTH)
    with driver.session() as session:
        msg = session.execute_read(hello)
        print(msg)
```

Run the test:

```bash
python tests/test_neo4j.py  # should print Hello Neo4j
```

---

## 9 Backend (`app.py`)

**Instructions:** Place this at project root as `app.py`:

```python
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

def configure_clients():
    openai.api_key = LLM_API_KEY
    openai.api_base = LLM_BASE_URL

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

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
    node_q = "MATCH (p:Person) RETURN id(p) AS id, p.email AS email"
    edge_q = (
        "MATCH (p:Person)-[r:SENT]->(q:Person) "
        "RETURN id(p) AS source, id(q) AS target, r.subject AS subject, r.timestamp AS timestamp"
    )
    nodes, edges = [], []
    with driver.session() as session:
        for rec in session.run(node_q):
            nodes.append({"data": {"id": str(rec["id"]), "email": rec["email"]}})
        for rec in session.run(edge_q):
            edges.append({"data": {"source": str(rec["source"]), "target": str(rec["target"]), "subject": rec["subject"], "timestamp": rec["timestamp"]}})
    return JSONResponse({"elements": nodes + edges})

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
```

---

## 10 Frontend (`frontend/index.html`)

**Instructions:** Copy the following complete HTML into `frontend/index.html` to render the graph, configure layouts, and enable two-node analysis:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>LSGraphInterface</title>

  <!-- Cytoscape.js for graph visualization -->
  <script src="https://unpkg.com/cytoscape/dist/cytoscape.min.js"></script>

  <!-- Styles -->
  <style>
    /* Base page layout */
    body {
      margin: 0;
      display: flex;
      flex-direction: column;
      height: 100vh;
      background: #1f2937;
      color: #cbd5e1;
      font-family: system-ui, sans-serif;
    }

    /* Top toolbar with layout selector and analyze button */
    #toolbar {
      display: flex;
      gap: 0.5rem;
      padding: 0.4rem;
      background: #111827;
      align-items: center;
    }

    /* Cytoscape graph container */
    #cy {
      flex: 1 1 auto;
      min-height: 0;
    }

    /* Analysis output area */
    #analysis {
      white-space: pre-wrap;
      max-height: 20vh;
      overflow: auto;
      padding: 0.5rem;
      background: #0f172a;
    }

    /* Shared styles for selects and buttons */
    select,
    button {
      background: #3b82f6;
      color: #fff;
      border: none;
      border-radius: 6px;
      padding: 0.35rem 0.6rem;
      cursor: pointer;
    }
  </style>
</head>
<body>

  <!-- Toolbar -->
  <div id="toolbar">
    <!-- Layout dropdown -->
    <label style="font-size:0.85rem;">
      Layout:
      <select id="layoutSelect">
        <option value="cose">CoSE</option>
        <option value="concentric">Concentric</option>
        <option value="grid">Grid</option>
        <option value="breadthfirst">Breadth-First</option>
      </select>
    </label>

    <!-- Analyze button (enabled when two nodes are selected) -->
    <button id="analyzeBtn" disabled>
      Analyze 2 Nodes
    </button>
  </div>

  <!-- Graph display -->
  <div id="cy"></div>

  <!-- Text output for analysis results -->
  <pre id="analysis"></pre>

  <!-- Main JavaScript -->
  <script>
    // Cytoscape instance and currently selected nodes
    let cy;
    let selected = [];

    // Configuration for different layout algorithms
    const LAYOUT_OPTS = {
      cose: {
        name: 'cose',
        idealEdgeLength: 100,
        nodeSpacing: () => 50,
        padding: 10
      },
      concentric: {
        name: 'concentric',
        padding: 10,
        concentric: node => node.degree(),
        levelWidth: () => 2,
        minNodeSpacing: 50
      },
      grid: {
        name: 'grid',
        padding: 10
      },
      breadthfirst: {
        name: 'breadthfirst',
        padding: 10,
        directed: true
      }
    };

    /**
     * Apply a layout by name.
     * @param {string} name - One of the keys in LAYOUT_OPTS
     */
    function applyLayout(name) {
      cy.layout(LAYOUT_OPTS[name]).run();
    }

    // Handle layout selection changes
    document.getElementById('layoutSelect').onchange = e => applyLayout(e.target.value);

    // When the "Analyze 2 Nodes" button is clicked
    document.getElementById('analyzeBtn').onclick = async () => {
      if (selected.length !== 2) return;

      // Build descriptions for selected nodes
      const infos = selected.map(n => `Node ${n.id()}: ${n.data('email')}\n`).join('');

      // Gather incident edges
      const incidentEdges = cy.edges().filter(e =>
        selected.some(n =>
          [e.data('source'), e.data('target')].includes(n.id())
        )
      );

      // Describe edges
      const relInfo =
        incidentEdges
          .map(e => `Edge ${e.id()} (${e.data('subject') || 'n/a'})\n`)
          .join('') || 'No incident edges.\n';

      // Identify neighbor nodes
      const neighbours = [
        ...new Set(
          incidentEdges
            .map(e => [e.source(), e.target()])
            .flat()
        )
      ].filter(n => !selected.includes(n));

      // Describe neighbor nodes
      const neighbourInfo =
        neighbours
          .map(n => `Node ${n.id()}: ${n.data('email')}\n`)
          .join('') || 'No neighbour nodes.\n';

      // Construct and send prompt
      const prompt = `Analyze:\n${infos}Edges:\n${relInfo}Neighbours:\n${neighbourInfo}`;
      const res = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
      }).then(r => r.json());

      document.getElementById('analysis').textContent = res.response;
    };

    // Fetch graph data and initialize Cytoscape
    fetch('/api/graph')
      .then(r => r.json())
      .then(({ elements }) => {
        cy = cytoscape({
          container: document.getElementById('cy'),
          elements: elements,
          style: [
            {
              selector: 'node',
              style: {
                label: 'data(email)',
                'background-color': '#3b82f6',
                color: '#ffffff',
                'text-valign': 'center',
                'text-halign': 'center',
                'font-size': '11px',
                'text-outline-width': 2,
                'text-outline-color': '#3b82f6'
              }
            },
            {
              selector: 'edge',
              style: {
                label: 'data(subject)',
                'curve-style': 'bezier',
                'line-color': '#64748b',
                'target-arrow-shape': 'triangle',
                'target-arrow-color': '#64748b',
                'font-size': '9px',
                color: '#cbd5e1',
                'text-background-color': '#334155',
                'text-background-opacity': 1,
                'text-background-shape': 'roundrectangle',
                'text-rotation': 'autorotate'
              }
            },
            {
              selector: '.selected',
              style: {
                'background-color': '#facc15',
                'line-color': '#facc15',
                'target-arrow-color': '#facc15',
                color: '#ffffff',
                'font-weight': 'bold',
                'text-outline-width': 0
              }
            }
          ]
        });

        // Apply default layout
        applyLayout('cose');

        // Node selection logic
        cy.on('tap', 'node', evt => {
          const node = evt.target;
          if (node.hasClass('selected')) {
            node.removeClass('selected');
            selected = selected.filter(n => n.id() !== node.id());
          } else {
            if (selected.length === 2) {
              selected[0].removeClass('selected');
              selected.shift();
            }
            node.addClass('selected');
            selected.push(node);
          }
          document.getElementById('analyzeBtn').disabled = selected.length !== 2;
        });
      });
  </script>
</body>
</html>
```

---

## 11 Advanced Email Loader

**Instructions:** Place this script in `neo4j_project/scripts/load_emails.py`:

```python
import sys, os, json
from neo4j import GraphDatabase
# ensure project root in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..','..')))
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
import pathlib

DATA_FILE = pathlib.Path(__file__).with_name("email_data.json")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session() as session:
    emails = json.loads(DATA_FILE.read_text())
    for mail in emails:
        sender, to, subject, ts = mail["from"], mail["to"], mail["subject"], mail["timestamp"]
        session.run("MERGE (p:Person {email:$sender})", sender=sender)
        session.run("MERGE (q:Person {email:$to})", to=to)
        session.run(
            """
            MATCH (p:Person {email:$sender}), (q:Person {email:$to})
            MERGE (p)-[:SENT {subject:$subject, timestamp:$ts}]->(q)
            """,
            sender=sender, to=to, subject=subject, ts=ts
        )
```

---

## 12 Advanced Email Dataset

**Save** this as `neo4j_project/scripts/email_data.json`:

```json
[
  {"from":"jeff.skilling@enron.com","to":"kenneth.lay@enron.com","subject":"Q4 Earnings Call","timestamp":"2001-01-10T09:00:00"},
  {"from":"louise.kitchen@enron.com","to":"greg.whalley@enron.com","subject":"Gas Market Review","timestamp":"2001-01-11T10:15:00"},
  {"from":"kenneth.lay@enron.com","to":"jeff.skilling@enron.com","subject":"Re: Q4 Earnings Call","timestamp":"2001-01-12T11:30:00"},
  {"from":"greg.whalley@enron.com","to":"louise.kitchen@enron.com","subject":"Re: Gas Market Review","timestamp":"2001-01-13T08:45:00"},
  {"from":"victoria.bartholomew@enron.com","to":"john.dye@enron.com","subject":"Contract Approval","timestamp":"2001-01-14T14:25:00"}
]
```

---

## 13 Running the Application (Uvicorn & localhost)

From your activated venv:

```bash
source .venv/bin/activate
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Open your browser at [http://localhost:8000](http://localhost:8000) to view the interface.

---

## 14 Next Steps

- Expand schemas (Thread, Message nodes)
- Refine LLM prompt templates
- Add search/filter UI controls
- Implement authentication & secure key management

---

## 15 Complete File Manifest

```
LSGraphInterface/
├── .env
├── app.py
├── docker-compose.yml
├── requirements.txt
├── frontend/
│   └── index.html
├── neo4j_project/
│   └── scripts/
│       ├── load_emails.py
│       └── email_data.json
├── tests/
│   └── test_neo4j.py
└── …other util & results folders
```

---
