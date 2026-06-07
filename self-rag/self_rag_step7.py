#!/usr/bin/env python
# coding: utf-8

from typing import List, TypedDict, Literal
from pydantic import BaseModel, Field

import os
import re
import pandas as pd

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError(
        "OPENAI_API_KEY is not set. Add it to self-rag/.env before running."
    )

# =========================================================
# LOAD DATA
# =========================================================
def extract_ids(text):
    # Normalize case so matching works regardless of how the user typed the id,
    # and tolerate the optional underscore some generators use (driver_45).
    t = text.upper()
    req = re.findall(r"REQ-[A-Z0-9]+", t)
    card = re.findall(r"CARD-\d+", t)
    user = re.findall(r"DRIVER_?\d+", t)
    return set(req + card + user)


# Captures an id that directly follows a first-person identity phrase, e.g.
# "I am driver002", "I'm driver002", "this is driver002", "my card is CARD-10011".
# A bare mention like "tell me about driver020" is NOT captured.
_identity_pattern = re.compile(
    r"(?:\bi\s*am\b|\bi'?m\b|\bthis is\b|"
    r"\bmy (?:user\s*id|driver\s*id|id|email|card)\b)\s*"
    r"(?:is|=|:|the|a|an|user)?\s*"
    # email first so its 'driver...' prefix isn't grabbed by the driver pattern
    r"([a-zA-Z0-9._%+-]+@shellfleet\.com|CARD-\d+|driver_?\d+)",
    re.IGNORECASE,
)


def detect_identity(text):
    """Extract a self-identification from a first-person statement.

    Returns a dict like {"user_id": "driver002"} when the user states who they
    are, or {} when the message is not a first-person identity claim.
    """
    ids = {}

    for match in _identity_pattern.finditer(text):
        value = match.group(1)
        low = value.lower()

        # check '@' before 'driver' since emails start with 'driver...' too
        if "@" in low:
            ids["email"] = low
        elif low.startswith("card"):
            ids["card_id"] = value.upper()
        elif low.startswith("driver"):
            ids["user_id"] = low

    return ids


def identity_context(identity):
    """Render a stored identity dict into a context string for prompts/retrieval."""
    if not identity:
        return ""

    parts = []
    if identity.get("user_id"):
        parts.append(f"user_id: {identity['user_id']}")
    if identity.get("email"):
        parts.append(f"email: {identity['email']}")
    if identity.get("card_id"):
        parts.append(f"card_id: {identity['card_id']}")

    if not parts:
        return ""

    return "Known user identity — " + ", ".join(parts) + "."


project_folder = os.path.join(
    os.path.dirname(__file__),
    "documents"
)

print("Project folder:", project_folder)

xlsx_files = [
    "EnhancedApplicationLog.xlsx",
    "EnhancedDBLog.xlsx",
    "EnhancedLogAnalytics.xlsx",
]

docs = []

for filename in xlsx_files:

    file_path = os.path.join(
        project_folder,
        filename
    )

    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"⚠️ Could not read {filename}: {e}")
        continue

    for _, row in df.iterrows():

        docs.append(
            Document(
                page_content=str(
                    row.get("Details", "")
                ),

                metadata={

                    # source
                    "source": filename,

                    # identifiers
                    "correlation_id": str(
                        row.get("CorrelationId", "")
                    ),

                    "user_id": str(
                        row.get("UserId", "")
                    ),

                    "email": str(
                        row.get("Email", "")
                    ),

                    "card_id": str(
                        row.get("CardId", "")
                    ),

                    # log metadata
                    "timestamp": str(
                        row.get("Timestamp", "")
                    ),

                    "module": str(
                        row.get("Module", "")
                    ),

                    "event": str(
                        row.get("Event", "")
                    ),

                    "level": str(
                        row.get(
                            "Level",
                            row.get("Status", "")
                        )
                    ),

                    "sql_operation": str(
                        row.get("SQL Operation", "")
                    ),
                }
            )
        )

print(f"Total documents loaded: {len(docs)}")

if not docs:
    raise RuntimeError(
        "No log documents loaded. Check the Enhanced*.xlsx files in documents/."
    )

print(
    docs[0].page_content[:500]
)

# =========================================================
# CHUNKING
# =========================================================

chunks = RecursiveCharacterTextSplitter(
    chunk_size=600,
    chunk_overlap=150
).split_documents(docs)

