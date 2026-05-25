"""
LangChain LCEL RAG Chain - built on top of MACS RAG Engine.

This module provides LangChain LCEL (LangChain Expression Language) wrappers
around MACS's existing RAG components, enabling standard LangChain-style
RAG pipelines with the flexibility to use any LangChain-supported chat model.

LCEL Chain Flow:
    Document Loader → Splitter → Embedding → VectorStore → Retrieval → QA

Usage:
    # Basic usage with default settings
    chain = LCELRAGChain()
    await chain.add_texts(texts)
    result = await chain.invoke("your question")

    # With custom chat model
    from langchain_community.chat_models import ChatZhipuAI
    chain = LCELRAGChain(chat_model=ChatZhipuAI(...))
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Sequence, Union
import os

# ─── LangChain Core ───────────────────────────────────────────────────────────
# Required: pip install langchain-core
#
# Note: Some langchain-core submodules transitively import transformers/torch,
# which may fail on Windows (OSError: DLL load failure). All imports are
# wrapped to degrade gracefully — unavailable components get a None fallback.
_LC_ERROR: Optional[str] = None

try:
    from langchain_core.documents import Document as LCDocument
except (ImportError, OSError) as e:
    LCDocument = None  # type: ignore
    _LC_ERROR = f"langchain-core.documents: {e}"

try:
    from langchain_core.output_parsers import StrOutputParser
except (ImportError, OSError) as e:
    import warnings
    warnings.warn(f"StrOutputParser unavailable (torch DLL issue): {e}", RuntimeWarning)
    StrOutputParser = None  # type: ignore

try:
    from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
except (ImportError, OSError) as e:
    ChatPromptTemplate = None  # type: ignore
    PromptTemplate = None  # type: ignore
    _LC_ERROR = f"langchain-core.prompts: {e}"

try:
    from langchain_core.runnables import (
        Runnable,
        RunnablePassthrough,
        RunnableLambda,
    )
except (ImportError, OSError) as e:
    Runnable = None  # type: ignore
    RunnablePassthrough = None  # type: ignore
    RunnableLambda = None  # type: ignore
    _LC_ERROR = f"langchain-core.runnables: {e}"

if LCDocument is None or ChatPromptTemplate is None or Runnable is None:
    import warnings
    warnings.warn(
        "langchain-core is partially unavailable due to torch/transformers DLL issue "
        f"on Windows: {_LC_ERROR}. "
        "The LCELRAGChain class will not be functional until this is resolved.",
        RuntimeWarning,
    )

# ─── LangChain Community (for document loaders & chat models) ─────────────────
# Required: pip install langchain-community
# All langchain-community imports can fail due to torch DLL issues on Windows
_LC_COMMUNITY_ERROR: Optional[str] = None

try:
    from langchain_community.document_loaders import TextLoader, DirectoryLoader
except (ImportError, OSError) as e:
    TextLoader = None  # type: ignore
    DirectoryLoader = None  # type: ignore
    _LC_COMMUNITY_ERROR = f"langchain_community.document_loaders: {e}"

try:
    from langchain_community.chat_models import MiniMaxChat
except (ImportError, OSError) as e:
    MiniMaxChat = None  # type: ignore
    _LC_COMMUNITY_ERROR = f"langchain_community.chat_models: {e}"

try:
    from langchain_community.embeddings import HuggingFaceBgeEmbeddings
except (ImportError, OSError) as e:
    HuggingFaceBgeEmbeddings = None  # type: ignore
    _LC_COMMUNITY_ERROR = f"langchain_community.embeddings: {e}"

try:
    from langchain_community.vectorstores import Chroma, FAISS
except (ImportError, OSError) as e:
    Chroma = None  # type: ignore
    FAISS = None  # type: ignore
    _LC_COMMUNITY_ERROR = f"langchain_community.vectorstores: {e}"

if TextLoader is None or MiniMaxChat is None or HuggingFaceBgeEmbeddings is None:
    import warnings
    warnings.warn(
        "langchain-community is partially unavailable due to torch/transformers DLL issue "
        f"on Windows: {_LC_COMMUNITY_ERROR}. "
        "Document loading, embeddings, and MiniMaxChat will not be functional.",
        RuntimeWarning,
    )

# ─── MACS RAG Engine ──────────────────────────────────────────────────────────
from macs_pkg.rag.rag_engine import RAGEngine, RAGConfig
from macs_pkg.rag.document import Document as MACSDocument


# ═══════════════════════════════════════════════════════════════════════════════
# LCEL RAG Chain
# ═══════════════════════════════════════════════════════════════════════════════

class LCELRAGChain:
    """
    LangChain LCEL-based RAG Chain.

    Wraps the MACS RAG engine with LangChain LCEL syntax, providing a
    standard LangChain-style interface while retaining MACS's robust
    embedding, chunking, and hybrid search capabilities.

    The chain diagram (LCEL):

        [Retriever] → [Context Formatter] → [Prompt] → [Chat Model] → [Output]

    Attributes:
        retriever: The underlying MACS RAG Engine used as a LangChain retriever.
        chat_model: A LangChain ChatModel (any provider supported by LangChain).
        prompt: The QA prompt template used in the chain.
        vectorstore: The LangChain VectorStore (Chroma/FAISS) for direct LCEL ops.
    """

    def __init__(
        self,
        chat_model: Optional[Any] = None,
        retriever: Optional[RAGEngine] = None,
        persist_directory: Optional[str] = None,
        embedding_model: str = "BAAI/bge-small-zh-v1.5",
        vectorstore_type: str = "chroma",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        default_top_k: int = 5,
        enable_hybrid: bool = False,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        """
        Initialize the LCEL RAG Chain.

        Args:
            chat_model: A LangChain-compatible chat model instance.
                        If None, uses MiniMaxChat (requires langchain-community).
            retriever: An existing MACS RAG Engine to use as the retriever.
                       If None, a new one is created based on the other params.
            persist_directory: Directory for persisting the vector store.
            embedding_model: HuggingFace embedding model name (used for vectorstore).
                              Set to None to skip creating a LangChain vectorstore.
            vectorstore_type: "chroma" or "faiss" (which LangChain vectorstore to use).
            chunk_size: Character-level chunk size for splitting.
            chunk_overlap: Overlap between adjacent chunks.
            default_top_k: Default number of documents to retrieve.
            enable_hybrid: Enable hybrid search (vector + BM25) in MACS RAG Engine.
            api_key: API key for the chat model (e.g., MiniMax).
            model_name: Model name for the chat model.
        """
        # ── Sanity check: LCEL components must be available ─────────────────
        if ChatPromptTemplate is None or RunnablePassthrough is None or RunnableLambda is None:
            raise ImportError(
                "langchain-core LCEL components are unavailable due to a torch/transformers "
                "DLL loading issue on this Windows machine. "
                "Fix the torch installation or run on Linux/macOS to use LCELRAGChain."
            )

        # ── Chat model ──────────────────────────────────────────────────────
        self._chat_model = chat_model
        if self._chat_model is None:
            if MiniMaxChat is not None:
                # Use MiniMaxChat from langchain-community if available
                self._chat_model = MiniMaxChat(
                    api_key=api_key or os.environ.get("MINIMAX_API_KEY", ""),
                    model=model_name or "MiniMax-M2.7",
                )
            else:
                raise ImportError(
                    "No chat model provided and langchain-community MiniMaxChat is unavailable. "
                    "Provide a chat_model argument."
                )

        # ── MACS RAG Engine (used as the retriever backbone) ─────────────────
        self._retriever = retriever
        if self._retriever is None:
            rag_config = RAGConfig(
                embedder_provider="dummy",  # We use LangChain embeddings for vectorstore
                vector_store_type="memory",
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                default_top_k=default_top_k,
                enable_hybrid=enable_hybrid,
                api_key=api_key,
                model_name=embedding_model,
            )
            self._retriever = RAGEngine(config=rag_config)

        # ── LangChain VectorStore (optional, for direct LCEL operations) ────
        self._vectorstore: Optional[Any] = None
        self._embedding_model = embedding_model
        self._persist_directory = persist_directory
        self._vectorstore_type = vectorstore_type

        if self._embedding_model is not None:
            self._init_vectorstore()

        # ── LCEL Chain components ─────────────────────────────────────────────
        # QA Prompt following LangChain best practices
        self._prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个专业的知识库问答助手。 "
                "请根据以下参考上下文，回答用户的问题。 "
                "如果上下文中没有相关信息，请如实说明，不要编造答案。\n\n"
                "参考上下文：\n{context}"
            )),
            ("human", "{question}"),
        ])

        # Output parser to extract the string response
        # StrOutputParser may be None if torch DLL fails on Windows
        if StrOutputParser is not None:
            self._output_parser = StrOutputParser()
        else:
            # Minimal fallback: just return the AIMessage content as a string
            self._output_parser = RunnableLambda(
                lambda msg: msg.content if hasattr(msg, "content") else str(msg)
            )

        # ── Build the LCEL chain ─────────────────────────────────────────────
        # Chain diagram:
        #   input: {"question": ...}
        #     → _format_inputs       (extracts question)
        #     → retriever           (MACS RAG Engine → LCEL retriever adapter)
        #     → _format_context     (joins docs into a single context string)
        #     → prompt              (injects context + question into prompt)
        #     → chat_model          (generates answer)
        #     → output_parser       (extracts str content)
        #
        # LCEL operator: | chains runnables together (output of left → input of right)
        self._chain = (
            RunnablePassthrough()
            | RunnableLambda(self._format_inputs)
            | self._build_retriever_runnable()
            | RunnableLambda(self._format_context)
            | self._prompt
            | self._chat_model
            | self._output_parser
        )

    # ─── VectorStore initialization ──────────────────────────────────────────

    def _init_vectorstore(self) -> None:
        """Initialize the LangChain VectorStore with HuggingFace embeddings."""
        if HuggingFaceBgeEmbeddings is None:
            raise ImportError(
                "langchain_community is required for vectorstore support. "
                "Install with: pip install langchain-community"
            )

        if Chroma is None and FAISS is None:
            raise ImportError(
                "Neither Chroma nor FAISS is available. "
                "Install with: pip install chromadb faiss-cpu"
            )

        embeddings = HuggingFaceBgeEmbeddings(
            model_name=self._embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        if self._persist_directory and os.path.exists(self._persist_directory):
            # Load existing vectorstore
            if self._vectorstore_type == "chroma" and Chroma is not None:
                self._vectorstore = Chroma(
                    persist_directory=self._persist_directory,
                    embedding_function=embeddings,
                )
            elif self._vectorstore_type == "faiss" and FAISS is not None:
                self._vectorstore = FAISS.load_local(
                    self._persist_directory,
                    embeddings,
                    allow_dangerous_deserialization=True,
                )
        else:
            # Create new vectorstore
            if self._vectorstore_type == "chroma" and Chroma is not None:
                self._vectorstore = Chroma(
                    embedding_function=embeddings,
                    persist_directory=self._persist_directory,
                )
            elif self._vectorstore_type == "faiss" and FAISS is not None:
                self._vectorstore = FAISS.from_texts(
                    ["initialization_placeholder"],
                    embeddings,
                )
                # Remove the placeholder
                self._vectorstore.delete(ids=["0"])

    # ─── LCEL Chain assembly ──────────────────────────────────────────────────

    def _build_retriever_runnable(self) -> Runnable:
        """
        Build a LangChain-compatible retriever runnable from the MACS RAG Engine.

        The MACS RAG Engine is async-first. This wraps it in a
        RunnableLambda so it integrates seamlessly with LCEL's sync/async
        chain composition.

        LCEL note: When an async function is passed to RunnableLambda,
        LCEL automatically runs it in the async context when the chain
        is invoked with async methods (e.g., ainvoke).
        """
        async def retrieve(query: str) -> List[LCDocument]:
            """Async retrieval using MACS RAG Engine."""
            contexts = await self._retriever.search(query, top_k=self._retriever.config.default_top_k)
            return [
                LCDocument(
                    page_content=ctx.content,
                    metadata={
                        "chunk_id": ctx.chunk_id,
                        "score": ctx.score,
                        "source": ctx.source,
                        **ctx.metadata,
                    },
                )
                for ctx in contexts
            ]

        return RunnableLambda(retrieve)  # Wraps the async fn as a Runnable

    # ─── Chain input / output formatting ─────────────────────────────────────

    @staticmethod
    def _format_inputs(query: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Normalize chain input to always be a dict with 'question' key."""
        if isinstance(query, str):
            return {"question": query}
        return query

    @staticmethod
    def _format_context(docs: List[LCDocument]) -> Dict[str, Any]:
        """Join retrieved documents into a context string for the prompt."""
        if not docs:
            context = "[未找到相关参考上下文]"
        else:
            context = "\n\n---\n\n".join(
                f"[Source {i + 1}] {doc.page_content}" for i, doc in enumerate(docs)
            )
        return {"context": context}


