from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

def load_docs(path="data/docs"):
    # Load PDF files
    pdf_loader = DirectoryLoader(path, glob="**/*.pdf", loader_cls=PyPDFLoader)
    pdf_docs = pdf_loader.load()

    # Load Markdown files
    md_loader = DirectoryLoader(path, glob="**/*.md", loader_cls=TextLoader)
    md_docs = md_loader.load()

    # Load text files
    txt_loader = DirectoryLoader(path, glob="**/*.txt", loader_cls=TextLoader)
    txt_docs = txt_loader.load()

    # Combine all documents
    all_docs = pdf_docs + md_docs + txt_docs

    print(f"Loaded {len(pdf_docs)} PDF files, {len(md_docs)} Markdown files, {len(txt_docs)} text files")

    # Split documents into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100
    )
    return splitter.split_documents(all_docs)