# =========================================================
# VECTOR STORE
# =========================================================

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large"
)

# Persist the index so we don't re-embed every doc on each run/reload.
# Delete the .faiss_index dir to force a rebuild after the logs change.
index_dir = os.path.join(
    os.path.dirname(__file__),
    ".faiss_index"
)

if os.path.isdir(index_dir):
    print(f"Loading cached FAISS index from {index_dir}")
    vector_store = FAISS.load_local(
        index_dir,
        embeddings,
        allow_dangerous_deserialization=True
    )
else:
    print("Building FAISS index (first run, embedding all docs)...")
    vector_store = FAISS.from_documents(
        chunks,
        embeddings
    )
    vector_store.save_local(index_dir)
    print(f"Saved FAISS index to {index_dir}")

retriever = vector_store.as_retriever(
    search_type="mmr",
    search_kwargs={
        "k": 20,
        "fetch_k": 50
    }
)

# =========================================================
# LLM
# =========================================================

openai_api_key = os.getenv(
    "OPENAI_API_KEY"
)

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=openai_api_key
)

# =========================================================
# STATE
# =========================================================

class State(TypedDict):

    question: str

    # conversation context (carried in from the frontend each turn)
    history: str
    user_context: str

    retrieval_query: str
    rewrite_tries: int

    need_retrieval: bool

    docs: List[Document]
    relevant_docs: List[Document]

    context: str
    answer: str

    from_memory: bool

    issup: Literal[
        "fully_supported",
        "partially_supported",
        "no_support"
    ]

    evidence: List[str]

    retries: int

    isuse: Literal[
        "useful",
        "not_useful"
    ]

    use_reason: str

# =========================================================
# DECIDE RETRIEVAL
# =========================================================

class RetrieveDecision(BaseModel):

    should_retrieve: bool = Field(
        ...,
        description="Whether retrieval is needed"
    )
decide_retrieval_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You decide whether retrieval is needed.\n"
            "Return JSON with key: should_retrieve (boolean).\n\n"

            "Guidelines:\n"
            "- should_retrieve=True if answering requires specific facts from log documents.\n"
            "- should_retrieve=True if the question references:\n"
            "  - user_id\n"
            "  - email\n"
            "  - card_id\n"
            "  - correlation_id / REQ ID\n"
            "  - exceptions\n"
            "  - transaction failures\n"
            "  - DB failures\n"
            "  - stack traces\n"
            "- should_retrieve=False for general explanations or definitions.\n"
            "- If unsure, choose True."
        ),

        (
            "human",
            "Question: {question}"
        ),
    ]
)

should_retrieve_llm = llm.with_structured_output(
    RetrieveDecision
)

class ConversationMemory:
    """Per-conversation Q&A cache: an exact-match list plus a semantic FAISS index.

    Create one instance per user session (see streamlit_frontend.py). The
    module-level _default_memory below is only a fallback for standalone runs,
    so memory is NOT shared across browser sessions.
    """

    # similarity_search_with_score returns L2 DISTANCE (lower = more similar),
    # not a similarity score. A hit must be strictly below this distance.
    MAX_DISTANCE = 0.85
    MIN_SHARED_WORDS = 3

    def __init__(self, embeddings):
        self.embeddings = embeddings
        self.store = []          # [{"question", "answer"}] for exact match
        self.vectorstore = None  # FAISS, lazily created on first save

    def search(self, question: str, scope: str = ""):

        # exact match (same question AND same identity scope)
        q = question.lower().strip()
        for item in self.store:
            if q == item["question"].lower().strip() and item.get("scope", "") == scope:
                print("✅ Exact memory hit")
                return item["answer"]

        # semantic match
        if self.vectorstore is None:
            return None

        results = self.vectorstore.similarity_search_with_score(question, k=1)
        if not results:
            return None

        doc, distance = results[0]
        print("Distance:", distance)

        if distance >= self.MAX_DISTANCE:
            return None

        # Identity scope must match: never reuse one identity's answer for
        # another (or a scoped answer for an unscoped question).
        if doc.metadata.get("scope", "") != scope:
            return None

        stored_question = doc.metadata["question"]
        stored_ids = extract_ids(stored_question)
        current_ids = extract_ids(question)

        # A shared identifier (REQ / CARD / driver) ties both questions to the
        # same entity -> safe to reuse the cached answer.
        if stored_ids & current_ids:
            print("✅ Strong ID memory hit")
            return doc.metadata["answer"]

        # Fuzzy word-overlap fallback ONLY when neither question mentions an
        # identifier. Otherwise two questions about *different* entities
        # (e.g. driver10 vs driver20) could share enough words to wrongly
        # reuse each other's answer.
        if not stored_ids and not current_ids:
            shared_words = (
                set(stored_question.lower().split())
                & set(question.lower().split())
            )
            if len(shared_words) >= self.MIN_SHARED_WORDS:
                print("⚠️ Weak semantic hit")
                return doc.metadata["answer"]

        return None

    def save(self, question: str, answer: str, scope: str = ""):
        self.store.append(
            {"question": question, "answer": answer, "scope": scope}
        )

        # Embed the QUESTION only so similarity reflects the question, not the
        # answer text or the identity scope (scope is matched separately).
        metadata = {"question": question, "answer": answer, "scope": scope}

        if self.vectorstore is None:
            self.vectorstore = FAISS.from_texts(
                [question], self.embeddings, metadatas=[metadata]
            )
        else:
            self.vectorstore.add_texts(texts=[question], metadatas=[metadata])

        print("💾 Answer saved to memory")


