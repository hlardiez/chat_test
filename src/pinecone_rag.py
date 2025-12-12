"""Pinecone RAG system for retrieving relevant context."""

import logging
from typing import List
from pinecone import Pinecone
from config.settings import settings

logger = logging.getLogger(__name__)


class PineconeRAG:
    """Pinecone RAG client for vector similarity search."""
    
    def __init__(self):
        """Initialize Pinecone client with API key from settings."""
        try:
            logger.info("Initializing Pinecone client...")
            logger.info(f"API Key: {settings.pinecone_api_key[:10]}...{settings.pinecone_api_key[-5:] if len(settings.pinecone_api_key) > 15 else '***'}")
            logger.info(f"Index Name: {settings.pinecone_index_name}")
            
            # Initialize Pinecone client
            self.pc = Pinecone(api_key=settings.pinecone_api_key)
            self.index_name = settings.pinecone_index_name
            
            # Get the index (works with both Serverless and Pod-based indexes)
            logger.info(f"Connecting to index '{self.index_name}'...")
            self.index = self.pc.Index(self.index_name)
            
            # Try to get index stats to verify connection
            try:
                stats = self.index.describe_index_stats()
                logger.info(f"Index stats: {stats}")
                
                # Extract dimension from stats
                if hasattr(stats, 'dimension'):
                    self.index_dimension = stats.dimension
                elif isinstance(stats, dict) and 'dimension' in stats:
                    self.index_dimension = stats['dimension']
                else:
                    # Try to get from namespaces
                    if hasattr(stats, 'namespaces'):
                        namespaces = stats.namespaces if hasattr(stats, 'namespaces') else {}
                        if namespaces:
                            # Get dimension from first namespace
                            first_ns = list(namespaces.values())[0]
                            if hasattr(first_ns, 'dimension'):
                                self.index_dimension = first_ns.dimension
                            else:
                                self.index_dimension = None
                    else:
                        self.index_dimension = None
                
                if self.index_dimension:
                    logger.info(f"Index dimension: {self.index_dimension}")
                else:
                    logger.warning("Could not determine index dimension from stats")
                
                # Auto-detect namespace if not specified
                if not settings.pinecone_namespace:
                    # Get namespaces from stats
                    if isinstance(stats, dict):
                        namespaces = stats.get('namespaces', {})
                    elif hasattr(stats, 'namespaces'):
                        namespaces = stats.namespaces
                        # Convert to dict if it's an object
                        if not isinstance(namespaces, dict):
                            namespaces = {}
                    else:
                        namespaces = {}
                    
                    if namespaces:
                        # Use the namespace with the most vectors, or first non-empty namespace
                        namespace_list = list(namespaces.keys())
                        if namespace_list:
                            # Filter out empty namespace if there are others
                            non_empty = [ns for ns in namespace_list if ns]
                            if non_empty:
                                self.namespace = non_empty[0]
                                # Get vector count
                                ns_info = namespaces.get(self.namespace, {})
                                if isinstance(ns_info, dict):
                                    vector_count = ns_info.get('vector_count', 0)
                                elif hasattr(ns_info, 'vector_count'):
                                    vector_count = ns_info.vector_count
                                else:
                                    vector_count = 0
                                logger.info(f"Auto-detected namespace: '{self.namespace}' (has {vector_count} vectors)")
                                logger.debug(f"Namespace info: {ns_info}")
                            else:
                                self.namespace = ""
                                logger.info("Using default namespace (empty)")
                        else:
                            self.namespace = ""
                            logger.info("Using default namespace (empty)")
                    else:
                        self.namespace = ""
                        logger.info("No namespaces found, using default namespace (empty)")
                else:
                    self.namespace = settings.pinecone_namespace
                    logger.info(f"Using configured namespace: '{self.namespace}'")
                    
            except Exception as e:
                logger.warning(f"Could not get index stats: {str(e)}")
                self.index_dimension = None
                self.namespace = settings.pinecone_namespace or ""
            
            self.top_k = settings.rag_top_k
            logger.info(f"✓ Successfully connected to Pinecone index: {self.index_name}")
        except Exception as e:
            logger.error(f"❌ Error initializing Pinecone client: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            raise
    
    def retrieve_context(self, query: str) -> tuple[str, List]:
        """
        Retrieve relevant context from Pinecone based on query.
        
        Args:
            query: The user's question or query string
            
        Returns:
            Tuple of (formatted_context_string, raw_results)
        """
        try:
            logger.info(f"Starting Pinecone query for: '{query}'")
            logger.info(f"Index: {self.index_name}, Top-K: {self.top_k}")
            
            # Generate embedding
            logger.info("Generating query embedding...")
            embedding = self._get_query_embedding(query)
            embedding_dim = len(embedding)
            logger.info(f"Embedding generated: dimension={embedding_dim}, first 5 values={embedding[:5]}")
            
            # Check dimension mismatch
            if hasattr(self, 'index_dimension') and self.index_dimension:
                if embedding_dim != self.index_dimension:
                    logger.error(f"⚠️  DIMENSION MISMATCH!")
                    logger.error(f"   Embedding dimension: {embedding_dim}")
                    logger.error(f"   Index dimension: {self.index_dimension}")
                    logger.error(f"   This will cause the query to fail or return no results!")
                else:
                    logger.info(f"✓ Dimension match: {embedding_dim} == {self.index_dimension}")
            
            # Query Pinecone
            namespace = getattr(self, 'namespace', settings.pinecone_namespace or "")
            logger.info(f"Querying Pinecone index '{self.index_name}' in namespace '{namespace}'...")
            query_params = {
                "vector": embedding,
                "top_k": self.top_k,
                "include_metadata": True
            }
            if namespace:
                query_params["namespace"] = namespace
            query_response = self.index.query(**query_params)
            logger.info(f"Pinecone query completed. Response type: {type(query_response)}")
            logger.info(f"Response: {query_response}")
            
            # Handle both dict and object responses (Pinecone v7 returns QueryResponse object)
            if isinstance(query_response, dict):
                logger.info(f"Query response is a dict. Keys: {list(query_response.keys())}")
                results = query_response.get('matches', [])
            else:
                # If it's an object (QueryResponse), try to access matches attribute
                logger.info(f"Query response is an object: {type(query_response)}")
                
                # Try to_dict() method first (Pinecone QueryResponse has this)
                if hasattr(query_response, 'to_dict'):
                    try:
                        response_dict = query_response.to_dict()
                        logger.info(f"Converted to dict. Keys: {list(response_dict.keys())}")
                        results = response_dict.get('matches', [])
                    except Exception as e:
                        logger.warning(f"to_dict() failed: {str(e)}, trying direct access")
                        # Fall through to direct access
                
                # Try direct attribute access
                if 'results' not in locals() or not results:
                    if hasattr(query_response, 'matches'):
                        results = query_response.matches
                        logger.info(f"Accessed matches via .matches attribute")
                    elif hasattr(query_response, 'get'):
                        results = query_response.get('matches', [])
                    else:
                        # Try to convert to dict if possible
                        try:
                            if hasattr(query_response, '__dict__'):
                                results = query_response.__dict__.get('matches', [])
                            else:
                                results = []
                                logger.warning("Could not extract matches from response object")
                        except Exception as e:
                            logger.error(f"Error extracting matches: {str(e)}")
                            results = []
            
            logger.info(f"Retrieved {len(results)} results from Pinecone")
            
            # Detailed logging of results structure
            if results:
                first_result = results[0]
                logger.info(f"First result type: {type(first_result)}")
                logger.info(f"First result: {first_result}")
                
                if isinstance(first_result, dict):
                    logger.info(f"First result keys: {list(first_result.keys())}")
                    metadata = first_result.get('metadata', {})
                    logger.info(f"First result metadata type: {type(metadata)}")
                    logger.info(f"First result metadata: {metadata}")
                    if isinstance(metadata, dict):
                        logger.info(f"First result metadata keys: {list(metadata.keys())}")
                    # Also log score
                    score = first_result.get('score', 'N/A')
                    logger.info(f"First result score: {score}")
                else:
                    metadata = getattr(first_result, 'metadata', None)
                    logger.info(f"First result metadata (object): {metadata}")
                    score = getattr(first_result, 'score', 'N/A')
                    logger.info(f"First result score: {score}")
            else:
                logger.warning("⚠️  No results returned from Pinecone query!")
                logger.warning("Possible reasons:")
                logger.warning("  1. Index might be empty")
                logger.warning("  2. Embedding dimension mismatch")
                logger.warning("  3. Query doesn't match any vectors")
                logger.warning("  4. Index name might be incorrect")
            
            # Format context from results
            context_parts = []
            for i, match in enumerate(results):
                # Handle both dict and object responses
                if isinstance(match, dict):
                    metadata = match.get('metadata', {})
                else:
                    metadata = getattr(match, 'metadata', {})
                
                logger.info(f"Match {i} metadata: {metadata}")
                logger.info(f"Match {i} metadata type: {type(metadata)}")
                
                # Ensure metadata is a dict for .get() calls
                if not isinstance(metadata, dict):
                    if isinstance(metadata, str):
                        text = metadata
                    else:
                        metadata = {} if metadata is None else {'value': str(metadata)}
                
                # Try common metadata keys for text content
                if isinstance(metadata, dict):
                    text = (
                        metadata.get('text', '') or 
                        metadata.get('content', '') or 
                        metadata.get('chunk', '') or
                        metadata.get('page_content', '') or
                        metadata.get('document', '') or
                        metadata.get('value', '') or
                        str(metadata) if metadata else ''
                    )
                else:
                    text = str(metadata) if metadata else ''
                
                # If still empty, check if metadata itself is a string
                if not text and isinstance(metadata, str):
                    text = metadata
                
                logger.info(f"Match {i} - Extracted text length: {len(text)}")
                if text and text.strip():
                    logger.info(f"Match {i} - Adding text to context (first 100 chars): {text[:100]}...")
                    context_parts.append(text)
                else:
                    logger.warning(f"Match {i} - No text extracted! Metadata was: {metadata}")
            
            formatted_context = "\n\n".join(context_parts)
            logger.info(f"Final formatted context length: {len(formatted_context)} characters")
            if not formatted_context:
                logger.warning("⚠️  Context is empty! No text could be extracted from Pinecone results.")
            return formatted_context, results
            
        except Exception as e:
            logger.error(f"Error retrieving context from Pinecone: {str(e)}")
            # Return empty context on error, don't fail completely
            return "", []
    
    def _get_query_embedding(self, query: str) -> List[float]:
        """
        Get embedding vector for a query string using OpenAI embeddings API.
        
        Args:
            query: The query string to embed
            
        Returns:
            List of float values representing the embedding vector
        """
        try:
            from openai import OpenAI
            from config.settings import settings
            
            client = OpenAI(api_key=settings.openai_api_key)
            
            # Use configurable embedding model
            embedding_model = settings.embedding_model
            logger.info(f"Using embedding model: {embedding_model}")
            
            # For text-embedding-3 models, we can specify dimensions
            # Check if we need to match index dimension
            embedding_params = {"model": embedding_model, "input": query}
            
            if hasattr(self, 'index_dimension') and self.index_dimension:
                # For text-embedding-3-large: supports 256, 1024, 3072
                # For text-embedding-3-small: supports 512, 1024, 1536
                if embedding_model == "text-embedding-3-large" and self.index_dimension in [256, 1024, 3072]:
                    embedding_params["dimensions"] = self.index_dimension
                    logger.info(f"Setting dimensions={self.index_dimension} for text-embedding-3-large")
                elif embedding_model == "text-embedding-3-small" and self.index_dimension in [512, 1024, 1536]:
                    embedding_params["dimensions"] = self.index_dimension
                    logger.info(f"Setting dimensions={self.index_dimension} for text-embedding-3-small")
                else:
                    # Try to use the index dimension anyway - some models may support it
                    embedding_params["dimensions"] = self.index_dimension
                    logger.warning(f"Using dimensions={self.index_dimension} for {embedding_model} (may not be officially supported)")
            
            response = client.embeddings.create(**embedding_params)
            
            embedding = response.data[0].embedding
            embedding_dim = len(embedding)
            logger.info(f"Generated embedding successfully: dimension={embedding_dim}")
            
            # Warn if dimension doesn't match index
            if hasattr(self, 'index_dimension') and self.index_dimension:
                if embedding_dim != self.index_dimension:
                    logger.error(f"⚠️  CRITICAL: Embedding dimension ({embedding_dim}) doesn't match index dimension ({self.index_dimension})!")
                    logger.error(f"   This will cause queries to return no results.")
                    logger.error(f"   Please set EMBEDDING_MODEL in .env to a model that produces {self.index_dimension}-dimensional vectors.")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating query embedding: {str(e)}")
            raise
    
    def test_connection(self) -> dict:
        """
        Test Pinecone connection and return diagnostic information.
        
        Returns:
            Dictionary with connection test results
        """
        results = {
            "connected": False,
            "index_name": self.index_name,
            "error": None,
            "stats": None,
            "sample_query": None
        }
        
        try:
            # Test index stats
            stats = self.index.describe_index_stats()
            results["connected"] = True
            results["stats"] = str(stats)
            logger.info(f"Connection test successful. Stats: {stats}")
            
            # Try a sample query if index has vectors
            try:
                # Get a random vector dimension from stats if available
                if hasattr(stats, 'dimension'):
                    dimension = stats.dimension
                elif isinstance(stats, dict) and 'dimension' in stats:
                    dimension = stats['dimension']
                else:
                    dimension = 1536  # Default for text-embedding-ada-002
                
                # Create a dummy embedding for testing
                test_embedding = [0.0] * dimension
                test_response = self.index.query(
                    vector=test_embedding,
                    top_k=1,
                    include_metadata=True
                )
                
                if isinstance(test_response, dict):
                    matches = test_response.get('matches', [])
                else:
                    matches = getattr(test_response, 'matches', [])
                
                results["sample_query"] = {
                    "matches_count": len(matches),
                    "has_results": len(matches) > 0
                }
                
            except Exception as e:
                results["sample_query"] = {"error": str(e)}
                logger.warning(f"Sample query test failed: {str(e)}")
                
        except Exception as e:
            results["error"] = str(e)
            results["error_type"] = type(e).__name__
            logger.error(f"Connection test failed: {str(e)}")
        
        return results

