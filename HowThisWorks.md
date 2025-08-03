# LSGraphInterface Workflow Overview

This document describes, in detail, the end-to-end workflow of the LSGraphInterface application. Starting from launching the server to obtaining LLM-powered insights on selected graph nodes, each step is explained with the underlying code interactions.

---

## Summary Introduction

LSGraphInterface is a local development setup that:

1. **Serves a graph UI** powered by Cytoscape.js, displaying email-based relationships stored in Neo4j.
2. **Exposes API endpoints** via FastAPI to fetch graph data and to query a language model for analysis.
3. **Integrates** a local or closed-system LLM (GPT-compatible) to provide context-aware insights when two nodes are selected.

This workflow guide walks through:

- Initial server startup and configuration
- Loading and rendering the graph in the browser
- Handling user interactions (node selection & analysis)
- Backend processing of graph and LLM calls

---

## 1. Server Startup & Configuration

### 1.1 Activate Virtual Environment

```bash
source .venv/bin/activate
```

- **Purpose:** Ensures Python dependencies (FastAPI, Neo4j driver, OpenAI SDK) are available.

### 1.2 Launch Uvicorn

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

- ``: ASGI server that runs the FastAPI app.
- ``: Automatically reloads code on file changes.
- ``: Imports the `app` instance from `app.py`.

#### 1.2.1 Lifespan Event

- **FastAPI** calls `lifespan` context manager on startup:
  - Executes `configure_clients()`:
    ```python
    openai.api_key = LLM_API_KEY
    openai.api_base = LLM_BASE_URL
    ```
  - **Outcome:** OpenAI client is configured for future LLM calls.

---

## 2. Serving Frontend

### 2.1 Static Files Mount

- **In **``**:**
  ```python
  app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
  ```
- **Effect:** Any request to `/` returns `frontend/index.html` and associated JS/CSS.

### 2.2 Browser Request

- **User** navigates to `http://localhost:8000/`.
- **FastAPI** serves the HTML and JavaScript for the Cytoscape UI.

---

## 3. Graph Data Fetch & Initialization

### 3.1 Fetch Graph Data

```js
fetch('/api/graph')
  .then(res => res.json())
  .then(({ elements }) => initializeCytoscape(elements));
```

- **Action:** Frontend sends `GET /api/graph`.

### 3.2 Backend Query: `get_graph()`

```python
@app.get("/api/graph")
def get_graph():
    # 1. Run Cypher to fetch Person nodes
    nodes = session.run("MATCH (p:Person) RETURN id(p) AS id, p.email AS email")
    # 2. Run Cypher to fetch SENT edges
    edges = session.run("MATCH (p:Person)-[r:SENT]->(q:Person) RETURN id(p), id(q), r.subject, r.timestamp")
    return JSONResponse({"elements": nodes + edges})
```

- **Purpose:** Retrieve all nodes and edges to visualize.
- **Data Format:** JSON array with `{ data: { id, email }}` for nodes and `{ data: { source, target, subject, timestamp }}` for edges.

### 3.3 Initialize Cytoscape

```js
cy = cytoscape({
  container: document.getElementById('cy'),
  elements,
  style: [ /* styling selectors */ ],
  layout: { name: 'cose', idealEdgeLength:100, nodeSpacing:50 }
});
```

- **Outcome:** Graph is rendered. Initial layout organizes nodes.

---

## 4. User Interaction: Node Selection

### 4.1 Tap Event Listener

```js
cy.on('tap', 'node', event => {
  const node = event.target;
  toggleSelection(node);
});
```

- **Effect:** Whenever a node is clicked, `toggleSelection()` runs.

### 4.2 `toggleSelection(node)`

1. **Check if node is already selected**:
   - If yes, remove `.selected` class and remove from `selected` array.
2. **If selecting new**:
   - If `selected.length === 2`, deselect the oldest.
   - Add `.selected` class and push to `selected`.
3. **Enable/Disable Analyze button**: `selected.length === 2` → button enabled.

---

## 5. Analysis Workflow

Triggered by clicking **Analyze 2 Nodes** button:

### 5.1 Gather Context

```js
const infos = selected.map(n => `Node ${n.id()}: ${n.data('email')}
`).join('');
```

- **Collects:** IDs and emails of two selected nodes.

```js
const incidentEdges = cy.edges().filter(e => …);
const relInfo = incidentEdges.map(...).join('');
const neighbours = extractNeighbours(incidentEdges, selected);
```

- **Incident edges:** Filters edges incident to either selected node.
- **Neighbours:** Finds connected nodes not in the selected pair.

### 5.2 Build Prompt

```js
const prompt = `Analyze:
${infos}Edges:
${relInfo}Neighbours:
${neighbourInfo}`;
```

- **Goal:** Provide the LLM with graph context (nodes, edges, neighbours).

### 5.3 Call LLM Endpoint

```js
const res = await fetch('/api/ask', {
  method: 'POST',
  body: JSON.stringify({ prompt }),
});
const analysis = await res.json();
```

- **Backend** receives prompt under `AskRequest` model.

### 5.4 Backend `api_ask()`

```python
@app.post("/api/ask")
def api_ask(req: AskRequest):
    model = req.model if req.model in LLM_MODELS else LLM_DEFAULT_MODEL
    resp = openai.chat.completions.create(
        model=model,
        messages=[{"role":"user","content":req.prompt}]
    )
    return {"response": resp.choices[0].message.content}
```

- **Action:** Uses OpenAI SDK to query the LLM.
- **Response:** Returns the LLM’s answer as `response`.

### 5.5 Display Analysis

```js
document.getElementById('analysis').textContent = analysis.response;
```

- **UI Update:** Shows the analysis text in the `<pre>` area.

---

## 6. Summary of Code Functions

| Step                        | Frontend Function           | Backend Function       |
| --------------------------- | --------------------------- | ---------------------- |
| Fetch graph data            | `fetchGraph()` (JS)         | `get_graph()` (Python) |
| Node selection              | `toggleSelection()` (JS)    | —                      |
| Build LLM prompt            | Inline JS code in `onclick` | —                      |
| Call LLM                    | `fetch('/api/ask')` (JS)    | `api_ask()` (Python)   |
| Initialize Cytoscape layout | `applyLayout(name)` (JS)    | —                      |

---

*Save this file as **`workflow.md`** for inclusion in your docs.*
