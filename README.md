# 🚀 Project Name (SRE System / Log Analyzer)

## 📌 Overview

This project is an SRE-focused log analysis and debugging system built using RAG (Retrieval-Augmented Generation).

It helps diagnose application issues using:

* Application logs
* DB logs
* Log analytics data

---

## 🧠 Architecture

* LLM: gpt-4o-mini
* Embeddings: text-embedding-3-large
* Vector DB: FAISS
* Framework: LangChain + LangGraph

### Flow:

1. Decide if retrieval is needed
2. Retrieve logs (Correlation ID / semantic search)
3. Filter relevant logs
4. Generate root cause
5. Verify answer (Self-RAG loop)

---

## 📂 Project Structure

```
project/
│── documents/           # Excel log files
│── app.py               # Main pipeline
│── README.md
│── .env                 # API keys
```

---

## ⚙️ Setup Instructions

### 1. Clone repo

```
git clone <your-repo-url>
cd <repo>
```

### 2. Install dependencies

```
pip install -r requirements.txt
```

### 3. Add environment variables

Create `.env`:

```
OPENAI_API_KEY=your_key_here
```

---

## ▶️ Run the Project

```
python app.py
```

---

## 🔍 Example Use Case

**Input:**
User unable to create account

**Output:**
Root cause detected from logs (e.g., SQL constraint failure)

---

## ⚠️ Limitations

* FAISS is in-memory (not persistent)
* Depends on log quality
* Requires correlationId for best results

---

## 🚀 Future Improvements

* Move to Pinecone / Weaviate
* Add UI dashboard
* Real-time log ingestion

---

## 👨‍💻 Author
Sajal Kirtiman
Shweta Kaalay
Rashmi Yadav
