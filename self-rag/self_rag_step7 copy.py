#!/usr/bin/env python
# coding: utf-8

# In[48]:


from typing import List, TypedDict, Literal
from pydantic import BaseModel, Field
import os
import pprint
from langchain_community.document_loaders import UnstructuredExcelLoader

#from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate

from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

load_dotenv()


# In[49]:


# -----------------------------
# Load + chunk + embed
# -----------------------------
# Base project folder (relative path from your working directory)
project_folder = os.path.join(os.path.dirname(__file__), "documents")
print("Project folder:", project_folder)
# In[49]:
# List of PDF filenames
# pdf_files = [
#     "Company_Policies.pdf",
#     "Company_Profile.pdf",
#     "Product_and_Pricing.pdf",
# ]

xlsx_files = [
    "ApplicationLog.xlsx",
    "DBLog.xlsx",
    "LogAnalytics.xlsx",
]

# # Load all PDFs generically
# docs = []
# for filename in pdf_files:
#     file_path = os.path.join(project_folder, filename)
#     loader = PyPDFLoader(file_path)
#     docs.extend(loader.load())
import pandas as pd

docs = []
for filename in xlsx_files:
    file_path = os.path.join(project_folder, filename)
    loader = UnstructuredExcelLoader(file_path)
    docs.extend(loader.load())

# In[49]:
print(f"Total documents loaded: {len(docs)}")
print(f"{docs[0].page_content[:500]}...")  # print the first 500 characters of the first document as a sample




# In[50]:


chunks = RecursiveCharacterTextSplitter(
    chunk_size=600, chunk_overlap=150
).split_documents(docs)


# In[51]:


embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
vector_store = FAISS.from_documents(chunks, embeddings)
retriever = vector_store.as_retriever(search_kwargs={"k": 4})


# In[52]:


openai_api_key = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0,api_key=openai_api_key)


# In[53]:


# -----------------------------
# Graph State
# -----------------------------
class State(TypedDict):
    question: str

    # ✅ NEW: what we actually send to vector retriever
    retrieval_query: str
    rewrite_tries: int

    need_retrieval: bool
    docs: List[Document]
    relevant_docs: List[Document]
    context: str
    answer: str

    # Post-generation verification
    issup: Literal["fully_supported", "partially_supported", "no_support"]
    evidence: List[str]

    retries: int

    isuse: Literal["useful", "not_useful"]
    use_reason: str


# In[54]:


# -----------------------------
# 1) Decide retrieval
# -----------------------------
class RetrieveDecision(BaseModel):
    should_retrieve: bool = Field(
        ...,
        description="True if external documents are needed to answer reliably, else False."
    )

decide_retrieval_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You decide whether retrieval is needed.\n"
            "Return JSON with key: should_retrieve (boolean).\n\n"
            "Guidelines:\n"
            "- should_retrieve=True if answering requires specific facts from company documents.\n"
            "- should_retrieve=False for general explanations/definitions.\n"
            "- If unsure, choose True."
        ),
        ("human", "Question: {question}"),
    ]
)

should_retrieve_llm = llm.with_structured_output(RetrieveDecision)

def decide_retrieval(state: State):
    decision: RetrieveDecision = should_retrieve_llm.invoke(
        decide_retrieval_prompt.format_messages(question=state["question"])
    )
    return {"need_retrieval": decision.should_retrieve}

def route_after_decide(state: State) -> Literal["generate_direct", "retrieve"]:
    return "retrieve" if state["need_retrieval"] else "generate_direct"


# In[55]:


# -----------------------------
# 2) Direct answer (no retrieval)
# -----------------------------
direct_generation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Answer using only your general knowledge.\n"
            "If it requires specific other info, say:\n"
            "'I don't know based on my general knowledge.'"
        ),
        ("human", "{question}"),
    ]
)

