from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.query_engine import CitationQueryEngine
from dotenv import load_dotenv
from .qdrant_client_factory import get_qdrant_client, create_collection_if_not_exists

class RAGEngine:
    def __init__(self, collection_name="rag_collection"):
        load_dotenv()
        
        # Configure global settings instead of ServiceContext
        Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-large", dimensions=3072)
        
        # Get client from factory
        self.client = get_qdrant_client()
        self.collection_name = collection_name
        
        # Ensure collection exists
        create_collection_if_not_exists(collection_name)
        
        # Set up vector store and index
        self.vector_store = QdrantVectorStore(client=self.client, collection_name=self.collection_name)
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        self.index = VectorStoreIndex.from_vector_store(self.vector_store)

    def index_file(self, file_path: str, case_id: int = None):
        # Load and index documents
        docs = SimpleDirectoryReader(input_files=[file_path]).load_data()
        self.index.insert_documents(docs)

    def query(self, query: str) -> dict:
        # Use CitationQueryEngine for answers with citations
        citation_query_engine = CitationQueryEngine.from_args(
            self.index,
            similarity_top_k=3,
            citation_chunk_size=512,
        )
        response = citation_query_engine.query(query)
        citations = []
        for i, node in enumerate(response.source_nodes):
            meta = node.node.metadata
            citations.append({
                "source": meta.get("file_name", f"chunk_{i+1}"),
                "text": node.node.get_text()[:200]
            })
        return {"answer": str(response), "citations": citations} 