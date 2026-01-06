import streamlit as st
from dotenv import load_dotenv
from rag.qa_chain_free import get_qa_chain

# Load environment variables
load_dotenv()

st.set_page_config(page_title="📘 Doc Assistant")
st.title("📘 Intelligent Technical Doc-Assistant")

qa_chain = get_qa_chain()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

question = st.chat_input("Ask about the documentation")

if question:
    # 1️⃣ Call RAG chain
    response = qa_chain({
        "question": question,
        "chat_history": st.session_state.chat_history
    })

    answer = response["answer"]

    # 2️⃣ Save conversation
    st.session_state.chat_history.append((question, answer))

    # 3️⃣ Display chat history
    for q, a in st.session_state.chat_history:
        st.chat_message("user").write(q)
        st.chat_message("assistant").write(a)

    # 4️⃣ ✅ ADD SOURCE CITATIONS HERE (RIGHT AFTER ANSWER)
    with st.expander("📌 Source Citations"):
        for doc in response["source_documents"]:
            st.markdown(
                f"**Source:** `{doc.metadata.get('source', 'Unknown')}`"
            )
            st.markdown(
                f"<mark>{doc.page_content[:500]}...</mark>",
                unsafe_allow_html=True
            )    
