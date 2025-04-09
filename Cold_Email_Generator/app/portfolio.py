import pandas as pd
import chromadb
import uuid


class Portfolio:
    def __init__(self, file_path=r"C:\Users\RONO\Desktop\CHAT_BOT_AGENT\app\resource\my_portfolio.csv"):
        self.file_path = file_path
        self.data = pd.read_csv(file_path)
        self.chroma_client = chromadb.PersistentClient('vectorstore')
        self.collection = self.chroma_client.get_or_create_collection(name="portfolio")

    def load_portfolio(self):
        if not self.collection.count():
            for _, row in self.data.iterrows():
                # Adding documents to the ChromaDB collection with metadata and unique IDs
                self.collection.add(
                    documents=[row["Techstack"]],
                    metadatas=[{"links": row["Links"]}],  # Wrapping metadata in a list
                    ids=[str(uuid.uuid4())]
                )

    def query_links(self, skills):
        # Ensure `skills` is a list or string
        if isinstance(skills, list):
            skills = " ".join(skills)
        elif not isinstance(skills, str):
            skills = str(skills)

        # Querying the ChromaDB collection
        result = self.collection.query(query_texts=[skills], n_results=2)

        # Extracting metadata containing links
        links = [meta['links'] for meta in result.get('metadatas', []) if 'links' in meta]
        return links
