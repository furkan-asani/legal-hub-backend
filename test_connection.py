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
        return

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
        
        print("\n✅ Successfully connected to Qdrant!")
        print(f"   Host: {qdrant_host}")

        if collections:
            print("\nAvailable collections:")
            for collection in collections:
                print(f"  - {collection['name']}")
        else:
            print("\nNo collections found.")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Failed to connect to Qdrant.")
        print(f"   Error: {e}")
        print("\nPlease check the following:")
        print("  1. Is your Qdrant instance running and accessible at the specified HOST?")
        print("  2. Is your internet connection or network configuration correct?")
        print("  3. Is the QDRANT_HOST in your .env file correct (e.g., includes https://)?")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    test_qdrant_connection_rest() 