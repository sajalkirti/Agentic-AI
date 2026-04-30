#!/usr/bin/env python
# coding: utf-8

from typing import List, TypedDict
import os
import re
import pandas as pd

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.documents import Document
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

load_dotenv()

# -----------------------------
# LOAD DATA
# -----------------------------
project_folder = os.path.join(os.path.dirname(__file__), "documents")

xlsx_files = [
    "EnhancedApplicationLog.xlsx",
    "EnhancedDBLog.xlsx",
    "EnhancedLogAnalytics.xlsx",
]

docs = []

for filename in xlsx_files:
    file_path = os.path.join(project_folder, filename)
    df = pd.read_excel(file_path)

    for _, row in df.iterrows():
        docs.append(
            Document(
                page_content=str(row["Details"]),
                metadata={
                    "source": filename,
                    "timestamp": str(row.get("Timestamp", "")),
                    "module": str(row.get("Module", "")),
                    "level": str(row.get("Level", row.get("Status", "")))
                }
            )
        )

print(f"Total documents loaded: {len(docs)}")

# -----------------------------
# GROUP BY CORRELATION ID
# -----------------------------
def group_by_correlation(docs):
    grouped = {}

    for doc in docs:
        match = re.search(r"(CID-[A-Z0-9]+|REQ-[A-Z0-9]+)", doc.page_content)
        cid = match.group(1) if match else "UNKNOWN"

        grouped.setdefault(cid, []).append(doc.page_content)

    return [
        Document(
            page_content="\n".join(logs),
            metadata={"correlation_id": cid}
        )
        for cid, logs in grouped.items()
    ]


chunks = group_by_correlation(docs)
print(f"Grouped docs: {len(chunks)}")

# -----------------------------
# VECTOR STORE
# -----------------------------
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

vector_store = FAISS.from_documents(chunks, embeddings)

retriever = vector_store.as_retriever(
    search_type="mmr",
    search_kwargs={"k": 20, "fetch_k": 50}
)

# -----------------------------
# LLM
# -----------------------------
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)

# -----------------------------
# STATE
# -----------------------------
class State(TypedDict):
    question: str
    retrieval_query: str
    rewrite_tries: int

    need_retrieval: bool
    docs: List[Document]
    relevant_docs: List[Document]
    context: str
    answer: str

    issup: str
    evidence: List[str]
    retries: int

    isuse: str
    use_reason: str

    # ONLY MEMORY (CLEAN)
    message_history: List[str]

# -----------------------------
# RETRIEVE (IMPROVED)
# -----------------------------
def retrieve(state: State):
    query = state.get("retrieval_query") or state["question"]

    history = state.get("message_history", [])

    # keep only last 4 messages
    if history:
        query += " " + " ".join(
            msg["content"] for msg in history[-4:]
            if isinstance(msg, dict) and "content" in msg
)

    # direct CID optimization
    match = re.search(r"(CID-[A-Z0-9]+|REQ-[A-Z0-9]+)", query)

    if match:
        cid = match.group(1)

        matched_docs = [
            doc for doc in chunks
            if doc.metadata.get("correlation_id") == cid
        ]

        if matched_docs:
            return {"docs": matched_docs}

    return {"docs": retriever.invoke(query)}

# -----------------------------
# GENERATION
# -----------------------------
def generate_from_context(state: State):
    context = "\n\n".join([d.page_content for d in state.get("relevant_docs", [])])

    if not context:
        return {"answer": "No answer found.", "context": ""}

    response = llm.invoke(
        f"""Analyze logs and find root cause.

Context:
{context}

Question:
{state['question']}
"""
    )

    # -----------------------------
    # CHAT MEMORY UPDATE (CLEAN)
    # -----------------------------
    new_history = state.get("message_history", [])[-10:]  # keep last 10

    new_history.append(f"User: {state['question']}")
    new_history.append(f"AI: {response.content}")

    return {
        "answer": response.content,
        "context": context,
        "message_history": new_history
    }

# -----------------------------
# SIMPLE ROUTER
# -----------------------------
def is_relevant(state: State):
    return {"relevant_docs": state.get("docs", [])}

# -----------------------------
# GRAPH
# -----------------------------
g = StateGraph(State)

g.add_node("retrieve", retrieve)
g.add_node("is_relevant", is_relevant)
g.add_node("generate_from_context", generate_from_context)

g.add_edge(START, "retrieve")
g.add_edge("retrieve", "is_relevant")
g.add_edge("is_relevant", "generate_from_context")
g.add_edge("generate_from_context", END)

app = g.compile()