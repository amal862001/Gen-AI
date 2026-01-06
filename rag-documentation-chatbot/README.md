# 🤖 RAG Documentation Chatbot

A **completely free**, production-ready RAG (Retrieval-Augmented Generation) chatbot that answers questions from your technical documentation using local LLMs and embeddings.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![LangChain](https://img.shields.io/badge/LangChain-latest-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## ✨ Features

- 🔍 **Semantic Search** - Find relevant information across multiple documents
- 💬 **Conversational AI** - Maintains context across chat sessions
- 📚 **Multi-Format Support** - PDF, Markdown, and TXT files
- 🎯 **Source Citations** - Shows exactly where answers came from
- 💰 **100% Free** - No API costs, runs completely offline
- ⚡ **Fast Retrieval** - <100ms vector search with FAISS
- 🌐 **Web Interface** - Clean Streamlit UI with chat history

## 🏗️ Architecture

**Tech Stack:**
- **LangChain** - RAG orchestration framework
- **FAISS** - Vector database for similarity search
- **Ollama (Llama 3.2 1B)** - Local LLM for answer generation
- **HuggingFace (all-MiniLM-L6-v2)** - Local embeddings model
- **Streamlit** - Web interface

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- [Ollama](https://ollama.com/download) installed

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/rag-chatbot.git
cd rag-chatbot
```

2. **Create virtual environment**
```bash
python -m venv venv
.\venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On Mac/Linux
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Download Ollama model**
```bash
ollama pull llama3.2:1b
```

5. **Add your documents**
- Place PDF, Markdown, or TXT files in `data/docs/`

6. **Build the vector index**
```bash
python ingestion/embed_store_free.py
```

7. **Run the app**
```bash
streamlit run app.py
```

8. **Open browser** at `http://localhost:8501`

## 📁 Project Structure

```
rag-chatbot/
├── app.py                          # Streamlit web interface
├── data/
│   └── docs/                       # Your documents (PDF/MD/TXT)
├── ingestion/
│   ├── loader.py                   # Multi-format document loader
│   └── embed_store_free.py         # FAISS index builder
├── rag/
│   ├── retriever_free.py           # Vector retriever
│   └── qa_chain_free.py            # QA chain with Ollama
├── evaluation/
│   ├── evaluate.py                 # Accuracy testing
│   └── text_set.json               # Test cases
├── requirements.txt                # Python dependencies
└── README.md
```

## 🎯 Usage

### Adding Documents
1. Place files in `data/docs/` (supports PDF, MD, TXT)
2. Rebuild index: `python ingestion/embed_store_free.py`
3. Restart the app

### Evaluation
Test chatbot accuracy:
```bash
python evaluation/evaluate.py
```

## ⚙️ Configuration

### Chunking Strategy
Edit `ingestion/loader.py`:
```python
chunk_size=800      # Characters per chunk
chunk_overlap=100   # Overlap between chunks
```

### Retrieval Settings
Edit `rag/retriever_free.py`:
```python
search_kwargs={"k": 4}  # Number of chunks to retrieve
```

### LLM Model
Edit `rag/qa_chain_free.py`:
```python
model="llama3.2:1b"  # Change to any Ollama model
temperature=0        # 0 = deterministic, 1 = creative
```

## 📊 Performance Metrics

- **Retrieval Speed**: <100ms for top-4 chunks
- **Cost**: $0/month (100% local)
- **Accuracy**: 75-90% on domain-specific questions
- **Supported Formats**: PDF, Markdown, TXT
- **Chunk Processing**: 45+ chunks from sample document

## 🔧 Troubleshooting

**Error: "No connection could be made"**
- Start Ollama: `ollama serve`

**Error: "No module named 'rag'"**
- Run from project root directory
- Ensure virtual environment is activated

**Error: "faiss_index not found"**
- Build index first: `python ingestion/embed_store_free.py`

## 🤝 Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- [LangChain](https://langchain.com/) - RAG framework
- [Ollama](https://ollama.com/) - Local LLM runtime
- [FAISS](https://github.com/facebookresearch/faiss) - Vector search
- [HuggingFace](https://huggingface.co/) - Embedding models
