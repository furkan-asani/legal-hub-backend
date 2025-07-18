from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.openai import OpenAIEmbedding
import os


def semantic_chunk_documents(documents, buffer_size=1, breakpoint_percentile_threshold=95):
    """
    Splits loaded documents into semantically meaningful chunks using LlamaIndex's SemanticSplitterNodeParser.

    Args:
        documents: List of loaded documents (as from SimpleDirectoryReader).
        buffer_size: Buffer size for the splitter (default: 1).
        breakpoint_percentile_threshold: Percentile threshold for semantic breakpoints (default: 95).

    Returns:
        List of semantic chunks (nodes).
    """
    # Ensure OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        raise EnvironmentError("OPENAI_API_KEY must be set in the environment.")

    embed_model = OpenAIEmbedding(model="text-embedding-3-large", dimensions=3072)
    splitter = SemanticSplitterNodeParser(
        buffer_size=buffer_size,
        breakpoint_percentile_threshold=breakpoint_percentile_threshold,
        embed_model=embed_model
    )
    nodes = splitter.get_nodes_from_documents(documents)
    return nodes 