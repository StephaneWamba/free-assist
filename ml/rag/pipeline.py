from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, TypedDict

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings, HuggingFacePipeline
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langgraph.graph import END, START, StateGraph



# Constants


EMBED_MODEL = "dangvantuan/sentence-camembert-large"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
MAX_QUERY_REWRITES = 2       # circuit breaker — avoid infinite rewrite loops



# Graph state



class RAGState(TypedDict):
    """Mutable state threaded through each node of the RAG graph."""
    question: str
    documents: list[Document]
    generation: str
    query_rewrites: int         # counts rewrites to enforce circuit breaker



# Prompts


_GRADE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "Tu es un évaluateur de pertinence pour le support technique télécom. "
        "Réponds UNIQUEMENT par 'yes' ou 'no'. "
        "'yes' si le document est pertinent pour répondre à la question, 'no' sinon.",
    ),
    ("human", "Document :\n{document}\n\nQuestion : {question}"),
])

_GENERATE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "Tu es un assistant expert du support technique Iliad-Free. "
        "Propose une réponse professionnelle et précise à l'agent, basée UNIQUEMENT sur le contexte. "
        "Si le contexte est insuffisant, dis-le clairement.",
    ),
    (
        "human",
        "Contexte :\n{context}\n\nTicket client : {question}\n\nRéponse suggérée :",
    ),
])

_REWRITE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "Tu es un expert en reformulation de requêtes pour un système de recherche télécom. "
        "Reformule la question pour améliorer la récupération de documents pertinents.",
    ),
    ("human", "Question originale : {question}\n\nQuestion reformulée :"),
])



# Node functions



def _make_retrieve_node(retriever):
    """Retrieve documents from FAISS given the current question."""
    def retrieve(state: RAGState) -> dict:
        docs = retriever.invoke(state["question"])
        return {"documents": docs}
    return retrieve


def _make_grade_node(llm):
    """Filter retrieved documents — keep only those relevant to the question."""
    grader = _GRADE_PROMPT | llm | StrOutputParser()

    def grade_documents(state: RAGState) -> dict:
        relevant: list[Document] = []
        for doc in state["documents"]:
            verdict = grader.invoke({"document": doc.page_content, "question": state["question"]})
            if "yes" in verdict.lower():
                relevant.append(doc)
        return {"documents": relevant}

    return grade_documents


def _make_generate_node(llm):
    """Generate a support response from the graded context."""
    chain = (
        {"context": lambda s: "\n\n".join(d.page_content for d in s["documents"]),
         "question": lambda s: s["question"]}
        | _GENERATE_PROMPT
        | llm
        | StrOutputParser()
    )

    def generate(state: RAGState) -> dict:
        return {"generation": chain.invoke(state)}

    return generate


def _make_rewrite_node(llm):
    """Rewrite the question when retrieved docs are not relevant."""
    rewriter = _REWRITE_PROMPT | llm | StrOutputParser()

    def rewrite_query(state: RAGState) -> dict:
        new_question = rewriter.invoke({"question": state["question"]})
        return {
            "question": new_question.strip(),
            "query_rewrites": state.get("query_rewrites", 0) + 1,
        }

    return rewrite_query



# Routing logic (conditional edges)



def _route_after_grading(state: RAGState) -> Literal["generate", "rewrite_query"]:
    """
    After grading: go to generate if we have relevant docs,
    rewrite if not — but cap rewrites to avoid infinite loops.
    """
    if state["documents"]:
        return "generate"
    if state.get("query_rewrites", 0) >= MAX_QUERY_REWRITES:
        # Circuit breaker: generate with empty context rather than loop forever
        return "generate"
    return "rewrite_query"



# Graph builder



def build_rag_graph(retriever, llm):
    retrieve = _make_retrieve_node(retriever)
    grade = _make_grade_node(llm)
    generate = _make_generate_node(llm)
    rewrite = _make_rewrite_node(llm)

    graph = StateGraph(RAGState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("grade_documents", grade)
    graph.add_node("generate", generate)
    graph.add_node("rewrite_query", rewrite)

    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "grade_documents")
    graph.add_conditional_edges(
        "grade_documents",
        _route_after_grading,
        {"generate": "generate", "rewrite_query": "rewrite_query"},
    )
    graph.add_edge("rewrite_query", "retrieve")   # loop back after rewrite
    graph.add_edge("generate", END)

    return graph.compile()



# High-level facade



from dataclasses import dataclass, field


@dataclass
class RAGResult:
    answer: str
    source_documents: list[str] = field(default_factory=list)
    query_rewrites: int = 0


class FreeAssistRAG:
    """
    Production facade over the LangGraph agentic RAG graph.
    Loaded once at API startup; thread-safe for concurrent requests.
    """

    def __init__(self, index_dir: str | Path, llm_model_id: str | None = None) -> None:
        self._index_dir = Path(index_dir)
        self._llm_model_id = llm_model_id or os.getenv(
            "LLM_MODEL_ID", "mistralai/Mistral-7B-Instruct-v0.3"
        )
        self._graph = None

    def is_loaded(self) -> bool:
        return self._graph is not None

    def load(self) -> None:
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBED_MODEL,
            model_kwargs={"device": _device()},
            encode_kwargs={"normalize_embeddings": True},
        )
        store = FAISS.load_local(
            str(self._index_dir),
            embeddings,
            allow_dangerous_deserialization=True,
        )
        retriever = store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 4, "fetch_k": 10},
        )

        llm = HuggingFacePipeline.from_model_id(
            model_id=self._llm_model_id,
            task="text-generation",
            pipeline_kwargs={
                "max_new_tokens": 512,
                "temperature": 0.1,
                "repetition_penalty": 1.1,
                "do_sample": True,
            },
        )

        self._graph = build_rag_graph(retriever, llm)

    def generate(self, question: str) -> RAGResult:
        """Run the full agentic RAG graph. Returns RAGResult."""
        if self._graph is None:
            raise RuntimeError("RAG not loaded. Call load() first.")

        initial_state: RAGState = {
            "question": question,
            "documents": [],
            "generation": "",
            "query_rewrites": 0,
        }
        final_state = self._graph.invoke(initial_state)
        return RAGResult(
            answer=final_state.get("generation", ""),
            source_documents=[
                doc.metadata.get("source", doc.page_content[:80])
                for doc in final_state.get("documents", [])
            ],
            query_rewrites=final_state.get("query_rewrites", 0),
        )



# Index builder (standalone CLI utility)



def build_index(knowledge_base_dir: str | Path, index_dir: str | Path) -> FAISS:
    knowledge_base_dir = Path(knowledge_base_dir)
    index_dir = Path(index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)

    loader = DirectoryLoader(
        str(knowledge_base_dir),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=True,
    )
    docs = loader.load()
    print(f"Loaded {len(docs)} documents")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )
    chunks = splitter.split_documents(docs)
    print(f"Split into {len(chunks)} chunks")

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        model_kwargs={"device": _device()},
        encode_kwargs={"normalize_embeddings": True},
    )

    store = FAISS.from_documents(chunks, embeddings)
    store.save_local(str(index_dir))
    print(f"FAISS index saved to {index_dir}")
    return store


def _device() -> str:
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"
