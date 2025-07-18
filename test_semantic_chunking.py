from rag.doc_loader import load_docx_as_documents
from rag.semantic_chunker import semantic_chunk_documents
from rag.qdrant_uploader import upload_nodes_to_qdrant
from rag.embedder import embed_nodes
import os
import pickle

# Set your .docx file path here
DOCX_FILE_PATH = "./Abmahnung an Angeklagte.docx"  # <-- Change this to your test file
CACHE_FILE = "cached_nodes.pkl"
COLLECTION_NAME = "rag_collection"
EMBEDDINGS_FILE = "embeddings.pkl"

if __name__ == "__main__":
    # Step 1: Load the document
    documents = load_docx_as_documents(file_path=DOCX_FILE_PATH)
    print(f"Loaded {len(documents)} document(s)")
    # You can set a breakpoint here to inspect 'documents'

    # Step 2: Chunk the document semantically, with embedding caching
    if os.path.exists(CACHE_FILE):
        print(f"Loading cached nodes from {CACHE_FILE}")
        with open(CACHE_FILE, "rb") as f:
            nodes = pickle.load(f)
    else:
        print("No cache found. Chunking document...")
        nodes = semantic_chunk_documents(documents)
        with open(CACHE_FILE, "wb") as f:
            pickle.dump(nodes, f)
        print(f"Cached {len(nodes)} nodes to {CACHE_FILE}")
    print(f"Generated {len(nodes)} semantic chunks")
    # You can set a breakpoint here to inspect 'nodes'

    # Step 2.5: Embedding serialization logic
    if os.path.exists(EMBEDDINGS_FILE):
        print(f"Loading embeddings from {EMBEDDINGS_FILE}")
        with open(EMBEDDINGS_FILE, "rb") as f:
            embeddings = pickle.load(f)
        for node, embedding in zip(nodes, embeddings):
            node.embedding = embedding
    else:
        print("No embeddings file found. Embedding nodes...")
        embed_nodes(nodes)
        embeddings = [node.embedding for node in nodes]
        with open(EMBEDDINGS_FILE, "wb") as f:
            pickle.dump(embeddings, f)
        print(f"Saved embeddings to {EMBEDDINGS_FILE}")

    # Step 3: Print out the content of each chunk for inspection
    for i, node in enumerate(nodes):
        print(f"\n--- Chunk {i+1} ---\n{node.get_content()[:500]}\n...")

    # Step 4: Upload to Qdrant
    upload_nodes_to_qdrant(nodes, collection_name=COLLECTION_NAME) 