import os
import requests
from dotenv import load_dotenv
from rag.qdrant_client_factory import get_qdrant_client, test_qdrant_connection

def test_qdrant_connection_rest():
    """
    Tests the connection to the Qdrant database via REST API.
    """
    print("Attempting to connect to Qdrant via REST API...")

    load_dotenv()
    
    qdrant_host = os.getenv("QDRANT_HOST")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    
    if not qdrant_host or not qdrant_api_key:
        print("Error: QDRANT_HOST and QDRANT_API_KEY must be set in your .env file.")
        return False

    headers = {
        "Content-Type": "application/json",
        "api-key": qdrant_api_key,
    }
    
    collections_url = f"{qdrant_host}/collections"

    try:
        response = requests.get(collections_url, headers=headers, timeout=10)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)

        data = response.json()
        collections = data.get("result", {}).get("collections", [])
        
        print("\n✅ Successfully connected to Qdrant via REST API!")
        print(f"   Host: {qdrant_host}")
        if collections:
            print("\nAvailable collections:")
            for collection in collections:
                print(f"  - {collection['name']}")
        else:
            print("\nNo collections found.")
        return True

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Failed to connect to Qdrant via REST API.")
        print(f"   Error: {e}")
        print("\nPlease check the following:")
        print("  1. Is your Qdrant instance running and accessible at the specified HOST?")
        print("  2. Is your internet connection or network configuration correct?")
        print("  3. Is the QDRANT_HOST in your .env file correct (e.g., includes https://)?")
        return False
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
        return False

def test_qdrant_connection_client():
    """
    Tests the connection to the Qdrant database via the centralized client factory.
    """
    print("\nAttempting to connect to Qdrant via centralized client factory...")
    
    try:
        # Use the factory method
        client = get_qdrant_client()
        collections = client.get_collections().collections
        
        print("\n✅ Successfully connected to Qdrant via client factory!")
        print(f"   Host: {os.getenv('QDRANT_HOST')}")
        if collections:
            print("\nAvailable collections:")
            for collection in collections:
                print(f"  - {collection.name}")
        else:
            print("\nNo collections found.")
        return True
        
    except Exception as e:
        print(f"\n❌ Failed to connect to Qdrant via client factory.")
        print(f"   Error: {e}")
        return False

def test_qdrant_factory_method():
    """
    Test the factory's built-in connection test method.
    """
    print("\nTesting Qdrant factory connection method...")
    
    success = test_qdrant_connection()
    if success:
        print("✅ Factory connection test passed!")
    else:
        print("❌ Factory connection test failed!")
    
    return success

if __name__ == "__main__":
    print("\n--- Qdrant Connection Test ---")
    
    # Test REST API connection
    rest_success = test_qdrant_connection_rest()
    
    # Test client factory connection
    client_success = test_qdrant_connection_client()
    
    # Test factory method
    factory_success = test_qdrant_factory_method()
    
    print("\n--- Summary ---")
    if all([rest_success, client_success, factory_success]):
        print("✅ All Qdrant connection tests passed!")
    else:
        results = []
        if rest_success:
            results.append("REST API ✅")
        else:
            results.append("REST API ❌")
            
        if client_success:
            results.append("Client Factory ✅")
        else:
            results.append("Client Factory ❌")
            
        if factory_success:
            results.append("Factory Method ✅")
        else:
            results.append("Factory Method ❌")
            
        print(f"Test results: {', '.join(results)}")
    
    print("\n--- Environment Variables Needed ---")
    print("Required:")
    print("  - QDRANT_HOST (e.g., https://your-cluster.qdrant.io)")
    print("  - QDRANT_API_KEY (your Qdrant API key)")
    
    if not (rest_success and client_success and factory_success):
        exit(1)