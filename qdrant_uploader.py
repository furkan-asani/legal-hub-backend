import os
import uuid
import requests
import json
from typing import List
from dotenv import load_dotenv

# Node type hint: should have get_embedding() and get_content() methods

def upload_nodes_to_qdrant(nodes: List, collection_name: str = "law-test"):
    """
    Uploads semantic nodes (with embeddings) to a Qdrant collection using the Qdrant REST API.

    Args:
        nodes: List of nodes (from semantic_chunk_documents), each with get_embedding() and get_content().
        collection_name: Name of the Qdrant collection to upload to.
    """
    load_dotenv()
    QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    if QDRANT_HOST is None or QDRANT_HOST == "":
        raise ValueError("QDRANT_HOST must be set")
    # Compose URL
    qdrant_url = f"{QDRANT_HOST.rstrip('/')}/collections/{collection_name}/points?wait=true"
    url = qdrant_url
    headers = {"Content-Type": "application/json"}
    if QDRANT_API_KEY:
        headers["api-key"] = QDRANT_API_KEY

    point_ids = []
    vectors = []
    payloads = []

    for node in nodes:
        embedding = node.get_embedding()
        if embedding is None:
            # It's better to skip nodes without embeddings than to fail the whole batch
            print(f"Skipping a node because it does not have an embedding.")
            continue
            
        # Using UUIDs is more robust for IDs than list index
        point_ids.append(str(uuid.uuid4()))
        vectors.append(embedding)
        payloads.append({
            "text": node.get_content()
            # You can add more metadata here, e.g., "source": node.metadata.get("source")
        })

    # Assemble the final data payload in the correct batch format
    data = {"batch": {
            "ids": point_ids,
            "vectors": vectors,
            "payloads": payloads
        }}
    response = requests.put(url, headers=headers, data=json.dumps(data))
    print(f"Qdrant response status: {response.status_code}")
    try:
        print(f"Qdrant response: {response.json()}")
    except Exception:
        print(f"Qdrant response text: {response.text}")
    if not response.ok:
        raise RuntimeError(f"Failed to upload points to Qdrant: {response.text}") 