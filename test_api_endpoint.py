#!/usr/bin/env python3
"""
Simple API endpoint test for the /query endpoint.

This script tests the HTTP API directly to ensure the endpoint works as expected.

Usage:
    python test_api_endpoint.py

Make sure your FastAPI server is running:
    uvicorn main:app --reload
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_BASE_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")
TEST_QUERIES = [
    {
        "query": "What are the main legal arguments?",
        "case_id": None
    },
    {
        "query": "What are the payment terms?",
        "case_id": 1
    },
    {
        "query": "How can this contract be terminated?",
        "case_id": None
    }
]

def test_query_endpoint():
    """Test the /query endpoint with various scenarios"""
    print("🔍 Testing Legal Hub Query API Endpoint\n")
    
    # Test server connectivity
    try:
        response = requests.get(f"{API_BASE_URL}/docs")
        if response.status_code == 200:
            print("✅ Server is running and accessible")
        else:
            print("❌ Server responded but with unexpected status")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure it's running:")
        print("   uvicorn main:app --reload")
        return False
    
    print(f"🌐 Testing endpoint: {API_BASE_URL}/query\n")
    
    for i, test_case in enumerate(TEST_QUERIES, 1):
        print(f"📋 Test {i}: {test_case['query']}")
        
        try:
            # Make the API request
            response = requests.post(
                f"{API_BASE_URL}/query",
                json=test_case,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Validate response structure
                required_fields = ["answer", "citations", "retrieved_chunks", "case_id_filter"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    print(f"   ❌ Missing fields: {missing_fields}")
                else:
                    print("   ✅ Response structure valid")
                    print(f"   📄 Retrieved chunks: {data['retrieved_chunks']}")
                    print(f"   📚 Citations: {len(data['citations'])}")
                    
                    if data.get('error'):
                        print(f"   ⚠️  Error in response: {data['error']}")
                    else:
                        # Show answer preview
                        answer = data['answer']
                        preview = answer[:150] + "..." if len(answer) > 150 else answer
                        print(f"   💡 Answer preview: {preview}")
                        
                        # Show citation preview
                        if data['citations']:
                            first_citation = data['citations'][0]
                            cite_preview = first_citation.get('text', '')[:100] + "..."
                            print(f"   📖 First citation: {cite_preview}")
            
            elif response.status_code == 422:
                print("   ❌ Validation error:")
                try:
                    error_data = response.json()
                    print(f"      {json.dumps(error_data, indent=2)}")
                except:
                    print(f"      {response.text}")
            
            elif response.status_code == 500:
                print("   ❌ Server error:")
                try:
                    error_data = response.json()
                    print(f"      {error_data.get('detail', 'Unknown error')}")
                except:
                    print(f"      {response.text}")
            
            else:
                print(f"   ❌ Unexpected status code: {response.status_code}")
                print(f"      Response: {response.text[:200]}...")
                
        except requests.exceptions.Timeout:
            print("   ❌ Request timed out (>30s)")
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request failed: {e}")
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
        
        print()  # Empty line between tests
    
    print("🏁 API endpoint testing completed!")
    return True

def test_upload_endpoint():
    """Quick test of the upload endpoint (optional)"""
    print("\n📤 Testing Upload Endpoint (optional)")
    
    # Create a simple test file
    test_content = "This is a test legal document with payment terms of 30 days."
    
    try:
        # Note: This is a simplified test - in reality you'd need a proper DOCX file
        files = {'file': ('test.txt', test_content, 'text/plain')}
        data = {'case_id': '999'}
        
        response = requests.post(
            f"{API_BASE_URL}/documents/upload",
            files=files,
            data=data,
            timeout=30
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ Upload endpoint is working")
            upload_data = response.json()
            print(f"   📄 Uploaded document ID: {upload_data.get('id')}")
        else:
            print(f"   ℹ️  Upload test status: {response.status_code}")
            print("   (This might be expected if you don't have a real DOCX file)")
            
    except Exception as e:
        print(f"   ℹ️  Upload test skipped: {e}")

if __name__ == "__main__":
    print("=" * 60)
    success = test_query_endpoint()
    test_upload_endpoint()
    print("=" * 60)
    
    if success:
        print("\n🎉 API testing completed! Check the results above.")
        print("\n💡 Tip: To test with real documents:")
        print("   1. Upload a document via the /documents/upload endpoint")
        print("   2. Run these queries to see better results")
        print(f"\n🔗 API Documentation: {API_BASE_URL}/docs")
    else:
        print("\n❌ API testing failed. Check your server setup.")
        exit(1) 