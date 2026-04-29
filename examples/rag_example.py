"""RAG Example - demonstrates retrieval augmented generation with MACS.

This example shows how to:
1. Create a RAG engine with document ingestion
2. Search for relevant context
3. Augment prompts with retrieved knowledge

Usage:
    python examples/rag_example.py
"""

import asyncio

from macs_pkg.rag import (
    RAGEngine,
    RAGConfig,
    DocumentChunker,
)


async def main():
    print("=" * 60)
    print("MACS RAG Example - Knowledge Retrieval System")
    print("=" * 60)
    print()

    # Sample knowledge base (could be loaded from files)
    documents = [
        {
            "content": """
            MACS (Multi-Agent Collaboration System) is a Python framework for building
            multi-agent AI systems. It supports various collaboration modes including
            hierarchical, decentralized, and pipeline patterns. The system integrates
            with LLMs like Claude and MiniMax for intelligent agent behavior.
            """,
            "metadata": {"source": "MACS Overview", "category": "intro"},
        },
        {
            "content": """
            The hierarchical collaboration mode in MACS follows a top-down approach
            where a planner agent decomposes tasks and assigns them to executor agents.
            The reviewer agent validates results. This mode is suitable for structured
            workflows with clear task hierarchies.
            """,
            "metadata": {"source": "Hierarchical Mode", "category": "collaboration"},
        },
        {
            "content": """
            The decentralized mode uses peer-to-peer negotiation where all agents are
            equals. Decisions are made through voting or consensus mechanisms. This mode
            works well for creative tasks or when no single agent should have authority.
            """,
            "metadata": {"source": "Decentralized Mode", "category": "collaboration"},
        },
        {
            "content": """
            Memory in MACS is powered by MemPalace, a local-first AI memory system.
            Agents can store and retrieve both short-term and long-term memories.
            The memory system supports semantic search for relevant past interactions.
            """,
            "metadata": {"source": "Memory System", "category": "memory"},
        },
        {
            "content": """
            RAG (Retrieval Augmented Generation) adds knowledge retrieval to agents.
            Documents are chunked, embedded into vectors, and stored in a vector database.
            When a query comes in, relevant documents are retrieved and included in the
            prompt to provide context-aware responses.
            """,
            "metadata": {"source": "RAG System", "category": "rag"},
        },
    ]

    # Create RAG engine with in-memory store (using dummy embedder for demo)
    print("[1/4] Creating RAG engine...")
    config = RAGConfig(
        embedder_provider="dummy",  # Use "sentence-transformers" for real embedding
        vector_store_type="memory",
        embedding_dim=384,
        chunk_size=200,
        chunk_overlap=30,
        default_top_k=3,
        similarity_threshold=0.1,  # Lower threshold for dummy embedder
    )
    rag = RAGEngine(config)
    print(f"      Config: {config.embedder_provider} embedder, {config.vector_store_type} store")

    # Add documents
    print("\n[2/4] Ingesting documents...")
    texts = [doc["content"] for doc in documents]
    metadatas = [doc["metadata"] for doc in documents]

    chunks_added = await rag.add_documents(texts, metadatas)
    print(f"      Added {chunks_added} chunks to knowledge base")

    # Show stats
    stats = await rag.get_stats()
    print(f"      Embedding dim: {stats['embedding_dim']}")
    print(f"      Chunk size: {stats['chunk_size']}")

    # Search queries
    queries = [
        "What is MACS?",
        "How does hierarchical mode work?",
        "What memory system does MACS use?",
        "What is RAG?",
    ]

    print("\n[3/4] Testing retrieval...")
    for query in queries:
        print(f"\n      Query: {query}")
        results = await rag.search(query)
        print(f"      Results: {len(results)} found")
        for i, r in enumerate(results[:2], 1):
            preview = r.content[:80].replace("\n", " ").strip()
            print(f"        [{i}] score={r.score:.3f}: {preview}...")

    # Demonstrate prompt augmentation
    print("\n[4/4] Prompt augmentation demo...")
    query = "Explain the decentralized collaboration mode in MACS"
    result = await rag.retrieve_and_augment(
        query=query,
        prompt_template="""Based on the following context, answer the question.

Context:
{context}

Question: {query}

Answer:"""
    )

    print(f"\n      Query: {query}")
    print(f"\n      Augmented prompt:")
    print("-" * 50)
    print(result["augmented_prompt"])
    print("-" * 50)

    print(f"\n      Sources:")
    for src in result["sources"]:
        print(f"        - {src['chunk_id']} (score: {src['score']:.3f})")

    print("\n" + "=" * 60)
    print("RAG example completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