# Fallback memory for standalone runs; the Streamlit frontend injects a
# per-session instance via config={"configurable": {"memory": ...}}.
_default_memory = ConversationMemory(embeddings)


def new_memory():
    """Factory for a fresh per-session memory (used by the Streamlit frontend)."""
    return ConversationMemory(embeddings)


def get_memory(config):
    """Return the session-scoped memory from the run config, or the fallback."""
    if config:
        mem = config.get("configurable", {}).get("memory")
        if mem is not None:
            return mem
    return _default_memory

def decide_retrieval(state: State):

    decision = should_retrieve_llm.invoke(
        decide_retrieval_prompt.format_messages(
            question=state["question"]
        )
    )

    return {
        "need_retrieval":
        decision.should_retrieve
    }

def route_after_decide(
    state: State
) -> Literal[
    "generate_direct",
    "retrieve"
]:

    return (
        "retrieve"
        if state["need_retrieval"]
        else "generate_direct"
    )

# =========================================================
# DIRECT ANSWER
# =========================================================

direct_generation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful assistant for the ShellFleet log analysis tool.\n"
            "Answer using your general knowledge and the conversation context below.\n\n"

            "USER CONTEXT (facts the user has stated about themselves this session):\n"
            "{user_context}\n\n"

            "- If the user asks about their own identity (e.g. 'who am I') and the "
            "USER CONTEXT contains it, answer directly from that context.\n"
            "- If the question requires specific details from logs, DB records, "
            "application traces, analytics, or identifiers that are NOT in the user "
            "context, respond with:\n"
            "'I don't know based on my general knowledge.'"
        ),

        (
            "human",
            "Conversation so far:\n{history}\n\n"
            "Question: {question}"
        ),
    ]
)

def generate_direct(state: State, config):

    memory = get_memory(config)
    scope = state.get("user_context") or ""

    # CHECK MEMORY FIRST
    memory_answer = memory.search(state["question"], scope=scope)

    if memory_answer:

        print("✅ Answer retrieved from memory")

        return {
            "answer": memory_answer,
            "from_memory": True
        }

    # NORMAL LLM FLOW
    out = llm.invoke(
        direct_generation_prompt.format_messages(
            question=state["question"],
            user_context=state.get("user_context") or "(none provided)",
            history=state.get("history") or "(no prior messages)"
        )
    )

    memory.save(state["question"], out.content, scope=scope)

    return {
        "answer": out.content,
        "from_memory": False
    }

# =========================================================
# RETRIEVE
# =========================================================

