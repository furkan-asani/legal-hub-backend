from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, ServiceContext, StorageContext
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
import qdrant_client
import os
from llama_index.core.query_engine import CitationQueryEngine
from dotenv import load_dotenv

class RAGEngine:
    def __init__(self, collection_name="rag_collection"):
        load_dotenv()
        QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
        QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
        if QDRANT_API_KEY is None or QDRANT_API_KEY == "" or QDRANT_HOST is None or QDRANT_HOST == "":
            raise ValueError("QDRANT_API_KEY and QDRANT_HOST must be set")
        self.client = qdrant_client.QdrantClient(url=QDRANT_HOST, api_key=QDRANT_API_KEY)
        self.collection_name = collection_name
        self.vector_store = QdrantVectorStore(client=self.client, collection_name=self.collection_name)
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        self.index = VectorStoreIndex.from_vector_store(self.vector_store)
        self.service_context = ServiceContext.from_defaults(embed_model=OpenAIEmbedding(model="text-embedding-3-large", dimensions=3072))

    def index_file(self, file_path: str, case_id: int = None):
        reader = SimpleDirectoryReader(input_files=[file_path])
        docs = reader.load_data()
        if case_id is not None:
            for doc in docs:
                if hasattr(doc, 'metadata') and isinstance(doc.metadata, dict):
                    doc.metadata["case_id"] = case_id
                else:
                    doc.metadata = {"case_id": case_id}
        self.index.insert_documents(docs, service_context=self.service_context)

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
            meta = node.node.metadata or {}
            citations.append({
                "source": meta.get("file_name", f"chunk_{i+1}"),
                "text": node.node.get_text()[:200]
            })
        return {"answer": str(response), "citations": citations} 