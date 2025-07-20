"""
Reranker module for improving search result relevance using various reranking strategies.
Supports Cohere Rerank and other reranking methods.
"""

import os
from typing import Optional, List, Any
from dotenv import load_dotenv

def get_reranker(provider: str = "cohere", top_n: int = 3) -> Optional[Any]:
    """
    Factory function to get a configured reranker based on the provider.
    
    Args:
        provider: Reranking provider ("cohere", "none")
        top_n: Number of top results to return after reranking
        
    Returns:
        Configured reranker instance or None if disabled
        
    Raises:
        ImportError: If required reranker package is not installed
        ValueError: If required API key is not set
    """
    load_dotenv()
    
    if provider.lower() == "none" or provider.lower() == "disabled":
        return None
    
    elif provider.lower() == "cohere":
        try:
            from llama_index.postprocessor.cohere_rerank import CohereRerank
            
            api_key = os.getenv("COHERE_API_KEY")
            if not api_key:
                raise ValueError(
                    "COHERE_API_KEY must be set in environment variables to use Cohere reranking. "
                    "Get your API key from https://dashboard.cohere.ai/api-keys"
                )
            
            return CohereRerank(api_key=api_key, top_n=top_n)
            
        except ImportError:
            raise ImportError(
                "Cohere reranker not installed. Install with: "
                "pip install llama-index-postprocessor-cohere-rerank"
            )
    
    else:
        raise ValueError(f"Unsupported reranker provider: {provider}")

def is_reranker_available(provider: str = "cohere") -> bool:
    """
    Check if a reranker provider is available (has required dependencies and API keys).
    
    Args:
        provider: Reranking provider to check
        
    Returns:
        bool: True if provider is available, False otherwise
    """
    try:
        reranker = get_reranker(provider)
        return reranker is not None
    except (ImportError, ValueError):
        return False

def get_reranker_config() -> dict:
    """
    Get reranker configuration from environment variables.
    
    Returns:
        dict: Configuration dictionary with provider and settings
    """
    load_dotenv()
    
    return {
        "provider": os.getenv("RERANKER_PROVIDER", "cohere"),
        "top_n": int(os.getenv("RERANKER_TOP_N", "3")),
        "enabled": os.getenv("RERANKER_ENABLED", "true").lower() == "true"
    }

def create_reranker_from_config() -> Optional[Any]:
    """
    Create a reranker instance from environment configuration.
    
    Returns:
        Configured reranker instance or None if disabled
    """
    config = get_reranker_config()
    
    if not config["enabled"]:
        return None
    
    try:
        return get_reranker(config["provider"], config["top_n"])
    except (ImportError, ValueError) as e:
        print(f"Warning: Could not initialize reranker: {e}")
        return None 