def retrieve(state: State):

    question_text = (
        state.get("retrieval_query")
        or state["question"]
    )

    # Append the known user identity so pronoun questions ("why did MY
    # transaction fail?") resolve to the user's identifiers. The question is
    # scanned first, so an explicit id in the question still takes precedence.
    identity = state.get("user_context", "") or ""
    scan = f"{question_text} {identity}".strip()

    # -----------------------------------------------------
    # CORRELATION ID
    # -----------------------------------------------------

    cid_match = re.search(
        r"(REQ-[A-Z0-9]+|CID-[A-Z0-9]+)",
        scan,
        re.IGNORECASE
    )

    if cid_match:

        cid = cid_match.group(1).upper()

        matched = [
            d for d in docs
            if d.metadata.get(
                "correlation_id",
                ""
            ).upper() == cid
        ]

        if matched:
            return {"docs": matched}

    # -----------------------------------------------------
    # USER ID
    # -----------------------------------------------------

    user_match = re.search(
        r"(driver_?\d+)",
        scan,
        re.IGNORECASE
    )

    if user_match:

        user_id = user_match.group(1).lower()

        matched = [
            d for d in docs
            if d.metadata.get(
                "user_id",
                ""
            ).lower() == user_id
        ]

        if matched:
            return {"docs": matched}

    # -----------------------------------------------------
    # EMAIL
    # -----------------------------------------------------

    email_match = re.search(
        r"([a-zA-Z0-9._%+-]+@shellfleet\.com)",
        scan,
        re.IGNORECASE
    )

    if email_match:

        email = email_match.group(1).lower()

        matched = [
            d for d in docs
            if d.metadata.get(
                "email",
                ""
            ).lower() == email
        ]

        if matched:
            return {"docs": matched}

    # -----------------------------------------------------
    # CARD ID
    # -----------------------------------------------------

    card_match = re.search(
        r"(CARD-\d+)",
        scan,
        re.IGNORECASE
    )

    if card_match:

        card_id = card_match.group(1).upper()

        matched = [
            d for d in docs
            if d.metadata.get(
                "card_id",
                ""
            ).upper() == card_id
        ]

        if matched:
            return {"docs": matched}

    # -----------------------------------------------------
    # VECTOR SEARCH (fallback)
    # -----------------------------------------------------

    return {
        "docs": retriever.invoke(question_text)
    }

# =========================================================
# RELEVANCE FILTER
# =========================================================

class RelevanceDecision(BaseModel):

    relevant_indices: List[int] = Field(
        default_factory=list,
        description="0-based indices of the documents relevant to the issue"
    )
is_relevant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an AI assistant diagnosing enterprise application issues from logs.\n"
            "Return JSON matching the schema.\n\n"

            "You will be given a user-reported issue and logs from:\n"
            "- Application logs\n"
            "- DB logs\n"
            "- Analytics logs\n\n"

            "Your task is to determine which of the numbered documents are relevant to the user's issue.\n"
            "Return relevant_indices: a JSON list of the 0-based indices of the relevant documents.\n\n"

            "IMPORTANT IDENTIFIERS:\n"
            "- correlation_id / REQ ID\n"
            "- user_id\n"
            "- email\n"
            "- card_id\n\n"

            "Guidelines:\n"
            "- If correlation_id matches the question, mark relevant.\n"
            "- If user_id matches the question, mark relevant.\n"
            "- If email matches the question, mark relevant.\n"
            "- If card_id matches the question, mark relevant.\n"
            "- If stack traces, exceptions, failures, or DB issues are related, mark relevant.\n"
            "- Cross-reference logs across systems.\n"
            "- Focus heavily on exceptions and transaction failures.\n"
            "- If unsure, return is_relevant=true.\n\n"

            "Examples:\n"
            "- NullReferenceException -> possible application failure.\n"
            "- SQL duplicate key -> DB insert/update failure.\n"
            "- TimeoutException -> infrastructure/API timeout.\n"
            "- InvalidCredentialException -> authentication failure.\n"
            "- TokenExpiredException -> password reset/session issue.\n\n"

            "Do NOT fabricate root causes or fixes.\n"
            "Only determine relevance."
        ),

        (
            "human",
            "Question:\n{question}\n\n"
            "Documents (each prefixed by its [index]):\n{documents}"
        ),
    ]
)


relevance_llm = llm.with_structured_output(
    RelevanceDecision
)

def is_relevant(state: State):

    docs = state.get("docs", [])

    if not docs:
        return {"relevant_docs": []}

    # Single batched call instead of one LLM call per document.
    listing = "\n\n".join(
        f"[{i}] {d.page_content}"
        for i, d in enumerate(docs)
    )

    decision = relevance_llm.invoke(
        is_relevant_prompt.format_messages(
            question=state["question"],
            documents=listing
        )
    )

    keep = set(decision.relevant_indices)

    relevant_docs = [
        d for i, d in enumerate(docs)
        if i in keep
    ]

    return {
        "relevant_docs": relevant_docs
    }

