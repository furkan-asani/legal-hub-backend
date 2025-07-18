import os
import requests
from dotenv import load_dotenv

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
    Tests the connection to the Qdrant database via the Qdrant client.
    """
    print("\nAttempting to connect to Qdrant via Qdrant client...")
    try:
        from qdrant_client import QdrantClient
        load_dotenv()
        qdrant_host = os.getenv("QDRANT_HOST")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        if not qdrant_host or not qdrant_api_key:
            print("Error: QDRANT_HOST and QDRANT_API_KEY must be set in your .env file.")
            return False
        client = QdrantClient(url=qdrant_host, api_key=qdrant_api_key, port= 6333, prefer_grpc=True, https=True)
        collections = client.get_collections().collections
        print("\n✅ Successfully connected to Qdrant via Qdrant client!")
        print(f"   Host: {qdrant_host}")
        if collections:
            print("\nAvailable collections:")
            for collection in collections:
                print(f"  - {collection.name}")
        else:
            print("\nNo collections found.")
        return True
    except Exception as e:
        print(f"\n❌ Failed to connect to Qdrant via Qdrant client.")
        print(f"   Error: {e}")
        return False

if __name__ == "__main__":
    print("\n--- Qdrant Connection Test ---")
    rest_success = test_qdrant_connection_rest()
    client_success = test_qdrant_connection_client()
    print("\n--- Summary ---")
    if rest_success and client_success:
        print("Both REST API and Qdrant client connections succeeded.")
    elif rest_success:
        print("REST API connection succeeded, but Qdrant client connection failed.")
    elif client_success:
        print("Qdrant client connection succeeded, but REST API connection failed.")
    else:
        print("Both REST API and Qdrant client connections failed.") 