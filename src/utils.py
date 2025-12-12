"""Utility functions for the chat engine."""

import logging
import sys
from typing import Optional


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def format_context(results: list) -> str:
    """Format Pinecone query results into a context string."""
    if not results:
        return ""
    
    context_parts = []
    for result in results:
        if hasattr(result, 'metadata') and result.metadata:
            # Extract text from metadata if available
            text = result.metadata.get('text', '') or result.metadata.get('content', '')
            if text:
                context_parts.append(text)
        elif hasattr(result, 'text'):
            context_parts.append(result.text)
    
    return "\n\n".join(context_parts)