def route_after_relevance(
    state: State
) -> Literal[
    "generate_from_context",
    "no_answer_found"
]:

    if (
        state.get("relevant_docs")
        and len(state["relevant_docs"]) > 0
    ):
        return "generate_from_context"

    return "no_answer_found"

# =========================================================
# GENERATE FROM CONTEXT
# =========================================================
rag_generation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an AI assistant diagnosing enterprise application issues from logs.\n\n"

            "You will receive a CONTEXT block containing:\n"
            "- Application logs\n"
            "- DB logs\n"
            "- Log analytics traces\n\n"

            "IMPORTANT IDENTIFIERS:\n"
            "- correlation_id / REQ ID\n"
            "- user_id\n"
            "- email\n"
            "- card_id\n\n"

            "Task:\n"
            "1. Analyze the logs carefully.\n"
            "2. Identify the exact root cause of the issue.\n"
            "3. Identify the exact exception or failure.\n"
            "4. Identify affected user/email/card.\n"
            "5. Explain the sequence of events.\n"
            "6. Mention DB failures if present.\n"
            "7. Suggest likely fix ONLY if evidence exists in logs.\n"
            "8. Correlate events across application, DB, and analytics logs.\n\n"

            "Guidelines:\n"
            "- Prioritize matching correlation_id, user_id, email, and card_id.\n"
            "- Focus heavily on stack traces and exceptions.\n"
            "- If multiple failures exist, identify the primary root cause.\n"
            "- If no fix can be determined from logs, respond with:\n"
            "'No code fix identified from logs'.\n"
            "- Do NOT hallucinate.\n"
            "- Do NOT mention 'context' or 'provided logs' in the response.\n"
            "- Use ONLY evidence from logs.\n"
            "- If USER CONTEXT identifies the user, resolve pronouns like 'my' or "
            "'me' to that identity and address the answer to them."
        ),

        (
            "human",
            "USER CONTEXT:\n{user_context}\n\n"
            "Conversation so far:\n{history}\n\n"
            "Question:\n{question}\n\n"
            "Context:\n{context}"
        ),
    ]
)

def generate_from_context(state: State, config):

    memory = get_memory(config)
    scope = state.get("user_context") or ""

    # CHECK MEMORY FIRST
    memory_answer = memory.search(state["question"], scope=scope)

    if memory_answer:

        print("✅ Answer retrieved from memory")

        return {
            "answer": memory_answer,
            "context": "memory",
            "from_memory": True
        }

    context = "\n\n---\n\n".join(
        [
            d.page_content
            for d in state.get(
                "relevant_docs",
                []
            )
        ]
    ).strip()

    if not context:

        return {
            "answer": "No answer found.",
            "context": "",
            "from_memory": False
        }

    out = llm.invoke(
        rag_generation_prompt.format_messages(
            question=state["question"],
            context=context,
            user_context=state.get("user_context") or "(none provided)",
            history=state.get("history") or "(no prior messages)"
        )
    )

    memory.save(state["question"], out.content, scope=scope)

    return {
        "answer": out.content,
        "context": context,
        "from_memory": False
    }

def no_answer_found(state: State):

    return {
        "answer": "No answer found.",
        "context": ""
    }

def route_after_generate(
    state: State
) -> Literal[
    "is_sup",
    "END"
]:

    # A cached answer was already verified when first produced; skip the
    # grounding/usefulness loop (its context is "memory", not real logs).
    if state.get("from_memory"):
        return "END"

    return "is_sup"

# =========================================================
# ISSUP
# =========================================================

class IsSUPDecision(BaseModel):

    issup: Literal[
        "fully_supported",
        "partially_supported",
        "no_support"
    ]

    evidence: List[str] = Field(
        default_factory=list
    )
issup_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are verifying whether the generated answer is fully supported by the logs.\n\n"

            "Return JSON with:\n"
            "- issup\n"
            "- evidence\n\n"

            "issup must be one of:\n"
            "- fully_supported\n"
            "- partially_supported\n"
            "- no_support\n\n"

            "How to decide:\n"
            "- fully_supported:\n"
            "  The logs directly support the answer with matching evidence.\n"
            "  Matching correlation_id, user_id, email, or card_id strongly supports this.\n"
            "- partially_supported:\n"
            "  The logs are related but do not fully confirm the answer.\n"
            "- no_support:\n"
            "  The logs do not support the answer.\n\n"

            "Rules:\n"
            "- Be strict.\n"
            "- Verify exceptions, stack traces, DB failures, and event sequences.\n"
            "- Include up to 3 short direct evidence snippets.\n"
            "- Do NOT use outside knowledge.\n"
            "- Do NOT infer unsupported conclusions."
        ),

        (
            "human",
            "Question:\n{question}\n\n"
            "Answer:\n{answer}\n\n"
            "Context:\n{context}"
        ),
    ]
)