# ═══════════════════════════════════════════════════════════════════════════════
# Convenience: build a minimal chain directly from texts (no file loading)
# ═══════════════════════════════════════════════════════════════════════════════

def create_rag_chain(
    texts: List[str],
    question: str,
    chat_model: Optional[Any] = None,
    embedding_model: str = "BAAI/bge-small-zh-v1.5",
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    top_k: int = 5,
    enable_hybrid: bool = False,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
) -> LCELRAGChain:
    """
    Create a RAG chain from a list of texts and invoke it immediately.

    This is a convenience function for quick experimentation.

    Args:
        texts: List of text documents to add to the knowledge base.
        question: The question to ask.
        chat_model: A LangChain ChatModel instance.
        embedding_model: HuggingFace embedding model for vectorization.
        chunk_size: Chunk size for splitting documents.
        chunk_overlap: Chunk overlap.
        top_k: Number of documents to retrieve.
        enable_hybrid: Enable hybrid search in MACS RAG Engine.
        api_key: API key for the chat model.
        model_name: Model name for the chat model.

    Returns:
        The generated answer string.

    Example:
        >>> answer = create_rag_chain(
        ...     texts=["采购申请超过1万元需要总监审批。"],
        ...     question="采购申请金额超过1万怎么处理？",
        ...     embedding_model=None,  # skip LangChain vectorstore
        ... )
        >>> print(answer)
    """
    chain = LCELRAGChain(
        chat_model=chat_model,
        embedding_model=embedding_model,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        enable_hybrid=enable_hybrid,
        api_key=api_key,
        model_name=model_name,
    )

    # Add documents via MACS RAG Engine (sync wrapper)
    asyncio.run(chain._retriever.add_documents(texts))

    # Invoke the chain
    return asyncio.run(chain._chain.ainvoke({"question": question}))


