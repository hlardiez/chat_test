# Chat Test Project - Architecture Document

## Project Overview

A chat engine built on OpenAI that:
1. Answers questions using data retrieved from a Pinecone RAG system
2. Collects the question, answer, and RAG context
3. Sends evaluation data to RagMetrics API

## Status: ✅ Implemented

This architecture document reflects the implemented system.

## Architecture Components

### 1. Core Modules

```
chat_test/
├── src/
│   ├── __init__.py
│   ├── chat_engine.py          # Main chat orchestrator
│   ├── openai_client.py        # OpenAI API integration
│   ├── pinecone_rag.py         # Pinecone vector database integration
│   ├── ragmetrics_client.py    # RagMetrics API integration
│   └── utils.py                # Helper functions
├── config/
│   └── settings.py             # Configuration management
├── .env                        # Environment variables (from .env.txt)
├── .env.txt                    # Template/documentation of env vars
├── requirements.txt            # Python dependencies
├── main.py                     # Entry point
└── README.md                   # Project documentation
```

### 2. Data Flow

```
User Question (CLI Input)
    ↓
Chat Engine (orchestrates)
    ↓
┌─────────────────────────────────────┐
│  1. Pinecone RAG System            │
│     - Generate query embedding     │
│       (OpenAI text-embedding-ada-002)│
│     - Query Pinecone vector DB     │
│     - Retrieve top 3 results       │
│     - Format context string        │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  2. OpenAI Chat Completion         │
│     - Build prompt with context    │
│     - Call OpenAI API              │
│     - Extract generated answer     │
│     - Return to user               │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  3. RagMetrics Evaluation          │
│     - Collect: question, answer,   │
│       context, ground_truth (""),  │
│       eval_group_id (constant),    │
│       type ("S")                   │
│     - Send POST to RagMetrics API  │
│     - Log success/failure          │
│     - Continue even on failure     │
└─────────────────────────────────────┘
    ↓
Return result to user (CLI)
```

### 3. Module Responsibilities

#### `chat_engine.py`
- Main orchestrator class
- Coordinates between OpenAI, Pinecone, and RagMetrics
- Manages conversation flow
- Handles error cases

#### `openai_client.py`
- Wraps OpenAI API calls using OpenAI Python SDK
- Handles chat completion with context injection
- Builds system and user prompts with RAG context
- Configurable model via environment variable (default: `gpt-3.5-turbo`)
- Manages API key and configuration from settings

#### `pinecone_rag.py`
- Connects to Pinecone vector database using API key
- Generates query embeddings using OpenAI `text-embedding-ada-002` model
- Performs vector similarity search (top-k=3)
- Retrieves relevant context/documentation from metadata
- Formats results into context string
- Handles errors gracefully (returns empty context on failure)

#### `ragmetrics_client.py`
- Prepares evaluation payload with required fields
- Sends POST request to RagMetrics API using `requests` library
- Handles API authentication (Token-based: `Token {API_KEY}`)
- Manages response/error handling (logs errors, returns success status)
- Non-blocking: failures are logged but don't stop the chat flow

#### `settings.py`
- Loads environment variables from `.env` file using `pydantic-settings`
- Validates required configuration with type checking
- Provides typed configuration objects via `Settings` class
- Supports default values for optional settings
- Centralized configuration management

#### `utils.py`
- Logging configuration (`setup_logging()`)
- Context formatting utilities
- Helper functions for data processing

#### `main.py`
- CLI entry point for the application
- Interactive chat loop with user input
- Error handling and graceful shutdown
- User-friendly output formatting
- Exit commands: `quit`, `exit`, `q`

### 4. Configuration Requirements

Environment variables required (in `.env`):
```bash
# OpenAI Configuration
OPENAI_API_KEY=<your_openai_key>              # Required
OPENAI_MODEL=gpt-3.5-turbo                    # Optional, default: gpt-3.5-turbo

# Pinecone Configuration
PINECONE_API_KEY=<your_pinecone_key>          # Required
PINECONE_INDEX_NAME=<index_name>              # Required
# PINECONE_ENVIRONMENT=<environment>          # Optional (for older Pinecone versions)

# RagMetrics Configuration
RAGMETRICS_API_KEY=<ragmetrics_api_key>       # Required
RAGMETRICS_BASE_URL=https://ragmetrics-staging-docker-c9ana3hgacg3fbbt.centralus-01.azurewebsites.net  # Optional, has default
EVAL_GROUP_ID=<eval_group_id>                 # Required (constant per exercise)
RAGMETRICS_TYPE=S                             # Optional, default: "S"

# RAG Configuration
RAG_TOP_K=3                                   # Optional, default: 3
```

