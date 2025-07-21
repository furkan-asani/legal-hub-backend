from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.query_engine import CitationQueryEngine
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters, FilterOperator
from dotenv import load_dotenv
from rag.qdrant_client_factory import get_qdrant_client, create_collection_if_not_exists
from rag.reranker import create_reranker_from_config, get_reranker_config

class RAGEngine:
    def __init__(self, collection_name="law-test"):
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
        
        # Initialize reranker
        self.reranker = create_reranker_from_config()
        self.reranker_config = get_reranker_config()
        
        # Log reranker status
        if self.reranker:
            print(f"✓ Reranker initialized: {self.reranker_config['provider']} (top_n={self.reranker_config['top_n']})")
        else:
            print("ℹ️ Reranker disabled or unavailable")

    def index_file(self, file_path: str, case_id: int = None):
        # Load and index documents
        docs = SimpleDirectoryReader(input_files=[file_path]).load_data()
        self.index.insert_documents(docs)

    def query(self, query: str, case_id: int = None) -> dict:
        # Configure node postprocessors (including reranker if available)
        node_postprocessors = []
        if self.reranker:
            node_postprocessors.append(self.reranker)
        
        # Build metadata filter if case_id is provided
        filters = None
        if case_id is not None:
            filters = MetadataFilters(
                filters=[MetadataFilter(key="case_id", value=case_id, operator=FilterOperator.EQ)]
            )
        
        # Use CitationQueryEngine for answers with citations
        citation_query_engine = CitationQueryEngine.from_args(
            self.index,
            similarity_top_k=5,  # Get more results before reranking
            citation_chunk_size=512,
            node_postprocessors=node_postprocessors,
            filters=filters
        )
        
        response = citation_query_engine.query(query)
        citations = []
        for i, node in enumerate(response.source_nodes):
            meta = node.node.metadata
            citation = {
                "source": meta.get("file_name", f"chunk_{i+1}"),
                "text": node.node.get_text()[:200]
            }
            # Add case_id to citation if present
            if "case_id" in meta:
                citation["case_id"] = meta["case_id"]
            # Add reranking score if available
            if hasattr(node, 'score') and node.score is not None:
                citation["score"] = node.score
                citation["reranked"] = True
            citations.append(citation)
        
        result = {
            "answer": str(response), 
            "citations": citations,
            "retrieved_chunks": len(response.source_nodes),
            "case_id_filter": case_id
        }
        
        # Add reranker info to result
        if self.reranker:
            result["reranker_used"] = self.reranker_config['provider']
            result["reranker_top_n"] = self.reranker_config['top_n']
        else:
            result["reranker_used"] = "none"
        
        return result

    def query_without_reranker(self, query: str) -> dict:
        """
        Query method that bypasses reranking for comparison purposes.
        """
        # Use CitationQueryEngine without any postprocessors
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
                "text": node.node.get_text()[:200],
                "reranked": False
            })
        
        return {
            "answer": str(response), 
            "citations": citations,
            "reranker_used": "none (bypassed)"
        }

    def compare_with_and_without_reranker(self, query: str) -> dict:
        """
        Compare results with and without reranking to show the difference.
        """
        if not self.reranker:
            return {"error": "Reranker not available for comparison"}
        
        # Get results with reranker
        with_reranker = self.query(query)
        
        # Get results without reranker
        without_reranker = self.query_without_reranker(query)
        
        return {
            "query": query,
            "with_reranker": with_reranker,
            "without_reranker": without_reranker,
            "reranker_config": self.reranker_config
        } 

    def get_chunks_by_case_id(self, case_id: int, limit: int = 1000):
        """
        Retrieve all chunks (points) for a given case_id from Qdrant.
        Returns a list of dicts with 'text' and 'metadata'.
        """
        from qdrant_client import models
        scroll_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="case_id",
                    match=models.MatchValue(value=case_id)
                )
            ]
        )
        all_points = []
        next_page = None
        while True:
            points, next_page = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=scroll_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False,
                offset=next_page
            )
            for point in points:
                payload = point.payload or {}
                all_points.append({
                    "text": payload.get("text", ""),
                    "metadata": payload
                })
            if not next_page:
                break
        return all_points 