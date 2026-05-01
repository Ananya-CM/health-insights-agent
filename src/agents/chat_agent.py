import streamlit as st
from groq import Groq
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS


class ChatAgent:
    """
    Handles follow-up Q&A on analyzed reports using RAG (retrieval-augmented generation).
    Builds a vector store from report text and retrieves relevant chunks per query.
    """

    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    LLM_MODEL = "llama-3.3-70b-versatile"
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200

    def __init__(self):
        self.embedder = HuggingFaceEmbeddings(model_name=self.EMBEDDING_MODEL)
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.CHUNK_SIZE,
            chunk_overlap=self.CHUNK_OVERLAP,
        )
        self.llm = Groq(api_key=st.secrets["GROQ_API_KEY"])

    def build_vector_store(self, report_text):
        """Create a FAISS vector store from the report text."""
        content = report_text.strip() if report_text and report_text.strip() else "No report available."
        chunks = self.splitter.split_text(content) or [content]
        return FAISS.from_texts(chunks, self.embedder)

    def _reframe_query(self, query, history):
        """Reframe the user's query to be self-contained given prior context."""
        if not history:
            return query

        recent = history[-4:]
        history_str = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in recent
        )

        reframe_prompt = (
            f"Given the conversation below, rewrite the latest question as a standalone question.\n"
            f"Do NOT answer — only rewrite if needed, otherwise return as-is.\n\n"
            f"Conversation:\n{history_str}\n\n"
            f"Latest question: {query}\n\nRewritten question:"
        )

        try:
            resp = self.llm.chat.completions.create(
                model=self.LLM_MODEL,
                messages=[
                    {"role": "system", "content": "You rewrite questions to be standalone."},
                    {"role": "user", "content": reframe_prompt},
                ],
                temperature=0.1,
                max_tokens=200,
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            return query

    def answer(self, query, vector_store, chat_history=None):
        """Generate a response using retrieved context and chat history."""
        history = chat_history or []
        refined_query = self._reframe_query(query, history)

        # Retrieve relevant chunks
        context = ""
        try:
            retriever = vector_store.as_retriever(search_kwargs={"k": 3})
            docs = retriever.get_relevant_documents(refined_query)
            context = "\n\n".join(d.page_content for d in docs)
            if context.strip() == "No report available.":
                context = ""
        except Exception:
            pass

        system_msg = (
            "You are a helpful health assistant answering questions about a patient's lab report. "
            "Use the provided context to answer accurately. "
            "If the answer isn't in the context, say so clearly. "
            "Keep answers concise — 3 sentences max."
        )

        messages = [{"role": "system", "content": system_msg}]

        if history:
            messages += [{"role": m["role"], "content": m["content"]} for m in history[-6:]]

        if context:
            user_content = f"Report context:\n{context}\n\nQuestion: {query}"
        else:
            user_content = f"Question: {query}\n\n(No report context available — using conversation history only.)"

        messages.append({"role": "user", "content": user_content})

        try:
            resp = self.llm.chat.completions.create(
                model=self.LLM_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=500,
            )
            return resp.choices[0].message.content
        except Exception as err:
            return f"Could not generate a response: {str(err)}"
