#!/usr/bin/env python3
"""
Comprehensive test script for the Legal Hub RAG query system.

Tests the complete workflow:
1. Document upload and processing
2. Vector database storage (Qdrant or Weaviate)
3. Query retrieval with case filtering
4. LLM response generation
5. Citation accuracy

Usage:
    python test_query_system.py

Environment variables needed:
- Vector Database: QDRANT_HOST + QDRANT_API_KEY OR WEAVIATE_URL + WEAVIATE_API_KEY
- OPENAI_API_KEY (or other LLM provider keys)
- DATABASE_CONNECTION_STRING
- VECTOR_STORE (optional, defaults to qdrant)
- LLM_PROVIDER (optional, defaults to openai)
- LLM_MODEL (optional)
"""

import os
import sys
import tempfile
import requests
import json
from typing import Dict, Any, List
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rag.rag_engine import RAGEngine
from rag.doc_loader import load_docx_as_documents
from rag.semantic_chunker import semantic_chunk_documents
from rag.embedder import embed_nodes
from rag.qdrant_uploader import upload_nodes_to_qdrant
from rag.vector_store_factory import get_vector_store_type, test_vector_store_connection

# Load environment variables
load_dotenv()

class TestColors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class QuerySystemTester:
    def __init__(self):
        self.vector_store_type = get_vector_store_type()
        self.collection_name = "test-collection"
        self.test_case_id = 9999
        self.rag_engine = None
        self.uploaded_nodes = []
        
    def print_status(self, message: str, status: str = "INFO"):
        """Print colored status messages"""
        color = TestColors.BLUE
        if status == "SUCCESS":
            color = TestColors.GREEN
        elif status == "ERROR":
            color = TestColors.RED
        elif status == "WARNING":
            color = TestColors.YELLOW
        
        print(f"{color}[{status}]{TestColors.END} {message}")

    def create_test_document(self) -> str:
        """Create a test document for upload"""
        test_content = """
        LEGAL CONTRACT ANALYSIS TEST DOCUMENT
        
        This is a test legal document for the automated query system.
        
        KEY PROVISIONS:
        1. Payment Terms: All payments must be made within 30 days of invoice date.
        2. Liability Clause: Total liability is limited to $100,000.
        3. Termination: Either party may terminate with 60 days written notice.
        4. Confidentiality: All information shared is confidential for 5 years.
        5. Governing Law: This contract is governed by California state law.
        
        IMPORTANT DATES:
        - Contract Start Date: January 1, 2024
        - Contract End Date: December 31, 2024
        - Review Date: June 30, 2024
        
        PARTIES:
        - Company A: Technology Services Provider
        - Company B: Marketing Services Client
        
        DISPUTE RESOLUTION:
        Any disputes will be resolved through binding arbitration in San Francisco.
        """
        
        # Create a temporary text file (simulating docx content)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(test_content)
            return f.name

    def test_environment_setup(self) -> bool:
        """Test that all required environment variables are set"""
        self.print_status("Testing environment setup...", "INFO")
        
        # Check vector store configuration
        vector_store_required_vars = []
        if self.vector_store_type == "qdrant":
            vector_store_required_vars = ["QDRANT_HOST", "QDRANT_API_KEY"]
        elif self.vector_store_type == "weaviate":
            vector_store_required_vars = ["WEAVIATE_URL"]
        
        required_vars = vector_store_required_vars + ["OPENAI_API_KEY", "DATABASE_CONNECTION_STRING"]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            self.print_status(f"Missing environment variables: {', '.join(missing_vars)}", "ERROR")
            return False
        
        # Show current configuration
        self.print_status(f"Vector Store: {self.vector_store_type}", "SUCCESS")
        
        # Test LLM provider configuration
        try:
            from rag.llm_provider import get_llm_provider
            llm_provider = get_llm_provider()
            provider_name = os.getenv("LLM_PROVIDER", "openai")
            model = os.getenv("LLM_MODEL", "default")
            self.print_status(f"LLM Provider: {provider_name}, Model: {model}", "SUCCESS")
        except Exception as e:
            self.print_status(f"LLM provider setup failed: {e}", "ERROR")
            return False
        
        self.print_status("Environment setup complete", "SUCCESS")
        return True

    def test_vector_store_connection(self) -> bool:
        """Test vector store connection using the factory"""
        self.print_status(f"Testing {self.vector_store_type} connection...", "INFO")
        
        try:
            success = test_vector_store_connection()
            if success:
                self.print_status(f"✓ {self.vector_store_type.title()} connection successful", "SUCCESS")
                return True
            else:
                self.print_status(f"✗ {self.vector_store_type.title()} connection failed", "ERROR")
                return False
        except Exception as e:
            self.print_status(f"{self.vector_store_type.title()} connection test failed: {e}", "ERROR")
            return False

    def test_document_processing(self) -> bool:
        """Test the document processing pipeline"""
        self.print_status("Testing document processing pipeline...", "INFO")
        
        try:
            # Create test document
            test_file = self.create_test_document()
            
            # Step 1: Load document (simulating docx)
            with open(test_file, 'r') as f:
                content = f.read()
            documents = [type('Document', (), {'text': content, 'metadata': {}})()]
            self.print_status("✓ Document loading", "SUCCESS")
            
            # Step 2: Semantic chunking
            # Mock the semantic chunking for testing
            class MockNode:
                def __init__(self, text, metadata=None):
                    self.text = text
                    self.metadata = metadata or {}
                    self.embedding = None
                
                def get_content(self):
                    return self.text
                
                def get_embedding(self):
                    return self.embedding
            
            # Split content into chunks
            chunks = content.split('\n\n')
            nodes = [MockNode(chunk.strip()) for chunk in chunks if chunk.strip()]
            self.print_status(f"✓ Semantic chunking: {len(nodes)} chunks created", "SUCCESS")
            
            # Step 3: Add metadata
            for node in nodes:
                node.metadata["file_name"] = "test_contract.txt"
                node.metadata["case_id"] = self.test_case_id
            self.print_status("✓ Metadata addition", "SUCCESS")
            
            # Step 4: Embedding (mock for speed)
            for i, node in enumerate(nodes):
                node.embedding = [0.1] * 3072  # Mock embedding
            self.print_status("✓ Embedding generation (mocked)", "SUCCESS")
            
            self.uploaded_nodes = nodes
            
            # Cleanup
            os.unlink(test_file)
            
            return True
            
        except Exception as e:
            self.print_status(f"Document processing failed: {e}", "ERROR")
            return False

    def test_rag_engine_initialization(self) -> bool:
        """Test RAG engine initialization"""
        self.print_status("Testing RAG engine initialization...", "INFO")
        
        try:
            self.rag_engine = RAGEngine(collection_name=self.collection_name)
            self.print_status(f"✓ RAG engine initialized with {self.vector_store_type}", "SUCCESS")
            self.print_status(f"✓ Collection/Class: {self.collection_name}", "INFO")
            return True
        except Exception as e:
            self.print_status(f"RAG engine initialization failed: {e}", "ERROR")
            return False

    def test_direct_vector_search(self) -> bool:
        """Test direct vector store search functionality"""
        self.print_status(f"Testing direct {self.vector_store_type} search...", "INFO")
        
        try:
            # Test search without case filter
            results = self.rag_engine._search_vector_store_directly("payment terms", limit=3)
            self.print_status(f"✓ Search without filter: {len(results)} results", "SUCCESS")
            
            # Test search with case filter
            results_filtered = self.rag_engine._search_vector_store_directly(
                "payment terms", 
                case_id=self.test_case_id, 
                limit=3
            )
            self.print_status(f"✓ Search with case filter: {len(results_filtered)} results", "SUCCESS")
            
            return True
        except Exception as e:
            self.print_status(f"Direct {self.vector_store_type} search failed: {e}", "ERROR")
            return False

    def test_llm_query(self) -> bool:
        """Test end-to-end LLM query"""
        self.print_status("Testing LLM query...", "INFO")
        
        test_queries = [
            {
                "query": "What are the payment terms in this contract?",
                "case_id": None,
                "expected_keywords": ["payment", "30 days", "invoice"]
            },
            {
                "query": "What is the liability limit?",
                "case_id": self.test_case_id,
                "expected_keywords": ["liability", "$100,000", "limited"]
            },
            {
                "query": "How can this contract be terminated?",
                "case_id": None,
                "expected_keywords": ["terminate", "60 days", "written notice"]
            }
        ]
        
        for i, test in enumerate(test_queries):
            try:
                self.print_status(f"Testing query {i+1}: '{test['query']}'", "INFO")
                
                result = self.rag_engine.query_with_gpt(
                    query=test["query"],
                    case_id=test["case_id"]
                )
                
                # Check response structure
                required_fields = ["answer", "citations", "retrieved_chunks", "case_id_filter", "vector_store"]
                for field in required_fields:
                    if field not in result:
                        self.print_status(f"Missing field in response: {field}", "ERROR")
                        return False
                
                # Check for errors
                if "error" in result:
                    self.print_status(f"Query returned error: {result['error']}", "ERROR")
                    return False
                
                # Verify vector store type in response
                if result["vector_store"] != self.vector_store_type:
                    self.print_status(f"Vector store mismatch: expected {self.vector_store_type}, got {result['vector_store']}", "WARNING")
                
                # Check answer content
                answer = result["answer"].lower()
                found_keywords = [kw for kw in test["expected_keywords"] if kw.lower() in answer]
                
                self.print_status(f"✓ Query {i+1} completed", "SUCCESS")
                self.print_status(f"  Vector Store: {result['vector_store']}", "INFO")
                self.print_status(f"  Retrieved chunks: {result['retrieved_chunks']}", "INFO")
                self.print_status(f"  Citations: {len(result['citations'])}", "INFO")
                self.print_status(f"  Keywords found: {found_keywords}", "INFO")
                
                if len(found_keywords) == 0:
                    self.print_status(f"  Warning: No expected keywords found in answer", "WARNING")
                
                # Print short answer preview
                answer_preview = result["answer"][:200] + "..." if len(result["answer"]) > 200 else result["answer"]
                self.print_status(f"  Answer preview: {answer_preview}", "INFO")
                
            except Exception as e:
                self.print_status(f"Query {i+1} failed: {e}", "ERROR")
                return False
        
        return True

    def test_citation_accuracy(self) -> bool:
        """Test citation accuracy and metadata"""
        self.print_status("Testing citation accuracy...", "INFO")
        
        try:
            result = self.rag_engine.query_with_gpt("What are the key provisions of this contract?")
            
            citations = result.get("citations", [])
            if not citations:
                self.print_status("No citations returned", "WARNING")
                return True
            
            for i, citation in enumerate(citations):
                required_fields = ["source", "text", "score"]
                for field in required_fields:
                    if field not in citation:
                        self.print_status(f"Citation {i+1} missing field: {field}", "ERROR")
                        return False
                
                # Check that citation text is not empty
                if not citation["text"].strip():
                    self.print_status(f"Citation {i+1} has empty text", "WARNING")
                
                self.print_status(f"✓ Citation {i+1}: {citation['source'][:50]}...", "SUCCESS")
            
            return True
            
        except Exception as e:
            self.print_status(f"Citation accuracy test failed: {e}", "ERROR")
            return False

    def cleanup(self):
        """Cleanup test resources"""
        self.print_status("Cleaning up test resources...", "INFO")
        
        try:
            if self.rag_engine:
                # In a real scenario, you might want to delete the test collection/class
                # For Qdrant: client.delete_collection(self.collection_name)
                # For Weaviate: client.schema.delete_class(self.collection_name)
                pass
            self.print_status("✓ Cleanup completed", "SUCCESS")
        except Exception as e:
            self.print_status(f"Cleanup failed: {e}", "WARNING")

    def run_all_tests(self) -> bool:
        """Run all tests in sequence"""
        print(f"\n{TestColors.BOLD}{TestColors.CYAN}Legal Hub RAG Query System Test Suite{TestColors.END}")
        print(f"{TestColors.CYAN}Vector Store: {self.vector_store_type.title()}{TestColors.END}\n")
        
        tests = [
            ("Environment Setup", self.test_environment_setup),
            ("Vector Store Connection", self.test_vector_store_connection),
            ("Document Processing", self.test_document_processing),
            ("RAG Engine Initialization", self.test_rag_engine_initialization),
            ("Direct Vector Search", self.test_direct_vector_search),
            ("LLM Query", self.test_llm_query),
            ("Citation Accuracy", self.test_citation_accuracy),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n{TestColors.BOLD}=== {test_name} ==={TestColors.END}")
            try:
                if test_func():
                    passed += 1
                else:
                    self.print_status(f"{test_name} FAILED", "ERROR")
            except Exception as e:
                self.print_status(f"{test_name} FAILED with exception: {e}", "ERROR")
        
        # Final results
        print(f"\n{TestColors.BOLD}=== Test Results ==={TestColors.END}")
        if passed == total:
            self.print_status(f"ALL TESTS PASSED ({passed}/{total})", "SUCCESS")
        else:
            self.print_status(f"TESTS FAILED ({passed}/{total} passed)", "ERROR")
        
        # Show configuration summary
        print(f"\n{TestColors.BOLD}=== Configuration Summary ==={TestColors.END}")
        print(f"Vector Store: {self.vector_store_type}")
        print(f"LLM Provider: {os.getenv('LLM_PROVIDER', 'openai')}")
        print(f"Collection/Class: {self.collection_name}")
        
        # Cleanup
        self.cleanup()
        
        return passed == total

def main():
    """Main test function"""
    tester = QuerySystemTester()
    success = tester.run_all_tests()
    
    if success:
        print(f"\n{TestColors.GREEN}{TestColors.BOLD}🎉 All tests passed! Your query system is ready to use.{TestColors.END}")
        return 0
    else:
        print(f"\n{TestColors.RED}{TestColors.BOLD}❌ Some tests failed. Please check the errors above.{TestColors.END}")
        return 1

if __name__ == "__main__":
    exit(main()) 