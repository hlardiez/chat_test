# RagMetrics - Self Correcting Chatbot - Architecture Document

## Project Overview

A self-correcting chat engine built on OpenAI that:
1. Answers questions using data retrieved from a Pinecone RAG system
2. Collects the question, answer, and RAG context
3. Sends evaluation data to RagMetrics API
4. Automatically regenerates answers when evaluation scores exceed thresholds

## Status: ✅ Implemented

This architecture document reflects the implemented system with self-correction capabilities.

## Architecture Components

### 1. Core Modules

```
chat_test/
├── src/
│   ├── __init__.py
│   ├── chat_engine.py          # Main chat orchestrator with self-correction
│   ├── openai_client.py        # OpenAI API integration
│   ├── pinecone_rag.py         # Pinecone vector database integration
│   ├── ragmetrics_client.py    # RagMetrics API integration
│   ├── prompt.py               # Prompt templates
│   └── utils.py                # Helper functions
├── config/
│   └── settings.py             # Configuration management
├── main.py                     # CLI entry point
├── web_ui.py                  # Streamlit web UI entry point
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (local development)
├── README.md                   # Project documentation
├── ARCHITECTURE.md            # This file
└── STREAMLIT_CLOUD_DEPLOY.md  # Deployment guide
```

### 2. Data Flow

```
User Question (CLI/Web UI Input)
    ↓
Chat Engine (orchestrates)
    ↓
┌─────────────────────────────────────┐
│  1. Pinecone RAG System            │
│     - Generate query embedding     │
│       (OpenAI text-embedding-3-small)│
│     - Query Pinecone vector DB     │
│     - Retrieve top K results       │
│       (configurable, default: 5)   │
│     - Format context string        │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  2. OpenAI Chat Completion         │
│     - Build prompt with context    │
│     - Call OpenAI API              │
│     - Extract generated answer     │
│     - Return answer                │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  3. RagMetrics Evaluation          │
│     - Collect: question, answer,   │
│       context, ground_truth (""),  │
│       eval_group_id, conversation_id│
│       type ("S")                   │
│     - Send POST to RagMetrics API  │
│     - Receive evaluation results   │
│       (criteria scores)            │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  4. Self-Correction Check          │
│     - Check if any criteria score  │
│       >= REG_SCORE (default: 3)    │
│     - If yes: Regenerate answer    │
│       with correction prompt        │
│     - If no: Use original answer   │
└─────────────────────────────────────┘
    ↓
Return result to user (CLI/Web UI)
```

### 3. Module Responsibilities

#### `chat_engine.py`
- Main orchestrator class
- Coordinates between OpenAI, Pinecone, and RagMetrics
- Manages conversation flow and self-correction logic
- Checks evaluation scores and triggers regeneration when needed
- Handles error cases

#### `openai_client.py`
- Wraps OpenAI API calls using OpenAI Python SDK
- Handles chat completion with context injection
- Builds system and user prompts with RAG context
- Provides answer regeneration functionality with correction prompts
- Configurable model via environment variable (default: `gpt-3.5-turbo`)
- Manages API key and configuration from settings

#### `pinecone_rag.py`
- Connects to Pinecone vector database using API key
- Generates query embeddings using configurable OpenAI embedding model
  (default: `text-embedding-3-small`, supports dimension matching)
- Auto-detects Pinecone namespace if not explicitly configured
- Performs vector similarity search (top-k configurable, default: 5)
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
- Uses lazy initialization for Streamlit Cloud compatibility
- Ignores extra environment variables (for backward compatibility)
- Centralized configuration management

#### `utils.py`
- Logging configuration (`setup_logging()`)
- Context formatting utilities
- Helper functions for data processing

#### `main.py`
- CLI entry point for the application
- Interactive chat loop with user input
- Displays answers, evaluation results, and regenerated answers
- Error handling and graceful shutdown
- User-friendly output formatting
- Exit commands: `quit`, `exit`, `q`

#### `web_ui.py`
- Streamlit web interface entry point
- Provides interactive web UI with conversation history
- Displays evaluation results inline with answers
- Shows regenerated answers when self-correction is triggered
- Manages session state and processing flow
- Responsive design with scrollable conversation panel

### 4. Configuration Requirements

Environment variables required (in `.env`):
```bash
# OpenAI Configuration
OPENAI_API_KEY=<your_openai_key>              # Required
OPEN_AI_MODEL=gpt-3.5-turbo                  # Optional, default: gpt-3.5-turbo

# Pinecone Configuration
PINECONE_API_KEY=<your_pinecone_key>          # Required
PINECONE_INDEX=<index_name>                   # Required
PINECONE_NAMESPACE=<namespace>                # Optional, auto-detected if not set
PINECONE_HOST=<host>                          # Optional

# RagMetrics Configuration
RAGMETRICS_API_KEY=<ragmetrics_api_key>       # Required
RAGMETRICS_URL=https://api.ragmetrics.ai      # Optional, has default
RAGMETRICS_EVAL_GROUP_ID=<eval_group_id>      # Required
RAGMETRICS_CONVERSATION_ID=<conv_id>          # Required
RAGMETRICS_EVAL_TYPE=S                        # Optional, default: "S"

# RAG Configuration
RAG_TOP_K=5                                   # Optional, default: 5
EMBEDDING_MODEL=text-embedding-3-small        # Optional, default: text-embedding-3-small

# Regeneration Configuration
REG_SCORE=3                                   # Optional, default: 3

# UI Configuration
TOPIC="your chatbot topic"                     # Optional, default: "the US Constitution"
```

