import os
import sys
from langchain_core.documents import Document

# Safe import wrapper to identify missing dependencies
try:
    from engine_optimized import OptimizedRAGEngine
except ImportError as e:
    print(f"CRITICAL: Failed to import OptimizedRAGEngine: {e}")
    sys.exit(1)

def test_ingestion():
    print("--- Starting Ingestion Test ---")
    
    # 1. Initialize Engine
    print("1. Initializing RAG Engine...")
    try:
        engine = OptimizedRAGEngine()
        # Force the check of vectorstore connection
        vs = engine.get_vectorstore()
        print("   -> Engine initialized and connected to OpenSearch.")
    except Exception as e:
        print(f"   -> FACTAL: Engine initialization failed: {e}")
        return

    # 2. Create Dummy Document
    print("2. Creating Test Document...")
    docs = [
        Document(page_content="This is a test document to verify the ingestion pipeline.", metadata={"source": "test_doc.txt", "page": 1})
    ]
    
    # 3. Test Embedding Generation (Implicitly in ingest, but let's try explicitly if possible or just run ingest)
    print("3. Attempting to ingest document...")
    try:
        # OptimizedRAGEngine expects a list of lists of chunks (batch processing structure)
        # engine.ingest_documents_bulk([[doc1, doc2], [doc3]])
        engine.ingest_documents_bulk([docs]) 
        print("   -> Ingestion method called without error.")
    except Exception as e:
        print(f"   -> FATAL: Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # 4. Verify Indexing
    print("4. Verifying document in index...")
    try:
        count = engine.get_document_count()
        print(f"   -> Total documents in index: {count}")
        
        # Try to search for it
        print("5. Attempting retrieval...")
        results, _ = engine.query_with_cache("test document pipeline")
        print(f"   -> Retrieval Result snippet: {results[:100]}...")
        
    except Exception as e:
        print(f"   -> FATAL: Verification failed: {e}")

    print("--- Test Complete ---")

if __name__ == "__main__":
    test_ingestion()
