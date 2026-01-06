from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from loader import load_docs

def build_vector_store():
    print("Loading documents...")
    docs = load_docs()
    print(f"Loaded {len(docs)} document chunks")
    
    print("Initializing embeddings model (this may download the model on first run)...")
    # Using a free, lightweight embedding model
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    
    print("Creating FAISS index...")
    db = FAISS.from_documents(docs, embeddings)
    
    print("Saving FAISS index...")
    db.save_local("faiss_index")
    print("✅ FAISS index created successfully!")

if __name__ == "__main__":
    build_vector_store()

