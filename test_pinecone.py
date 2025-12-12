"""Diagnostic script to test Pinecone connection and query."""

import logging
from src.pinecone_rag import PineconeRAG
from src.utils import setup_logging

# Set up logging to see all details
setup_logging(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def main():
    print("=" * 60)
    print("Pinecone Diagnostic Test")
    print("=" * 60)
    print()
    
    try:
        # Initialize Pinecone RAG
        print("1. Initializing Pinecone connection...")
        rag = PineconeRAG()
        print("   [OK] Connected successfully\n")
        
        # Test connection
        print("2. Testing connection...")
        test_results = rag.test_connection()
        print(f"   Connected: {test_results['connected']}")
        if test_results.get('stats'):
            print(f"   Index Stats: {test_results['stats']}")
        if test_results.get('error'):
            print(f"   Error: {test_results['error']}")
        print()
        
        # Try a sample query
        print("3. Testing sample query...")
        test_query = "What is the constitution?"
        print(f"   Query: '{test_query}'")
        print()
        
        context, results = rag.retrieve_context(test_query)
        
        print("4. Query Results:")
        print(f"   Results count: {len(results)}")
        print(f"   Context length: {len(context)} characters")
        print()
        
        if results:
            print("5. First Result Details:")
            first = results[0]
            if isinstance(first, dict):
                print(f"   Type: dict")
                print(f"   Keys: {list(first.keys())}")
                print(f"   Score: {first.get('score', 'N/A')}")
                print(f"   ID: {first.get('id', 'N/A')}")
                metadata = first.get('metadata', {})
                print(f"   Metadata type: {type(metadata)}")
                if isinstance(metadata, dict):
                    print(f"   Metadata keys: {list(metadata.keys())}")
                    print(f"   Metadata: {metadata}")
                else:
                    print(f"   Metadata: {metadata}")
            else:
                print(f"   Type: {type(first)}")
                print(f"   Attributes: {dir(first)}")
                if hasattr(first, 'metadata'):
                    print(f"   Metadata: {getattr(first, 'metadata', None)}")
            print()
        else:
            print("   [WARNING] No results returned!")
            print()
            print("   Possible issues:")
            print("   - Index might be empty")
            print("   - Embedding dimension mismatch")
            print("   - Query doesn't match any vectors")
            print()
        
        if context:
            print("6. Extracted Context:")
            print(f"   {context[:200]}..." if len(context) > 200 else f"   {context}")
        else:
            print("6. Context: (EMPTY)")
            if results:
                print("   [WARNING] Results were returned but context extraction failed!")
                print("   Check metadata structure above.")
        
    except Exception as e:
        print(f"\n[ERROR] Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

