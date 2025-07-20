import os
import uuid
from typing import List
from dotenv import load_dotenv
from qdrant_client.models import PointStruct
from .qdrant_client_factory import get_qdrant_client, create_collection_if_not_exists

# Node type hint: should have get_embedding() and get_content() methods

def upload_nodes_to_qdrant(nodes: List, collection_name: str = "law-test", case_id: int = None):
    """
    Uploads semantic nodes (with embeddings) to a Qdrant collection using the centralized client factory.

    Args:
        nodes: List of nodes (from semantic_chunk_documents), each with get_embedding() and get_content().
        collection_name: Name of the Qdrant collection to upload to.
        case_id: Optional case ID to include as metadata in each node's payload.
    """
    # Get client from factory
    client = get_qdrant_client()
    
    # Ensure collection exists
    collection_created = create_collection_if_not_exists(collection_name)
    if collection_created:
        print(f"✓ Created collection '{collection_name}'")
    
    # Prepare points for upload
    points = []
    skipped_count = 0
    
    for i, node in enumerate(nodes):
        embedding = node.get_embedding()
        if embedding is None:
            print(f"Skipping node {i+1} because it does not have an embedding.")
            skipped_count += 1
            continue
            
        # Build payload
        payload = {"text": node.get_content()}
        if case_id is not None:
            payload["case_id"] = case_id
            
        # Add metadata if available
        if hasattr(node, "metadata") and isinstance(node.metadata, dict):
            payload.update(node.metadata)
        
        # Create point
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload=payload
        )
        points.append(point)
    
    if not points:
        print("No valid points to upload (all nodes missing embeddings)")
        return
    
    # Upload points to Qdrant
    try:
        print(f"Uploading {len(points)} points to collection '{collection_name}'...")
        operation_info = client.upsert(
            collection_name=collection_name,
            wait=True,
            points=points
        )
        
        print(f"✓ Successfully uploaded {len(points)} points")
        if skipped_count > 0:
            print(f"⚠️  Skipped {skipped_count} nodes without embeddings")
        print(f"Operation info: {operation_info}")
        
    except Exception as e:
        print(f"❌ Failed to upload points to Qdrant: {e}")
        raise RuntimeError(f"Failed to upload points to Qdrant: {e}") 