issup_llm = llm.with_structured_output(
    IsSUPDecision
)

def is_sup(state: State):

    decision = issup_llm.invoke(
        issup_prompt.format_messages(
            question=state["question"],
            answer=state.get("answer", ""),
            context=state.get("context", "")
        )
    )

    return {
        "issup": decision.issup,
        "evidence": decision.evidence
    }

MAX_RETRIES = 10

def route_after_issup(
    state: State
) -> Literal[
    "accept_answer",
    "revise_answer"
]:

    if state.get("issup") == "fully_supported":
        return "accept_answer"

    if state.get("retries", 0) >= MAX_RETRIES:
        return "accept_answer"

    return "revise_answer"

# =========================================================
# ACCEPT
# =========================================================

def accept_answer(state: State):
    return {}

# =========================================================
# REVISE
# =========================================================
revise_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a STRICT reviser.\n\n"

            "You must revise the answer using ONLY evidence from logs.\n\n"

            "Rules:\n"
            "- Use ONLY the provided context.\n"
            "- Remove unsupported statements.\n"
            "- Keep stack traces, exceptions, DB failures, and identifiers accurate.\n"
            "- Do NOT hallucinate.\n"
            "- Do NOT add assumptions.\n"
            "- Do NOT use outside knowledge.\n"
            "- If evidence is weak, keep answer conservative."
        ),

        (
            "human",
            "Question:\n{question}\n\n"
            "Current Answer:\n{answer}\n\n"
            "Context:\n{context}"
        ),
    ]
)

def revise_answer(state: State):

    out = llm.invoke(
        revise_prompt.format_messages(
            question=state["question"],
            answer=state.get("answer", ""),
            context=state.get("context", "")
        )
    )

    return {
        "answer": out.content,
        "retries": state.get("retries", 0) + 1
    }

# =========================================================
# ISUSE
# =========================================================

class IsUSEDecision(BaseModel):

    isuse: Literal[
        "useful",
        "not_useful"
    ]

    reason: str

isuse_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are judging whether the generated answer is useful to the user.\n\n"

            "Goal:\n"
            "- Determine whether the answer actually addresses the user's issue.\n\n"

            "Return JSON with:\n"
            "- isuse\n"
            "- reason\n\n"

            "isuse must be:\n"
            "- useful\n"
            "- not_useful\n\n"

            "Rules:\n"
            "- useful:\n"
            "  The answer clearly identifies the issue, root cause, failure, or affected entities.\n"
            "- useful:\n"
            "  The answer references correct user_id, email, card_id, or correlation_id if present.\n"
            "- useful:\n"
            "  The answer explains the exception or event sequence.\n"
            "- not_useful:\n"
            "  The answer is generic, vague, unrelated, or incomplete.\n"
            "- not_useful:\n"
            "  The answer avoids answering the actual question.\n"
            "- Do NOT verify factual grounding here.\n"
            "- Only check usefulness."
        ),

        (
            "human",
            "Question:\n{question}\n\n"
            "Answer:\n{answer}"
        ),
    ]
)

isuse_llm = llm.with_structured_output(
    IsUSEDecision
)

def is_use(state: State):

    decision = isuse_llm.invoke(
        isuse_prompt.format_messages(
            question=state["question"],
            answer=state.get("answer", "")
        )
    )

    return {
        "isuse": decision.isuse,
        "use_reason": decision.reason
    }

MAX_REWRITE_TRIES = 3

def route_after_isuse(
    state: State
) -> Literal[
    "END",
    "rewrite_question",
    "no_answer_found"
]:

    if state.get("isuse") == "useful":
        return "END"

    if (
        state.get("rewrite_tries", 0)
        >= MAX_REWRITE_TRIES
    ):
        return "no_answer_found"

    return "rewrite_question"

# =========================================================
# REWRITE QUESTION
# =========================================================

