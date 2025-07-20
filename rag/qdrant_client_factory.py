"""
Centralized Qdrant client factory for consistent client configuration across the application.
"""

import os
from typing import Optional
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

# Global client instance for reuse
_client_instance: Optional[QdrantClient] = None

def get_qdrant_client() -> QdrantClient:
    """
    Factory method to get a configured Qdrant client instance.
    
    Returns the same client instance across calls to avoid multiple connections.
    
    Returns:
        QdrantClient: Configured Qdrant client
        
    Raises:
        ValueError: If required environment variables are not set
        Exception: If client creation fails
    """
    global _client_instance
    
    # Return existing instance if already created
    if _client_instance is not None:
        return _client_instance
    
    # Load environment variables
    load_dotenv()
    
    QDRANT_HOST = os.getenv("QDRANT_HOST")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    
    if not QDRANT_HOST:
        raise ValueError("QDRANT_HOST must be set in environment variables")
    
    try:
        # Create client with consistent configuration
        _client_instance = QdrantClient(
            url=QDRANT_HOST,
            api_key=QDRANT_API_KEY,
            port=6333,
            grpc_port=6334,
            prefer_grpc=True,
            https=True
        )
        
        # Test connection
        _client_instance.get_collections()
        
        return _client_instance
        
    except Exception as e:
        _client_instance = None  # Reset on failure
        raise Exception(f"Failed to create Qdrant client: {e}")

def create_collection_if_not_exists(collection_name: str, vector_size: int = 3072) -> bool:
    """
    Creates a Qdrant collection if it doesn't already exist.
    
    Args:
        collection_name: Name of the collection to create
        vector_size: Size of the vector embeddings (default: 3072 for text-embedding-3-large)
        
    Returns:
        bool: True if collection was created, False if it already existed
        
    Raises:
        Exception: If collection creation fails
    """
    client = get_qdrant_client()
    
    try:
        # Check if collection exists
        collections = client.get_collections().collections
        collection_exists = any(c.name == collection_name for c in collections)
        
        if collection_exists:
            return False
        
        # Create collection
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE
            )
        )
        
        return True
        
    except Exception as e:
        raise Exception(f"Failed to create collection '{collection_name}': {e}")

def reset_client():
    """
    Reset the global client instance. Useful for testing or config changes.
    """
    global _client_instance
    if _client_instance:
        try:
            _client_instance.close()
        except:
            pass
    _client_instance = None

def test_qdrant_connection() -> bool:
    """
    Test Qdrant connection and return success status.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        client = get_qdrant_client()
        collections = client.get_collections()
        return True
    except Exception as e:
        print(f"Qdrant connection test failed: {e}")
        return False 