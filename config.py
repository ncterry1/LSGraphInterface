import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# LLM / API settings
LLM_API_KEY       = os.getenv("LLM_API_KEY")
LLM_BASE_URL      = os.getenv("LLM_BASE_URL")
# Target models: OpenAI's GPT-3.5 Turbo and GPT-4
LLM_MODELS = [
    "gpt-3.5-turbo",
    "gpt-4",
]
# Default to GPT-3.5 Turbo if not specified
LLM_DEFAULT_MODEL = os.getenv("LLM_DEFAULT_MODEL", "gpt-3.5-turbo")

# Neo4j settings
NEO4J_URI       = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER      = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD  = os.getenv("NEO4J_PASSWORD", "StrongPassword!")
NEO4J_DATA_ROOT = os.getenv("NEO4J_DATA_ROOT", os.path.expanduser("~/neo4j_dbs/lsgraphinterface"))