# ═══════════════════════════════════════════════════════════════════════════════
# Minimal runnable example (no external LLM needed — for testing syntax)
# ═══════════════════════════════════════════════════════════════════════════════

def _demo_chain() -> None:
    """
    Demo the LCEL chain construction without requiring API keys or real models.

    Shows how the chain components compose together via the | operator.
    """
    if ChatPromptTemplate is None or RunnablePassthrough is None or RunnableLambda is None:
        print("Demo skipped: langchain-core LCEL components unavailable (torch DLL issue on Windows).")
        return

    # ── Mock retriever (simulates document retrieval) ──────────────────────────
    def mock_retrieve(query: str) -> List[LCDocument]:
        return [
            LCDocument(
                page_content=f"这是关于「{query}」的参考文档内容。",
                metadata={"source": "demo"},
            )
        ]

    # ── Build chain with mock retriever ───────────────────────────────────────
    #   prompt input:  {"context": "...", "question": "..."}
    #   output:        str (answer string)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "参考上下文：\n{context}"),
        ("human", "{question}"),
    ])

    # Output parser — use real StrOutputParser if available, else a basic fallback
    output_parser = (
        StrOutputParser()
        if StrOutputParser is not None
        else RunnableLambda(lambda msg: msg.content if hasattr(msg, "content") else str(msg))
    )

    chain = (
        RunnablePassthrough()
        | RunnableLambda(lambda x: {"question": x.get("question", x)})
        | RunnableLambda(mock_retrieve)
        | (lambda docs: {"context": "\n".join(d.page_content for d in docs)})
        | prompt
        | output_parser
    )

    # Note: Running the full chain requires a real chat model.
    # This demo only shows LCEL composition syntax.
    print("LCEL Chain constructed successfully:")
    print(f"  Chain structure: RunnablePassthrough | mock_retrieve | prompt | output_parser")
    print(f"  Chain type: {type(chain)}")


if __name__ == "__main__":
    _demo_chain()
    print("\n--- Minimal RAG Chain Demo ---")
    print("NOTE: Full execution requires a chat model and API key.")
    print("See create_rag_chain() for a complete usage example.")