def generate_direct(state: State):
    out = llm.invoke(direct_generation_prompt.format_messages(question=state["question"]))
    return {"answer": out.content}


# In[56]:


# -----------------------------
# 3) Retrieve
# -----------------------------
def retrieve(state: State):
    q = state.get("retrieval_query") or state["question"]
    return {"docs": retriever.invoke(q)}



# In[57]:


# -----------------------------
# 4) Relevance filter (strict)
# -----------------------------
class RelevanceDecision(BaseModel):
    is_relevant: bool = Field(
        ...,
        description="True ONLY if the document contains info that can directly answer the question."
    )

is_relevant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an AI assistant diagnosing application issues from logs.\n"
            "Return JSON matching the schema.\n\n"
            "You will be given a user-reported issue and multiple logs (DB log, application log, log analytical log).\n"
            "Your task is to analyze the logs and determine what could be the root cause of the issue.\n\n"
            "Guidelines:\n"
            "- Look for errors, exceptions, or anomalies in the logs.\n"
            "- Cross-reference the user’s issue with log entries.\n"
            "- If a likely cause is found, explain it clearly.\n"
            "- If no cause can be identified, When unsure, return is_relevant=true.'\n\n"
            "Examples:\n"
            "- If logs show NullReferenceException, suggest adding null checks.\n"
            "- If logs show SQL constraint violation, suggest fixing DB schema or query.\n"
            "- If logs show missing dependency, suggest installing the package.\n\n"
            "Do NOT fabricate fixes. Only suggest when evidence exists in logs."

        ),
        ("human", "Question:\n{question}\n\nDocument:\n{document}"),
    ]
)


relevance_llm = llm.with_structured_output(RelevanceDecision)

def is_relevant(state: State):
    relevant_docs: List[Document] = []
    for doc in state.get("docs", []):
        decision: RelevanceDecision = relevance_llm.invoke(
            is_relevant_prompt.format_messages(
                question=state["question"],
                document=doc.page_content,
            )
        )
        if decision.is_relevant:
            relevant_docs.append(doc)
    return {"relevant_docs": relevant_docs}

def route_after_relevance(state: State) -> Literal["generate_from_context", "no_answer_found"]:
    if state.get("relevant_docs") and len(state["relevant_docs"]) > 0:
        return "generate_from_context"
    return "no_answer_found"


# In[58]:


# -----------------------------
# 5) Generate from context
# -----------------------------
rag_generation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an AI assistant diagnosing application issues from logs.\n\n"
            "You will receive a CONTEXT block containing DB logs, application logs, and log analytical logs.\n"
            "Task:\n"
            "Read the logs and generate a context relevant to the queried error.\n"
            "Identify what could be the root cause of the issue based on the evidence in the logs.\n"
            "If a likely fix exists, suggest it clearly.\n"
            "If no fix can be identified, respond with: 'No code to fix for the given issue'.\n\n"
            "Do not mention that you are receiving logs or context in your answer."

        ),
        ("human", "Question:\n{question}\n\nContext:\n{context}"),
    ]
)

def generate_from_context(state: State):
    context = "\n\n---\n\n".join([d.page_content for d in state.get("relevant_docs", [])]).strip()
    if not context:
        return {"answer": "No answer found.", "context": ""}
    out = llm.invoke(
        rag_generation_prompt.format_messages(question=state["question"], context=context)
    )
    return {"answer": out.content, "context": context}

def no_answer_found(state: State):
    return {"answer": "No answer found.", "context": ""}


# In[59]:


# -----------------------------
# 6) IsSUP verify + revise loop
# -----------------------------
class IsSUPDecision(BaseModel):
    issup: Literal["fully_supported", "partially_supported", "no_support"]
    evidence: List[str] = Field(default_factory=list)

