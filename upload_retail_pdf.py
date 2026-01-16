"""Upload Retail Policy PDF to Pinecone retail-index."""

import sys
import logging
import os
from typing import List
from pinecone import Pinecone
from openai import OpenAI
from config.settings import settings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import PyPDF2, fallback to pypdf
try:
    from PyPDF2 import PdfReader
except ImportError:
    try:
        from pypdf import PdfReader
    except ImportError:
        logger.error("Please install PyPDF2 or pypdf: pip install PyPDF2")
        sys.exit(1)


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text as a string
    """
    try:
        logger.info(f"Extracting text from PDF: {pdf_path}")
        reader = PdfReader(pdf_path)
        text_parts = []
        
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text.strip():
                text_parts.append(text)
                logger.debug(f"Extracted {len(text)} characters from page {i+1}")
        
        full_text = "\n\n".join(text_parts)
        logger.info(f"Extracted {len(full_text)} total characters from {len(reader.pages)} pages")
        return full_text
        
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        raise


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into chunks with overlap.
    
    Args:
        text: The text to chunk
        chunk_size: Maximum size of each chunk in characters
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    if not text:
        return []
    
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        # Calculate end position
        end = min(start + chunk_size, text_length)
        
        # Extract chunk
        chunk = text[start:end]
        
        # Try to break at sentence boundary if not at end
        if end < text_length:
            # Look for sentence endings in the last 100 characters
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)
            
            if break_point > start + chunk_size * 0.7:  # Only break if we're not too early
                chunk = chunk[:break_point + 1]
                end = start + len(chunk)
        
        chunks.append(chunk.strip())
        logger.debug(f"Created chunk {len(chunks)}: {len(chunk)} characters")
        
        # Move start position with overlap
        start = end - overlap if end < text_length else end
    
    logger.info(f"Created {len(chunks)} chunks from text")
    return chunks


def create_embeddings(texts: List[str], model: str = None, index_dimension: int = None) -> List[List[float]]:
    """
    Create embeddings for a list of texts using OpenAI.
    
    Args:
        texts: List of text strings to embed
        model: Embedding model to use (defaults to settings.embedding_model)
        index_dimension: Target dimension to match the index (if None, uses model default)
        
    Returns:
        List of embedding vectors
    """
    if not texts:
        return []
    
    model = model or settings.embedding_model
    logger.info(f"Creating embeddings for {len(texts)} chunks using model: {model}")
    if index_dimension:
        logger.info(f"Target dimension: {index_dimension}")
    
    client = OpenAI(api_key=settings.openai_api_key)
    embeddings = []
    
    # Prepare embedding parameters
    embedding_params = {"model": model}
    if index_dimension:
        # For text-embedding-3 models, we can specify dimensions
        # text-embedding-3-large: supports 256, 1024, 3072
        # text-embedding-3-small: supports 512, 1024, 1536
        if "text-embedding-3" in model:
            if model == "text-embedding-3-large" and index_dimension in [256, 1024, 3072]:
                embedding_params["dimensions"] = index_dimension
                logger.info(f"Setting dimensions={index_dimension} for text-embedding-3-large")
            elif model == "text-embedding-3-small" and index_dimension in [512, 1024, 1536]:
                embedding_params["dimensions"] = index_dimension
                logger.info(f"Setting dimensions={index_dimension} for text-embedding-3-small")
            else:
                # Try to use the index dimension anyway
                embedding_params["dimensions"] = index_dimension
                logger.warning(f"Using dimensions={index_dimension} for {model} (may not be officially supported)")
        else:
            logger.warning(f"Model {model} may not support custom dimensions, but index requires {index_dimension}")
    
    # Process in batches to avoid rate limits
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")
        
        try:
            # Add input to params for this batch
            batch_params = {**embedding_params, "input": batch}
            response = client.embeddings.create(**batch_params)
            
            batch_embeddings = [item.embedding for item in response.data]
            embeddings.extend(batch_embeddings)
            
            # Verify dimension if specified
            if batch_embeddings and index_dimension:
                actual_dim = len(batch_embeddings[0])
                if actual_dim != index_dimension:
                    logger.error(f"⚠️  CRITICAL: Embedding dimension ({actual_dim}) doesn't match target ({index_dimension})!")
                else:
                    logger.info(f"Created {len(batch_embeddings)} embeddings with dimension {actual_dim}")
            else:
                logger.info(f"Created {len(batch_embeddings)} embeddings")
            
        except Exception as e:
            logger.error(f"Error creating embeddings for batch: {str(e)}")
            raise
    
    logger.info(f"Successfully created {len(embeddings)} embeddings")
    return embeddings


def get_index_dimension(index_name: str) -> int:
    """
    Get the dimension of a Pinecone index.
    
    Args:
        index_name: Name of the Pinecone index
        
    Returns:
        Index dimension as integer
    """
    logger.info(f"Getting dimension for index: {index_name}")
    pc = Pinecone(api_key=settings.pinecone_api_key)
    index = pc.Index(index_name)
    
    try:
        stats = index.describe_index_stats()
        if hasattr(stats, 'dimension'):
            dimension = stats.dimension
        elif isinstance(stats, dict) and 'dimension' in stats:
            dimension = stats['dimension']
        else:
            # Try to get from namespaces
            if hasattr(stats, 'namespaces'):
                namespaces = stats.namespaces if hasattr(stats, 'namespaces') else {}
                if namespaces:
                    first_ns = list(namespaces.values())[0]
                    if hasattr(first_ns, 'dimension'):
                        dimension = first_ns.dimension
                    elif isinstance(first_ns, dict) and 'dimension' in first_ns:
                        dimension = first_ns['dimension']
                    else:
                        raise ValueError("Could not determine index dimension from stats")
                else:
                    raise ValueError("No namespaces found in index stats")
            else:
                raise ValueError("Could not determine index dimension from stats")
        
        logger.info(f"Index dimension: {dimension}")
        return dimension
        
    except Exception as e:
        logger.error(f"Error getting index dimension: {str(e)}")
        raise


def upload_to_pinecone(
    chunks: List[str],
    embeddings: List[List[float]],
    index_name: str,
    namespace: str = None
) -> None:
    """
    Upload chunks and embeddings to Pinecone index.
    
    Args:
        chunks: List of text chunks
        embeddings: List of embedding vectors
        index_name: Name of the Pinecone index
        namespace: Namespace to upload to (uses settings namespace if None)
    """
    if len(chunks) != len(embeddings):
        raise ValueError(f"Mismatch: {len(chunks)} chunks but {len(embeddings)} embeddings")
    
    logger.info(f"Connecting to Pinecone index: {index_name}")
    pc = Pinecone(api_key=settings.pinecone_api_key)
    index = pc.Index(index_name)
    
    # Verify embedding dimension matches index
    if embeddings:
        actual_dim = len(embeddings[0])
        index_dimension = get_index_dimension(index_name)
        if actual_dim != index_dimension:
            raise ValueError(
                f"Embedding dimension ({actual_dim}) doesn't match index dimension ({index_dimension}). "
                f"Please recreate embeddings with dimension {index_dimension}."
            )
    
    # Use namespace from settings if not provided
    if namespace is None:
        namespace = settings.pinecone_namespace or ""
    
    logger.info(f"Uploading {len(chunks)} vectors to namespace: '{namespace}'")
    
    # Prepare vectors for upload
    vectors = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        vector = {
            'id': f'retail-policy-{i}',
            'values': embedding,
            'metadata': {
                'text': chunk,
                'source': 'RetailPolicy.pdf',
                'chunk_index': i
            }
        }
        vectors.append(vector)
    
    # Upload in batches (Pinecone recommends batches of 100)
    batch_size = 100
    total_uploaded = 0
    
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        logger.info(f"Uploading batch {i//batch_size + 1}/{(len(vectors) + batch_size - 1)//batch_size} ({len(batch)} vectors)")
        
        try:
            if namespace:
                index.upsert(vectors=batch, namespace=namespace)
            else:
                index.upsert(vectors=batch)
            
            total_uploaded += len(batch)
            logger.info(f"Successfully uploaded {total_uploaded}/{len(vectors)} vectors")
            
        except Exception as e:
            logger.error(f"Error uploading batch: {str(e)}")
            raise
    
    logger.info(f"✓ Successfully uploaded all {len(vectors)} vectors to index '{index_name}' in namespace '{namespace}'")


def main():
    """Main function to upload PDF to Pinecone."""
    pdf_path = "Docs/RetailPolicy.pdf"
    
    # Check if PDF exists
    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found: {pdf_path}")
        sys.exit(1)
    
    try:
        # Step 1: Extract text from PDF
        logger.info("=" * 60)
        logger.info("Step 1: Extracting text from PDF")
        logger.info("=" * 60)
        text = extract_text_from_pdf(pdf_path)
        
        if not text or not text.strip():
            logger.error("No text extracted from PDF")
            sys.exit(1)
        
        # Step 2: Get index dimension
        logger.info("=" * 60)
        logger.info("Step 2: Getting index dimension")
        logger.info("=" * 60)
        index_dimension = get_index_dimension(settings.pinecone_retail_index)
        
        # Step 3: Chunk text
        logger.info("=" * 60)
        logger.info("Step 3: Chunking text")
        logger.info("=" * 60)
        chunks = chunk_text(text, chunk_size=1000, overlap=200)
        
        if not chunks:
            logger.error("No chunks created from text")
            sys.exit(1)
        
        # Step 4: Create embeddings with matching dimension
        logger.info("=" * 60)
        logger.info("Step 4: Creating embeddings")
        logger.info("=" * 60)
        embeddings = create_embeddings(chunks, index_dimension=index_dimension)
        
        if len(embeddings) != len(chunks):
            logger.error(f"Mismatch: {len(chunks)} chunks but {len(embeddings)} embeddings")
            sys.exit(1)
        
        # Step 5: Upload to Pinecone
        logger.info("=" * 60)
        logger.info("Step 5: Uploading to Pinecone")
        logger.info("=" * 60)
        upload_to_pinecone(
            chunks=chunks,
            embeddings=embeddings,
            index_name=settings.pinecone_retail_index,
            namespace=settings.pinecone_namespace  # Use same namespace as constitution
        )
        
        logger.info("=" * 60)
        logger.info("✓ Upload completed successfully!")
        logger.info("=" * 60)
        logger.info(f"Uploaded {len(chunks)} chunks to index '{settings.pinecone_retail_index}'")
        logger.info(f"Namespace: '{settings.pinecone_namespace or 'default'}'")
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()

