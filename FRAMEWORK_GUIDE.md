# Framework Guide: Building a Self-Correcting Chatbot in Python

## Overview

This guide provides a comprehensive framework for building a self-correcting chatbot in Python that:
- Retrieves context from a vector database (RAG)
- Generates answers using LLMs
- Evaluates answer quality using an evaluation API
- Automatically regenerates answers when quality thresholds are not met

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [Technology Stack](#technology-stack)
4. [Step-by-Step Implementation](#step-by-step-implementation)
5. [Configuration Management](#configuration-management)
6. [Self-Correction Logic](#self-correction-logic)
7. [Testing](#testing)
8. [Deployment](#deployment)
9. [Best Practices](#best-practices)

## Architecture Overview

### High-Level Flow

```
User Question
    ↓
1. Context Retrieval (RAG)
    - Generate query embedding
    - Search vector database
    - Retrieve relevant context
    ↓
2. Answer Generation (LLM)
    - Build prompt with context
    - Generate initial answer
    ↓
3. Answer Evaluation
    - Send to evaluation API
    - Receive quality scores
    ↓
4. Self-Correction Check
    - Check if scores exceed threshold
    - If yes: Regenerate with correction prompt
    - If no: Use original answer
    ↓
Return Final Answer to User
```

### Key Principles

1. **Separation of Concerns**: Each component handles a specific responsibility
2. **Error Resilience**: System continues operating even if evaluation fails
3. **Configurable Thresholds**: Quality thresholds are configurable
4. **Lazy Evaluation**: Only regenerate when necessary
5. **Non-Blocking**: Evaluation failures don't block user experience

## Core Components

### 1. RAG (Retrieval-Augmented Generation) Module

**Purpose**: Retrieve relevant context from a vector database

**Responsibilities**:
- Generate query embeddings
- Query vector database
- Extract and format context from results
- Handle dimension mismatches
- Auto-detect namespaces

**Key Features**:
- Configurable embedding models
- Dimension matching for compatibility
- Metadata extraction from multiple formats
- Error handling with graceful degradation

### 2. LLM Client Module

**Purpose**: Generate answers using Large Language Models

**Responsibilities**:
- Build prompts with context
- Call LLM API
- Extract generated answers
- Handle regeneration with correction prompts

**Key Features**:
- Configurable models
- Context injection
- Specialized regeneration prompts
- Error handling

### 3. Evaluation Client Module

**Purpose**: Evaluate answer quality

**Responsibilities**:
- Prepare evaluation payload
- Send to evaluation API
- Parse evaluation results
- Extract criteria scores

**Key Features**:
- Non-blocking operation
- Multiple criteria support
- Error resilience
- Structured response parsing

### 4. Chat Engine (Orchestrator)

**Purpose**: Coordinate all components and implement self-correction logic

**Responsibilities**:
- Orchestrate RAG → LLM → Evaluation flow
- Check evaluation scores against thresholds
- Trigger regeneration when needed
- Manage conversation state

**Key Features**:
- Threshold-based regeneration
- Single evaluation per question
- Clean separation of concerns

### 5. Configuration Module

**Purpose**: Centralized configuration management

**Responsibilities**:
- Load environment variables
- Validate configuration
- Provide typed access to settings
- Support defaults and optional values

**Key Features**:
- Type validation
- Environment variable support
- Lazy initialization
- Backward compatibility

## Technology Stack

### Required Libraries

```python
# Core Dependencies
openai>=1.0.0              # LLM API client
pinecone>=7.0.0           # Vector database client
requests>=2.31.0          # HTTP client for evaluation API
pydantic>=2.0.0           # Data validation
pydantic-settings>=2.0.0  # Settings management
python-dotenv>=1.0.0      # Environment variable loading

# Optional (for Web UI)
streamlit>=1.28.0         # Web interface framework
```

### External Services

1. **OpenAI API**: For LLM completions and embeddings
2. **Pinecone**: Vector database for RAG
3. **RagMetrics API**: For answer evaluation (or custom evaluation service)

## Step-by-Step Implementation

### Step 1: Project Structure

Create the following directory structure:

```
your_chatbot/
├── src/
│   ├── __init__.py
│   ├── rag_client.py          # RAG/vector database client
│   ├── llm_client.py           # LLM API client
│   ├── evaluation_client.py    # Evaluation API client
│   ├── chat_engine.py          # Main orchestrator
│   ├── prompt.py               # Prompt templates
│   └── utils.py                # Utility functions
├── config/
│   ├── __init__.py
│   └── settings.py             # Configuration management
├── main.py                     # CLI entry point
├── web_ui.py                  # Web UI (optional)
├── requirements.txt
├── .env                        # Environment variables
└── README.md
```

### Step 2: Configuration Setup

Create `config/settings.py`:

```python
"""Configuration settings loaded from environment variables."""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # LLM Configuration
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-3.5-turbo", alias="OPEN_AI_MODEL")
    
    # Vector Database Configuration
    pinecone_api_key: str = Field(..., alias="PINECONE_API_KEY")
    pinecone_index_name: str = Field(..., alias="PINECONE_INDEX")
    pinecone_namespace: Optional[str] = Field(default=None, alias="PINECONE_NAMESPACE")
    
    # Evaluation API Configuration
    evaluation_api_key: str = Field(..., alias="EVALUATION_API_KEY")
    evaluation_base_url: str = Field(default="https://api.example.com", alias="EVALUATION_URL")
    evaluation_group_id: str = Field(..., alias="EVALUATION_GROUP_ID")
    evaluation_conversation_id: str = Field(..., alias="EVALUATION_CONVERSATION_ID")
    
    # RAG Configuration
    rag_top_k: int = Field(default=5, alias="RAG_TOP_K")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    
    # Self-Correction Configuration
    reg_score: int = Field(default=3, alias="REG_SCORE")
    
    # UI Configuration
    topic: str = Field(default="your chatbot topic", alias="TOPIC")
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_file_required=False,
        extra="ignore"
    )


# Lazy initialization for settings
_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
```

### Step 3: RAG Client Implementation

Create `src/rag_client.py`:

```python
"""RAG client for vector database integration."""

import logging
from typing import Tuple, List
from openai import OpenAI
from pinecone import Pinecone
from config.settings import get_settings

logger = logging.getLogger(__name__)


class RAGClient:
    """Client for retrieving context from vector database."""
    
    def __init__(self):
        """Initialize RAG client."""
        self.settings = get_settings()
        self.pc = Pinecone(api_key=self.settings.pinecone_api_key)
        self.index = self.pc.Index(self.settings.pinecone_index_name)
        self.openai_client = OpenAI(api_key=self.settings.openai_api_key)
        
        # Auto-detect namespace if not set
        if not self.settings.pinecone_namespace:
            stats = self.index.describe_index_stats()
            if stats.namespaces():
                self.namespace = list(stats.namespaces().keys())[0]
            else:
                self.namespace = ""
        else:
            self.namespace = self.settings.pinecone_namespace
    
    def retrieve_context(self, query: str) -> Tuple[str, List]:
        """
        Retrieve relevant context for a query.
        
        Args:
            query: User's question
            
        Returns:
            Tuple of (formatted_context_string, raw_results_list)
        """
        try:
            # Generate embedding
            embedding = self._get_query_embedding(query)
            
            # Query vector database
            query_response = self.index.query(
                vector=embedding,
                top_k=self.settings.rag_top_k,
                namespace=self.namespace,
                include_metadata=True
            )
            
            # Extract context from results
            context_parts = []
            raw_results = []
            
            for match in query_response.matches:
                raw_results.append(match)
                text = self._extract_text_from_match(match)
                if text:
                    context_parts.append(text)
            
            context = "\n\n".join(context_parts)
            return context, raw_results
            
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            return "", []
    
    def _get_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for query."""
        # Get index dimension
        stats = self.index.describe_index_stats()
        index_dimension = stats.dimension
        
        # Generate embedding with dimension matching
        embedding_params = {
            "model": self.settings.embedding_model,
            "input": query
        }
        
        # Set dimensions for text-embedding-3 models
        if "text-embedding-3" in self.settings.embedding_model:
            embedding_params["dimensions"] = index_dimension
        
        response = self.openai_client.embeddings.create(**embedding_params)
        return response.data[0].embedding
    
    def _extract_text_from_match(self, match) -> str:
        """Extract text from match metadata."""
        if not hasattr(match, 'metadata'):
            return ""
        
        metadata = match.metadata if hasattr(match, 'metadata') else {}
        
        # Try multiple possible keys
        for key in ['text', 'content', 'chunk', 'page_content', 'document', 'value']:
            if key in metadata:
                return str(metadata[key])
        
        return ""
```

### Step 4: LLM Client Implementation

Create `src/llm_client.py`:

```python
"""LLM client for answer generation."""

import logging
from typing import Optional
from openai import OpenAI
from config.settings import get_settings
from src.prompt import get_chat_prompt, get_regenerate_prompt

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for LLM API interactions."""
    
    def __init__(self):
        """Initialize LLM client."""
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key)
    
    def generate_answer(self, question: str, context: str) -> str:
        """
        Generate answer using LLM.
        
        Args:
            question: User's question
            context: Retrieved context from RAG
            
        Returns:
            Generated answer string
        """
        system_prompt, user_prompt = get_chat_prompt(question, context)
        
        try:
            response = self.client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.9,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content.strip()
            return answer
            
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            raise
    
    def regenerate_answer(self, question: str, previous_answer: str, context: Optional[str] = None) -> str:
        """
        Regenerate answer with correction prompt.
        
        Args:
            question: User's question
            previous_answer: Previous (erroneous) answer
            context: Retrieved context from RAG
            
        Returns:
            Regenerated answer string
        """
        system_prompt, user_prompt = get_regenerate_prompt(question, previous_answer, context or "")
        
        try:
            response = self.client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content.strip()
            return answer
            
        except Exception as e:
            logger.error(f"Error regenerating answer: {str(e)}")
            raise
```

### Step 5: Prompt Templates

Create `src/prompt.py`:

```python
"""Prompt templates for the chatbot."""

def get_chat_prompt(question: str, context: str) -> tuple[str, str]:
    """
    Get chat prompt with context.
    
    Args:
        question: User's question
        context: Retrieved context
        
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    system_prompt = """You are a helpful assistant that answers questions based on the provided context.
    
Rules:
- Only use information from the provided context
- If the context doesn't contain enough information, say so
- Be concise and accurate
- Do not make up information"""
    
    user_prompt = f"""Context:
{context}

Question: {question}

Answer:"""
    
    return system_prompt, user_prompt


def get_regenerate_prompt(question: str, previous_answer: str, context: str = "") -> tuple[str, str]:
    """
    Get regeneration prompt for correcting erroneous answers.
    
    Args:
        question: User's question
        previous_answer: Previous (erroneous) answer
        context: Retrieved context
        
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    system_prompt = """You are a helpful assistant that must provide accurate answers based strictly on the provided context.

CRITICAL INSTRUCTIONS:
- The previous answer contained errors or hallucinations
- You MUST provide a corrected answer that strictly adheres to the context
- Do NOT include any information not present in the context
- If the context doesn't contain enough information, clearly state that
- Be precise and factual"""
    
    user_prompt = f"""Context:
{context}

Question: {question}

Previous Answer (contains errors):
{previous_answer}

Provide a corrected answer that strictly adheres to the context:"""
    
    return system_prompt, user_prompt
```

### Step 6: Evaluation Client Implementation

Create `src/evaluation_client.py`:

```python
"""Evaluation client for answer quality assessment."""

import logging
import requests
from typing import Optional, Dict
from config.settings import get_settings

logger = logging.getLogger(__name__)


class EvaluationClient:
    """Client for evaluation API interactions."""
    
    def __init__(self):
        """Initialize evaluation client."""
        self.settings = get_settings()
        self.base_url = self.settings.evaluation_base_url.rstrip('/')
        self.headers = {
            "Authorization": f"Token {self.settings.evaluation_api_key}",
            "Content-Type": "application/json"
        }
    
    def evaluate_answer(self, question: str, answer: str, context: str) -> Optional[Dict]:
        """
        Evaluate answer quality.
        
        Args:
            question: User's question
            answer: Generated answer
            context: Retrieved context
            
        Returns:
            Evaluation result dictionary or None if failed
        """
        payload = {
            "question": question,
            "answer": answer,
            "context": context,
            "ground_truth": "",  # Empty as per requirements
            "eval_group_id": self.settings.evaluation_group_id,
            "conversation_id": self.settings.evaluation_conversation_id,
            "type": "S"  # Submission type
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/v2/single-evaluation/",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 202:
                result = response.json()
                return self._parse_evaluation_result(result)
            else:
                logger.error(f"Evaluation API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error evaluating answer: {str(e)}")
            return None
    
    def _parse_evaluation_result(self, response: Dict) -> Dict:
        """Parse evaluation API response."""
        # Extract criteria scores
        criteria_list = []
        
        if 'results' in response:
            criteria_list = response['results']
        elif 'criteria' in response:
            criteria_list = response['criteria']
        
        return {
            'raw_response': response,
            'criteria': criteria_list,
            'status': response.get('status', 'unknown')
        }
```

### Step 7: Chat Engine (Orchestrator)

Create `src/chat_engine.py`:

```python
"""Main chat engine orchestrator."""

import logging
from typing import Optional
from src.rag_client import RAGClient
from src.llm_client import LLMClient
from src.evaluation_client import EvaluationClient
from config.settings import get_settings

logger = logging.getLogger(__name__)


class ChatEngine:
    """Main chat engine that orchestrates RAG, LLM, and evaluation."""
    
    def __init__(self):
        """Initialize the chat engine."""
        self.settings = get_settings()
        self.rag_client = RAGClient()
        self.llm_client = LLMClient()
        self.evaluation_client = EvaluationClient()
    
    def process_question(self, question: str) -> dict:
        """
        Process a question through the full pipeline.
        
        Args:
            question: User's question
            
        Returns:
            Dictionary containing question, answer, context, and evaluation result
        """
        # Step 1: Retrieve context
        context, raw_results = self.rag_client.retrieve_context(question)
        
        # Step 2: Generate answer
        answer = self.llm_client.generate_answer(question, context)
        
        # Step 3: Evaluate answer
        evaluation_result = self.evaluation_client.evaluate_answer(
            question=question,
            answer=answer,
            context=context
        )
        
        return {
            "question": question,
            "answer": answer,
            "context": context,
            "evaluation_result": evaluation_result
        }
    
    def regenerate_answer_if_needed(self, question: str, answer: str, 
                                    context: str, evaluation_result: Optional[dict]) -> Optional[str]:
        """
        Check if regeneration is needed and regenerate if so.
        
        Args:
            question: User's question
            answer: Current answer
            context: Retrieved context
            evaluation_result: Evaluation result
            
        Returns:
            Regenerated answer if needed, None otherwise
        """
        if not evaluation_result:
            return None
        
        # Check if any criteria score >= threshold
        should_regenerate, _ = self._should_regenerate(evaluation_result)
        
        if should_regenerate:
            logger.info(f"Regenerating answer due to low quality scores")
            try:
                regenerated = self.llm_client.regenerate_answer(
                    question=question,
                    previous_answer=answer,
                    context=context
                )
                return regenerated
            except Exception as e:
                logger.error(f"Error regenerating answer: {str(e)}")
                return None
        
        return None
    
    def _should_regenerate(self, evaluation_result: dict) -> tuple[bool, list]:
        """
        Check if regeneration is needed based on evaluation scores.
        
        Args:
            evaluation_result: Evaluation result dictionary
            
        Returns:
            Tuple of (should_regenerate: bool, triggering_criteria: list)
        """
        criteria_list = evaluation_result.get('criteria', [])
        triggering_criteria = []
        
        for criterion in criteria_list:
            if isinstance(criterion, dict):
                score = criterion.get('score')
                criterion_name = criterion.get('criteria', criterion.get('name', 'Unknown'))
                
                # Convert score to int
                score_int = None
                if isinstance(score, (int, float)):
                    score_int = int(score)
                elif isinstance(score, str):
                    try:
                        score_int = int(float(score))
                    except (ValueError, TypeError):
                        continue
                
                if score_int is not None and score_int >= self.settings.reg_score:
                    triggering_criteria.append({
                        'name': criterion_name,
                        'score': score_int
                    })
        
        return len(triggering_criteria) > 0, triggering_criteria
```

### Step 8: CLI Entry Point

Create `main.py`:

```python
"""CLI entry point for the chatbot."""

import sys
import logging
from src.utils import setup_logging
from src.chat_engine import ChatEngine

setup_logging(level=logging.WARNING)
logger = logging.getLogger(__name__)


def main():
    """Main CLI entry point."""
    print("=" * 60)
    print("Self-Correcting Chatbot")
    print("=" * 60)
    print("Type 'quit' or 'exit' to end the session")
    print("=" * 60)
    print()
    
    try:
        engine = ChatEngine()
        print("Chatbot ready!\n")
        
        while True:
            try:
                question = input("\nYou: ").strip()
                
                if question.lower() in ['quit', 'exit', 'q']:
                    print("\nGoodbye!")
                    break
                
                if not question:
                    continue
                
                # Process question
                print("\nProcessing...", end='', flush=True)
                result = engine.process_question(question)
                
                # Show answer
                print("\r" + " " * 60 + "\r" + "-" * 60)
                print("Bot:", result['answer'])
                print("-" * 60)
                
                # Show evaluation results
                eval_result = result.get('evaluation_result')
                if eval_result:
                    criteria_list = eval_result.get('criteria', [])
                    if criteria_list:
                        print("\nEvaluation:")
                        print("-" * 60)
                        for criterion in criteria_list:
                            if isinstance(criterion, dict):
                                name = criterion.get('criteria', criterion.get('name', 'Unknown'))
                                score = criterion.get('score', 'N/A')
                                reason = criterion.get('reason', 'N/A')
                                print(f"{name} - {score}: {reason}")
                
                # Check for regeneration
                regenerated = engine.regenerate_answer_if_needed(
                    question=result['question'],
                    answer=result['answer'],
                    context=result['context'],
                    evaluation_result=eval_result
                )
                
                if regenerated:
                    print("\nERRONEOUS ANSWER")
                    print("-" * 60)
                    print("Regenerated Answer:", regenerated)
                    print("-" * 60)
                
            except KeyboardInterrupt:
                print("\n\nInterrupted by user. Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error processing question: {str(e)}")
                print(f"\n[ERROR] Error: {str(e)}")
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        print(f"\n[ERROR] Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Step 9: Utility Functions

Create `src/utils.py`:

```python
"""Utility functions."""

import logging
import sys


def setup_logging(level=logging.INFO):
    """Configure logging for the application."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
```

## Configuration Management

### Environment Variables

Create a `.env` file:

```bash
# LLM Configuration
OPENAI_API_KEY=your_openai_api_key
OPEN_AI_MODEL=gpt-3.5-turbo

# Vector Database Configuration
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX=your_index_name
PINECONE_NAMESPACE=your_namespace  # Optional

# Evaluation API Configuration
EVALUATION_API_KEY=your_evaluation_api_key
EVALUATION_URL=https://api.example.com
EVALUATION_GROUP_ID=your_group_id
EVALUATION_CONVERSATION_ID=your_conversation_id

# RAG Configuration
RAG_TOP_K=5
EMBEDDING_MODEL=text-embedding-3-small

# Self-Correction Configuration
REG_SCORE=3

# UI Configuration
TOPIC=your chatbot topic
```

## Self-Correction Logic

### Threshold-Based Regeneration

The self-correction system works as follows:

1. **Initial Answer Generation**: Generate answer using RAG context
2. **Evaluation**: Send answer to evaluation API
3. **Score Check**: Check if any criteria score >= `REG_SCORE`
4. **Regeneration**: If threshold exceeded, regenerate with correction prompt
5. **Display**: Show regenerated answer (original answer shown if error occurred)

### Key Design Decisions

- **Single Evaluation**: Only evaluate the first answer, not regenerated ones
- **Any Criteria**: Regeneration triggered if ANY criteria exceeds threshold
- **Non-Blocking**: Evaluation failures don't prevent answer display
- **Configurable**: Threshold is configurable via environment variable

## Testing

### Unit Tests

Test individual components:

```python
# test_rag_client.py
def test_rag_client_retrieval():
    client = RAGClient()
    context, results = client.retrieve_context("test question")
    assert isinstance(context, str)
    assert isinstance(results, list)

# test_llm_client.py
def test_llm_client_generation():
    client = LLMClient()
    answer = client.generate_answer("test", "test context")
    assert isinstance(answer, str)
    assert len(answer) > 0

# test_chat_engine.py
def test_chat_engine_flow():
    engine = ChatEngine()
    result = engine.process_question("test question")
    assert 'answer' in result
    assert 'evaluation_result' in result
```

### Integration Tests

Test full pipeline:

```python
def test_full_pipeline():
    engine = ChatEngine()
    result = engine.process_question("What is the main topic?")
    
    assert result['answer']
    assert result['context']
    
    # Check regeneration logic
    regenerated = engine.regenerate_answer_if_needed(
        question=result['question'],
        answer=result['answer'],
        context=result['context'],
        evaluation_result=result['evaluation_result']
    )
    
    # Regenerated should be None or a string
    assert regenerated is None or isinstance(regenerated, str)
```

## Deployment

### Local Development

1. Install dependencies: `pip install -r requirements.txt`
2. Create `.env` file with your credentials
3. Run CLI: `python main.py`
4. Run Web UI: `streamlit run web_ui.py`

### Production Deployment

1. Set environment variables in your deployment platform
2. Ensure all API keys are securely stored
3. Configure logging levels appropriately
4. Set up monitoring for API failures
5. Consider rate limiting for API calls

## Best Practices

### 1. Error Handling

- Always handle API failures gracefully
- Log errors with sufficient context
- Don't block user experience on evaluation failures
- Provide fallback behavior

### 2. Configuration

- Use environment variables for all secrets
- Provide sensible defaults
- Validate configuration at startup
- Support both local and cloud deployments

### 3. Logging

- Use appropriate log levels
- Include context in log messages
- Don't log sensitive information
- Use structured logging for production

### 4. Performance

- Cache embeddings when possible
- Batch API calls when appropriate
- Use async/await for concurrent operations
- Monitor API response times

### 5. Security

- Never commit API keys
- Use secure storage for secrets
- Validate all inputs
- Sanitize outputs

### 6. Testing

- Write unit tests for each component
- Test error scenarios
- Test threshold logic
- Test with various evaluation scores

## Customization Points

### 1. Evaluation Criteria

Modify `_should_regenerate()` to check specific criteria:

```python
def _should_regenerate(self, evaluation_result: dict) -> tuple[bool, list]:
    # Only regenerate on hallucination score
    for criterion in evaluation_result.get('criteria', []):
        if criterion.get('criteria') == 'Hallucination':
            score = criterion.get('score')
            if score >= self.settings.reg_score:
                return True, [criterion]
    return False, []
```

### 2. Multiple Regeneration Attempts

Modify to allow multiple regeneration attempts:

```python
def regenerate_with_retries(self, question: str, answer: str, 
                          context: str, max_attempts: int = 3):
    for attempt in range(max_attempts):
        regenerated = self.llm_client.regenerate_answer(...)
        eval_result = self.evaluation_client.evaluate_answer(...)
        if not self._should_regenerate(eval_result)[0]:
            return regenerated
    return regenerated  # Return last attempt
```

### 3. Custom Evaluation Logic

Implement custom evaluation instead of API:

```python
def custom_evaluate(self, question: str, answer: str, context: str):
    # Your custom evaluation logic
    score = calculate_custom_score(question, answer, context)
    return {'score': score, 'criteria': 'Custom'}
```

## Conclusion

This framework provides a complete foundation for building a self-correcting chatbot. Key features:

- Modular architecture
- Configurable thresholds
- Error resilience
- Easy to extend
- Production-ready structure

Customize the components to fit your specific requirements and evaluation criteria.