**Note**: All variables are loaded via `pydantic-settings` with validation. Missing required variables will cause startup errors. Extra variables (like removed PASSCODE) are ignored.

### 5. Dependencies

All dependencies are listed in `requirements.txt`:

- `openai>=1.0.0` - OpenAI Python SDK for chat completion and embeddings
- `pinecone>=7.0.0` - Pinecone Python SDK for vector database access
- `python-dotenv>=1.0.0` - Environment variable loading (.env file)
- `requests>=2.31.0` - HTTP client for RagMetrics API calls
- `pydantic>=2.0.0` - Data validation and models
- `pydantic-settings>=2.0.0` - Settings management with environment variable support
- `streamlit>=1.28.0` - Web UI framework

Install with: `pip install -r requirements.txt`

### 6. API Integration Details

#### RagMetrics API
- **Base URL**: `https://api.ragmetrics.ai`
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
    "eval_group_id": str,     // Value from RAGMETRICS_EVAL_GROUP_ID
    "conversation_id": str,   // Value from RAGMETRICS_CONVERSATION_ID
    "context": str,           // Retrieved context from Pinecone
    "type": "S"               // Always "S"
  }
  ```
- **Response**: Returns evaluation results with criteria scores (e.g., Accuracy, Hallucination)
- **Error Handling**: Non-blocking - failures are logged but don't stop chat flow
- **Timeout**: 30 seconds

#### OpenAI API
- **Service**: OpenAI Chat Completions API
- **Model**: Configurable via `OPEN_AI_MODEL` (default: `gpt-3.5-turbo`)
- **Embeddings Model**: Configurable via `EMBEDDING_MODEL` (default: `text-embedding-3-small`)
  - Supports dimension matching for Pinecone index compatibility
  - Models: `text-embedding-ada-002` (1536 dims), `text-embedding-3-small` (1536 or custom), `text-embedding-3-large` (3072 or custom)
- **Temperature**: 0.7
- **Max Tokens**: 500

#### Pinecone API
- **Service**: Pinecone Vector Database
- **Query Method**: Vector similarity search
- **Top-K**: Configurable via `RAG_TOP_K` (default: 5)
- **Namespace**: Auto-detected from index stats if not explicitly configured
- **Embedding**: Generated via OpenAI embeddings API with dimension matching
- **Metadata Extraction**: Looks for `text`, `content`, `chunk`, `page_content`, `document`, or `value` keys in metadata

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
   - Index name: Configurable via `PINECONE_INDEX` in `.env`
   - Namespace: Auto-detected or configurable via `PINECONE_NAMESPACE`
   - Embedding model: Configurable via `EMBEDDING_MODEL` (default: `text-embedding-3-small`)
   - Top-K results: Configurable via `RAG_TOP_K` (default: 5)

6. **OpenAI Model**: Configurable via `OPEN_AI_MODEL` in `.env` (default: `gpt-3.5-turbo`)

7. **Self-Correction**:
   - Regeneration threshold: Configurable via `REG_SCORE` (default: 3)
   - Triggers when any evaluation criteria score >= `REG_SCORE`
   - Uses specialized regeneration prompt to correct errors
   - Only first answer is evaluated; regenerated answer is not re-evaluated

8. **Error Handling Strategy**:
   - **Pinecone errors**: Logged, return empty context, continue
   - **OpenAI errors**: Logged, raise exception (blocks processing)
   - **RagMetrics errors**: Logged, alert user, continue (non-blocking)

9. **Interfaces**:
   - **CLI**: Interactive command-line interface (`main.py`)
   - **Web UI**: Streamlit-based web interface (`web_ui.py`)
   - Both interfaces support the same functionality

10. **UI Configuration**:
    - Topic/subject: Configurable via `TOPIC` environment variable (default: "the US Constitution")
    - Controls the subheader text displayed in the web UI

11. **Logging**: WARNING level by default in production, includes timestamps and module names

### 8. Technical Details

#### Embedding Generation
- Query text is embedded using configurable OpenAI embedding model
- Embedding is generated in `PineconeRAG._get_query_embedding()`
- Embedding dimension must match Pinecone index dimension
- For `text-embedding-3-*` models, dimensions can be set to match index requirements

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

### 9. Self-Correction Implementation

- **Evaluation**: All answers are evaluated using RagMetrics API
- **Threshold Check**: If any criteria score >= `REG_SCORE`, regeneration is triggered
- **Regeneration**: Uses specialized prompt emphasizing strict adherence to context
- **Display**: Original answer shown if regeneration occurs, regenerated answer replaces it
- **Single Evaluation**: Only the first answer is evaluated; regenerated answer is not re-evaluated

### 10. Future Enhancements (Not Implemented)

- Conversation history tracking across multiple turns
- Re-evaluation of regenerated answers
- Retry logic for failed API calls
- REST API server mode
- Batch processing mode
- Ground truth collection from user input
- Metrics collection and reporting
- Multiple evaluation criteria thresholds

