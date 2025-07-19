from llama_index.embeddings.openai import OpenAIEmbedding
from typing import List

def embed_nodes(nodes: List) -> None:
    """
    Embeds each node's content using OpenAIEmbedding and sets the embedding on the node.
    """
    embed_model = OpenAIEmbedding(model="text-embedding-3-large", dimensions=3072)

    for node in nodes:
        text = node.get_content()
        embedding = embed_model.get_text_embedding(text)
        node.embedding = embedding 