from langchain_classic.chains import ConversationalRetrievalChain
from langchain_classic.memory import ConversationBufferMemory
from langchain_ollama import ChatOllama
from .retriever_free import load_retriever

def get_qa_chain():
    retriever = load_retriever()

    # Using completely free local Ollama model
    llm = ChatOllama(
        model="llama3.2:1b",
        temperature=0
    )

    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
        output_key="answer"  # Specify which output to store in memory
    )

    return ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        return_source_documents=True
    )