issup_prompt = ChatPromptTemplate.from_messages(
    [
        (
           "system",
            "You are verifying whether the ERROR identified by the LLM in the logs is supported and relevant to the user-reported issue.\n"
            "Return JSON with keys: issup, evidence.\n"
            "issup must be one of: fully_supported, partially_supported, no_support.\n\n"
            "How to decide issup:\n"
            "- fully_supported:\n"
            "  The error identified in the logs directly matches the user’s reported issue with clear evidence.\n"
            "- partially_supported:\n"
            "  The error identified in the logs is related to the user’s issue but does not fully confirm it.\n"
            "- no_support:\n"
            "  The error identified in the logs is not relevant to the user’s reported issue.\n\n"
            "Rules:\n"
            "- Be strict: if the log evidence only partially overlaps with the user’s issue, choose partially_supported.\n"
            "- If the logs are unrelated or do not confirm the user’s issue, choose no_support.\n"
            "- Evidence: include up to 3 short direct quotes from the logs/context that support the decision.\n"
            "- Do not use outside knowledge."
        ),
        (
            "human",
            "Question:\n{question}\n\n"
            "Answer:\n{answer}\n\n"
            "Context:\n{context}\n"
        ),
    ]
)



issup_llm = llm.with_structured_output(IsSUPDecision)

def is_sup(state: State):
    decision: IsSUPDecision = issup_llm.invoke(
        issup_prompt.format_messages(
            question=state["question"],
            answer=state.get("answer", ""),
            context=state.get("context", ""),
        )
    )
    return {"issup": decision.issup, "evidence": decision.evidence}


MAX_RETRIES = 10

def route_after_issup(state: State) -> Literal["accept_answer", "revise_answer"]:
    # fully supported -> move forward to IsUSE (via "accept_answer" label)
    if state.get("issup") == "fully_supported":
        return "accept_answer"

    if state.get("retries", 0) >= MAX_RETRIES:
        return "accept_answer"  # will go to is_use, then likely not_useful -> no_answer_found

    return "revise_answer"





# In[60]:


def accept_answer(state: State):
    return {}  # keep answer as-is


# In[61]:


revise_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a STRICT reviser.\n\n"
            "You must output based on the following format:\n\n"
            "FORMAT (quote-only answer):\n"
            "- <direct quote from the CONTEXT>\n"
            "- <direct quote from the CONTEXT>\n\n"
            "Rules:\n"
            "- Use ONLY the CONTEXT.\n"
            "- Do NOT add any new words besides bullet dashes and the quotes themselves.\n"
            "- Do NOT explain anything.\n"
            "- Do NOT say 'context', 'not mentioned', 'does not mention', 'not provided', etc.\n"
        ),
        (
            "human",
            "Question:\n{question}\n\n"
            "Current Answer:\n{answer}\n\n"
            "CONTEXT:\n{context}"
        ),
    ]
)



def revise_answer(state: State):
    out = llm.invoke(
        revise_prompt.format_messages(
            question=state["question"],
            answer=state.get("answer", ""),
            context=state.get("context", ""),
        )
    )
    return {
        "answer": out.content,
        "retries": state.get("retries", 0) + 1,  # ✅ increment
    }



# In[62]:


class IsUSEDecision(BaseModel):
    isuse: Literal["useful", "not_useful"]
    reason: str = Field(..., description="Short reason in 1 line.")

isuse_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are judging USEFULNESS of the ANSWER for the QUESTION.\n\n"
            "Goal:\n"
            "- Decide if the answer actually addresses what the user asked.\n\n"
            "Return JSON with keys: isuse, reason.\n"
            "isuse must be one of: useful, not_useful.\n\n"
            "Rules:\n"
            "- useful: The answer directly answers the question or provides the requested specific info.\n"
            "- not_useful: The answer is generic, off-topic, or only gives related background without answering.\n"
            "- Do NOT use outside knowledge.\n"
            "- Do NOT re-check grounding (IsSUP already did that). Only check: 'Did we answer the question?'\n"
            "- Keep reason to 1 short line."
        ),
        (
            "human",
            "Question:\n{question}\n\nAnswer:\n{answer}"
        ),
    ]
)

