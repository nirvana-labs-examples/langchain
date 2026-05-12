"""
Minimal LangGraph RAG agent.

Stack:
  - Qdrant    : vector store for retrieved doc chunks
  - Postgres  : LangGraph checkpoints (conversation memory across turns)
  - Redis     : per-session activity counter
  - FastEmbed : local embeddings (BAAI/bge-small-en-v1.5, 384-dim)
  - Ollama    : local LLM (runs on same VM, no external API key)

Endpoints:
  POST /chat    : send a message in a session, get a grounded answer
  POST /ingest  : add new documents to the knowledge base
  GET  /health  : readiness check
  GET  /docs/count : how many chunks are indexed
"""

import logging
import os
import time
from pathlib import Path
from typing import Annotated, TypedDict

import redis
from fastapi import FastAPI, HTTPException
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("app")

QDRANT_URL = os.environ.get("QDRANT_URL", "http://qdrant:6333")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
POSTGRES_URL = os.environ["POSTGRES_URL"]
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b-instruct")
COLLECTION = os.environ.get("QDRANT_COLLECTION", "documents")
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384
DOCS_DIR = Path(os.environ.get("DOCS_DIR", "/app/docs"))

# ---------- Initialization ----------

log.info("Connecting to dependencies...")
qdrant = QdrantClient(url=QDRANT_URL, timeout=30)
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
embeddings = FastEmbedEmbeddings(model_name=EMBED_MODEL)
llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.2)

if not qdrant.collection_exists(COLLECTION):
    qdrant.create_collection(
        COLLECTION,
        vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
    )
    log.info("Created Qdrant collection '%s'", COLLECTION)

vectorstore = QdrantVectorStore(
    client=qdrant, collection_name=COLLECTION, embedding=embeddings
)
splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)

checkpointer_cm = PostgresSaver.from_conn_string(POSTGRES_URL)
checkpointer = checkpointer_cm.__enter__()
checkpointer.setup()


# ---------- LangGraph state machine ----------


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    context: str


def retrieve(state: State):
    last_user = next(
        (m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
        "",
    )
    docs = vectorstore.similarity_search(last_user, k=4) if last_user else []
    context = "\n\n---\n\n".join(d.page_content for d in docs)
    return {"context": context}


def generate(state: State):
    system = SystemMessage(
        content=(
            "You are a helpful assistant answering questions grounded in the "
            "provided context. If the context does not contain the answer, say so."
            f"\n\nContext:\n{state['context']}"
        )
    )
    response = llm.invoke([system] + state["messages"])
    return {"messages": [response]}


_graph = StateGraph(State)
_graph.add_node("retrieve", retrieve)
_graph.add_node("generate", generate)
_graph.add_edge(START, "retrieve")
_graph.add_edge("retrieve", "generate")
_graph.add_edge("generate", END)
agent = _graph.compile(checkpointer=checkpointer)


# ---------- Seed docs on cold start ----------


def ingest_paths(paths: list[Path]) -> int:
    chunks: list[Document] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for chunk in splitter.split_text(text):
            chunks.append(Document(page_content=chunk, metadata={"source": path.name}))
    if not chunks:
        return 0
    vectorstore.add_documents(chunks)
    return len(chunks)


def seed_if_empty():
    count = qdrant.count(COLLECTION, exact=True).count
    if count > 0:
        log.info("Collection has %d points, skipping seed", count)
        return
    if not DOCS_DIR.is_dir():
        log.warning("No seed docs at %s", DOCS_DIR)
        return
    md_files = sorted(DOCS_DIR.glob("*.md"))
    if not md_files:
        log.warning("No .md files in %s", DOCS_DIR)
        return
    n = ingest_paths(md_files)
    log.info("Seeded %d chunks from %d files", n, len(md_files))


seed_if_empty()


# ---------- HTTP API ----------

app = FastAPI(title="LangChain RAG Agent")


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[str]


class IngestRequest(BaseModel):
    texts: list[str]
    source: str = "user"


@app.get("/health")
def health():
    return {
        "ok": True,
        "qdrant_chunks": qdrant.count(COLLECTION, exact=True).count,
        "model": OLLAMA_MODEL,
    }


@app.get("/docs/count")
def docs_count():
    return {"chunks": qdrant.count(COLLECTION, exact=True).count}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(400, "message must not be empty")

    redis_client.hincrby(f"session:{req.session_id}", "turns", 1)
    redis_client.hset(f"session:{req.session_id}", "last_active", int(time.time()))

    config = {"configurable": {"thread_id": req.session_id}}
    state = agent.invoke({"messages": [HumanMessage(content=req.message)]}, config=config)

    sources = list({
        d.metadata.get("source", "")
        for d in vectorstore.similarity_search(req.message, k=4)
    })
    return ChatResponse(
        session_id=req.session_id,
        answer=state["messages"][-1].content,
        sources=[s for s in sources if s],
    )


@app.post("/ingest")
def ingest(req: IngestRequest):
    docs = [Document(page_content=t, metadata={"source": req.source}) for t in req.texts]
    chunks: list[Document] = []
    for d in docs:
        for c in splitter.split_text(d.page_content):
            chunks.append(Document(page_content=c, metadata=d.metadata))
    if not chunks:
        return {"chunks_added": 0}
    vectorstore.add_documents(chunks)
    return {"chunks_added": len(chunks)}