class RewriteDecision(BaseModel):

    retrieval_query: str
rewrite_for_retrieval_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Rewrite the user's issue into a retrieval-optimized query for enterprise log analysis.\n\n"

            "The logs may contain:\n"
            "- application failures\n"
            "- DB failures\n"
            "- transaction failures\n"
            "- authentication issues\n"
            "- analytics traces\n"
            "- stack traces\n\n"

            "IMPORTANT IDENTIFIERS:\n"
            "- correlation_id / REQ ID\n"
            "- user_id\n"
            "- email\n"
            "- card_id\n"
            "- controller names\n"
            "- exception names\n"
            "- module names\n\n"

            "Rules:\n"
            "- Preserve all important identifiers.\n"
            "- Preserve exception names.\n"
            "- Preserve stack trace keywords.\n"
            "- Add high-signal retrieval keywords.\n"
            "- Remove filler words.\n"
            "- Keep query concise.\n"
            "- Do NOT answer the question.\n\n"

            "Examples:\n"
            "'driver45 transaction failed during card validation'\n"
            "-> 'driver45 CardValidationFailed transaction exception card log'\n\n"

            "'REQ-AB1234 login timeout issue'\n"
            "-> 'REQ-AB1234 Login TimeoutException AuthController session timeout log'\n\n"

            "Return JSON:\n"
            "{{\"retrieval_query\": \"...\"}}"
        ),

        (
            "human",
            "QUESTION:\n{question}\n\n"
            "Previous retrieval query:\n{retrieval_query}\n\n"
            "Answer:\n{answer}"
        ),
    ]
)

rewrite_llm = llm.with_structured_output(
    RewriteDecision
)

def rewrite_question(state: State):

    decision = rewrite_llm.invoke(
        rewrite_for_retrieval_prompt.format_messages(
            question=state["question"],
            retrieval_query=state.get(
                "retrieval_query",
                ""
            ),
            answer=state.get("answer", "")
        )
    )

    return {

        "retrieval_query":
        decision.retrieval_query,

        "rewrite_tries":
        state.get("rewrite_tries", 0) + 1,

        "docs": [],
        "relevant_docs": [],
        "context": "",
    }

# =========================================================
# GRAPH
# =========================================================

g = StateGraph(State)

g.add_node(
    "decide_retrieval",
    decide_retrieval
)

g.add_node(
    "generate_direct",
    generate_direct
)

g.add_node(
    "retrieve",
    retrieve
)

g.add_node(
    "is_relevant",
    is_relevant
)

g.add_node(
    "generate_from_context",
    generate_from_context
)

g.add_node(
    "no_answer_found",
    no_answer_found
)

g.add_node(
    "is_sup",
    is_sup
)

g.add_node(
    "revise_answer",
    revise_answer
)

g.add_node(
    "is_use",
    is_use
)

g.add_node(
    "rewrite_question",
    rewrite_question
)

# =========================================================
# EDGES
# =========================================================

g.add_edge(
    START,
    "decide_retrieval"
)

g.add_conditional_edges(
    "decide_retrieval",

    route_after_decide,

    {
        "generate_direct":
        "generate_direct",

        "retrieve":
        "retrieve",
    },
)

g.add_edge(
    "generate_direct",
    END
)

g.add_edge(
    "retrieve",
    "is_relevant"
)

g.add_conditional_edges(
    "is_relevant",

    route_after_relevance,

    {
        "generate_from_context":
        "generate_from_context",

        "no_answer_found":
        "no_answer_found",
    },
)

g.add_conditional_edges(
    "generate_from_context",

    route_after_generate,

    {
        "is_sup": "is_sup",
        "END": END,
    },
)

g.add_conditional_edges(
    "is_sup",

    route_after_issup,

    {
        "accept_answer":
        "is_use",

        "revise_answer":
        "revise_answer",
    },
)

g.add_edge(
    "revise_answer",
    "is_sup"
)

g.add_conditional_edges(
    "is_use",

    route_after_isuse,

    {
        "END":
        END,

        "rewrite_question":
        "rewrite_question",

        "no_answer_found":
        "no_answer_found",
    },
)

g.add_edge(
    "rewrite_question",
    "retrieve"
)

g.add_edge(
    "no_answer_found",
    END
)

# =========================================================
# COMPILE
# =========================================================

app = g.compile()

print("✅ Graph compiled successfully")