**Note**: All variables are loaded via `pydantic-settings` with validation. Missing required variables will cause startup errors.

### 5. Dependencies

All dependencies are listed in `requirements.txt`:

- `openai>=1.0.0` - OpenAI Python SDK for chat completion and embeddings
- `pinecone-client>=2.2.0` - Pinecone Python SDK for vector database access
- `python-dotenv>=1.0.0` - Environment variable loading (.env file)
- `requests>=2.31.0` - HTTP client for RagMetrics API calls
- `pydantic>=2.0.0` - Data validation and models
- `pydantic-settings>=2.0.0` - Settings management with environment variable support

Install with: `pip install -r requirements.txt`

### 6. API Integration Details

#### RagMetrics API
- **Base URL**: `https://ragmetrics-staging-docker-c9ana3hgacg3fbbt.centralus-01.azurewebsites.net`
- **Endpoint**: `/v2/single-evaluation/`
- **Method**: POST
- **Headers**:
  - `Authorization: Token {RAGMETRICS_API_KEY}`
  - `Content-Type: application/json`
- **Body Structure**:
  ```json
  {
    "question": str,          // User's question
    "ground_truth": "",       // Empty string (as per requirements)
    "answer": str,            // Generated answer from OpenAI
    "eval_group_id": str,     // Constant value from .env
    "context": str,           // Retrieved context from Pinecone
    "type": "S"               // Always "S"
  }
  ```
- **Error Handling**: Non-blocking - failures are logged but don't stop chat flow
- **Timeout**: 30 seconds

#### OpenAI API
- **Service**: OpenAI Chat Completions API
- **Model**: Configurable via `OPENAI_MODEL` (default: `gpt-3.5-turbo`)
- **Embeddings Model**: `text-embedding-ada-002` (hardcoded for Pinecone queries)
- **Temperature**: 0.7
- **Max Tokens**: 500

#### Pinecone API
- **Service**: Pinecone Vector Database
- **Query Method**: Vector similarity search
- **Top-K**: 3 results (configurable via `RAG_TOP_K`)
- **Embedding**: Generated via OpenAI embeddings API
- **Metadata Extraction**: Looks for `text`, `content`, or `chunk` keys in metadata

### 7. Implementation Decisions

#### Decided Requirements:

1. **Ground Truth**: Empty string `""` for all evaluations (as specified)

2. **EVAL_GROUP_ID**: Constant value stored in `.env` file

3. **Type Field**: Always `"S"` for all RagMetrics submissions

4. **Interface Type**: CLI with interactive chat loop
   - User types questions, presses Enter
   - System processes and displays answer
   - Exit with `quit`, `exit`, or `q`

5. **Pinecone Setup**: 
   - Index name: Configurable via `PINECONE_INDEX_NAME` in `.env`
   - Embedding model: OpenAI `text-embedding-ada-002` (hardcoded in `pinecone_rag.py`)
   - Top-K results: 3 (configurable via `RAG_TOP_K`, default: 3)

6. **OpenAI Model**: Configurable via `OPENAI_MODEL` in `.env` (default: `gpt-3.5-turbo`)

7. **Error Handling Strategy**:
   - **Pinecone errors**: Logged, return empty context, continue
   - **OpenAI errors**: Logged, raise exception (blocks processing)
   - **RagMetrics errors**: Logged, alert user, continue (non-blocking)

8. **Conversation History**: Not implemented - each question is processed independently

9. **Logging**: INFO level by default, includes timestamps and module names

### 8. Technical Details

#### Embedding Generation
- Query text is embedded using OpenAI `text-embedding-ada-002`
- Embedding is generated in `PineconeRAG._get_query_embedding()`
- Embedding dimension must match Pinecone index dimension

#### Context Formatting
- Pinecone results are extracted from metadata fields: `text`, `content`, or `chunk`
- Multiple results are joined with double newlines (`\n\n`)
- Empty context is handled gracefully by OpenAI client

#### Error Resilience
- System continues on RagMetrics failures (logs warning, alerts user)
- System continues on Pinecone failures (uses empty context)
- System fails only on OpenAI errors (can't generate answer)

#### CLI User Experience
- Clean, formatted output with separators
- Progress indicators during processing
- Success/failure indicators for RagMetrics submission
- Graceful shutdown on Ctrl+C or exit commands

### 9. Future Enhancements (Not Implemented)

- Conversation history tracking across multiple turns
- Configurable embedding models
- Retry logic for failed API calls
- REST API server mode
- Batch processing mode
- Ground truth collection from user input
- Metrics collection and reporting