isuse_llm = llm.with_structured_output(IsUSEDecision)

def is_use(state: State):
    decision: IsUSEDecision = isuse_llm.invoke(
        isuse_prompt.format_messages(
            question=state["question"],
            answer=state.get("answer", ""),
        )
    )
    return {"isuse": decision.isuse, "use_reason": decision.reason}

MAX_REWRITE_TRIES = 3  # tune (2–4 is usually fine)

def route_after_isuse(state: State) -> Literal["END", "rewrite_question", "no_answer_found"]:
    if state.get("isuse") == "useful":
        return "END"

    if state.get("rewrite_tries", 0) >= MAX_REWRITE_TRIES:
        return "no_answer_found"

    return "rewrite_question"




# In[63]:


class RewriteDecision(BaseModel):
    retrieval_query: str = Field(
        ...,
        description="Rewritten query optimized for vector retrieval against internal company PDFs."
    )

rewrite_for_retrieval_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Rewrite the user's ERROR description into a query optimized for vector retrieval over APPLICATION LOGS (DB log, application log, log analytical log).\n\n"
            "Rules:\n"
            "- Keep it short (6–16 words).\n"
            "- Preserve key entities (e.g., module names, controller names, error types).\n"
            "- Add 2–5 high-signal keywords that likely appear in logs (e.g., exception, stack trace, null, timeout, SQL).\n"
            "- Remove filler words.\n"
            "- Do NOT answer the error.\n"
            "- Output JSON with key: retrieval_query\n\n"
            "Examples:\n"
            "Error: 'NullReferenceException in UserController when saving user data'\n"
            "-> {{'retrieval_query': 'UserController NullReferenceException save user data log error'}}\n\n"
            "Error: 'SQL constraint violation in Card module during transaction'\n"
            "-> {{'retrieval_query': 'Card module SQL constraint violation transaction DB log'}}"
        ),
        (
            "human",
            "QUESTION:\n{question}\n\n"
            "Previous retrieval query:\n{retrieval_query}\n\n"
            "Answer (if any):\n{answer}"
        ),
    ]
)



rewrite_llm = llm.with_structured_output(RewriteDecision)

def rewrite_question(state: State):
    decision: RewriteDecision = rewrite_llm.invoke(
        rewrite_for_retrieval_prompt.format_messages(
            question=state["question"],
            retrieval_query=state.get("retrieval_query", ""),
            answer=state.get("answer", ""),
        )
    )

    return {
        "retrieval_query": decision.retrieval_query,
        "rewrite_tries": state.get("rewrite_tries", 0) + 1,
        # ✅ optional: reset these so next pass is clean
        "docs": [],
        "relevant_docs": [],
        "context": "",
    }


# In[64]:


# -----------------------------
# Build graph (UPDATED: IsUSE -> if not useful -> rewrite -> retrieve; else END)
# -----------------------------
g = StateGraph(State)

# --------------------
# Nodes
# --------------------
g.add_node("decide_retrieval", decide_retrieval)
g.add_node("generate_direct", generate_direct)
g.add_node("retrieve", retrieve)

g.add_node("is_relevant", is_relevant)
g.add_node("generate_from_context", generate_from_context)
g.add_node("no_answer_found", no_answer_found)

# IsSUP + revise loop
g.add_node("is_sup", is_sup)
g.add_node("revise_answer", revise_answer)

# IsUSE
g.add_node("is_use", is_use)

# ✅ NEW: rewrite question for better retrieval
g.add_node("rewrite_question", rewrite_question)

# --------------------
# Edges
# --------------------
g.add_edge(START, "decide_retrieval")

g.add_conditional_edges(
    "decide_retrieval",
    route_after_decide,
    {"generate_direct": "generate_direct", "retrieve": "retrieve"},
)

g.add_edge("generate_direct", END)

# Retrieve -> relevance -> (generate | no_answer_found)
g.add_edge("retrieve", "is_relevant")

g.add_conditional_edges(
    "is_relevant",
    route_after_relevance,
    {
        "generate_from_context": "generate_from_context",
        "no_answer_found": "no_answer_found",
    },
)

g.add_edge("no_answer_found", END)

# --------------------
# Generate -> IsSUP -> (IsUSE | revise) loop
# --------------------
g.add_edge("generate_from_context", "is_sup")

g.add_conditional_edges(
    "is_sup",
    route_after_issup,
    {
        "accept_answer": "is_use",      # fully_supported (or max retries) -> go to IsUSE
        "revise_answer": "revise_answer",
    },
)

g.add_edge("revise_answer", "is_sup")  # 🔁 loop back to IsSUP

# --------------------
# IsUSE routing
#   - useful -> END
#   - not_useful -> rewrite_question -> retrieve (try again)
#   - give up -> no_answer_found -> END
# --------------------
g.add_conditional_edges(
    "is_use",
    route_after_isuse,
    {
        "END": END,
        "rewrite_question": "rewrite_question",
        "no_answer_found": "no_answer_found",
    },
)

# rewrite -> retrieve -> relevance -> ...
g.add_edge("rewrite_question", "retrieve")
# In[64]:
app = g.compile()
app




# In[65]:


# -----------------------------
# Run the graph
# -----------------------------
initial_state = {
    "question": '''sajaltest@shellfleet.com was trying to create a user and got issue.
can you tell me the issue caused''',
    "retrieval_query": '''sajaltest@shellfleet.com was trying to create a user and got issue.
can you tell me the issue caused''',  # ✅ important
    "rewrite_tries": 0,                                        # ✅ important
    "docs": [],
    "relevant_docs": [],
    "context": "",
    "answer": "",
    "issup": "",
    "evidence": [],
    "retries": 0,
    "isuse": "not_useful",
    "use_reason": "",
}

#In[66]:
result = app.invoke(
    initial_state,
    config={"recursion_limit": 80},  # allow revise → verify loops
)

# -----------------------------
# Debug / inspection output (clean + complete)
# -----------------------------
print("\n===== RAG EXECUTION RESULT =====\n")

print("Question:", initial_state.get("question"))
print("Need Retrieval:", result.get("need_retrieval"))

# In[67]:
# # If you added these counters/fields in your State:
# print("Rewrite tries (retrieval):", result.get("rewrite_tries", 0))
# print("Support revise tries:", result.get("retries", 0))

print("\nRetrieval:")
print("  Total retrieved docs:", len(result.get("docs", []) or []))
print("  Relevant docs:", len(result.get("relevant_docs", []) or []))

# # Optional: show sources/pages for relevant docs
relevant_docs = result.get("relevant_docs", []) or []
# if relevant_docs:
#     print("\nRelevant docs (source/page):")
#     for i, d in enumerate(relevant_docs, 1):
#         src = (d.metadata or {}).get("source", "unknown")
#         page = (d.metadata or {}).get("page", None)
#         title = (d.metadata or {}).get("title", "")
#         extra = f", title={title}" if title else ""
#         if page is not None:
#             print(f"  {i}. source={src}, page={page}{extra}")
#         else:
#             print(f"  {i}. source={src}{extra}")

# print("\nVerification (IsSUP):")
# print("  issup:", result.get("issup"))
# evidence = result.get("evidence", []) or []
# if evidence:
#     print("  evidence:")
#     for e in evidence:
#         print("   -", e)
# else:
#     print("  evidence: (none)")

# print("\nUsefulness (IsUSE):")
# print("  isuse:", result.get("isuse"))
# print("  reason:", result.get("use_reason", ""))

print("\nFinal Answer:")
print(result.get("answer"))

# print("\n===============================\n")


# # In[ ]:





# %%
