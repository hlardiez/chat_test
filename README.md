# RagMetrics - Self Correcting Chatbot

A self-correcting chat engine based on OpenAI that answers questions using data retrieved from a Pinecone RAG system, evaluates responses with RagMetrics API, and automatically regenerates answers when quality thresholds are not met.

## Features

- **RAG-based Chat**: Retrieves relevant context from Pinecone vector database
- **OpenAI Integration**: Uses OpenAI chat completion to generate answers
- **RagMetrics Evaluation**: Automatically sends evaluation data to RagMetrics API
- **Self-Correction**: Automatically regenerates answers when evaluation scores exceed thresholds
- **CLI Interface**: Interactive command-line interface for chat
- **Web UI**: Streamlit-based web interface with inline evaluation results

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the `.env` file and update it with your credentials:

- **OpenAI**: `OPENAI_API_KEY`, `OPEN_AI_MODEL`
- **Pinecone**: `PINECONE_API_KEY`, `PINECONE_INDEX`
- **RagMetrics**: `RAGMETRICS_API_KEY`, `RAGMETRICS_EVAL_GROUP_ID`, `RAGMETRICS_CONVERSATION_ID`
- **UI Configuration**: `TOPIC` (optional, defaults to "the US Constitution")

See `.env` file for all required variables. See `STREAMLIT_CLOUD_DEPLOY.md` for a complete list of environment variables.

### 3. Run the Chat Engine

**CLI Mode:**
```bash
python main.py
```

**Web UI Mode:**
```bash
streamlit run web_ui.py
```

The web UI will open in your default browser at `http://localhost:8501`

## Usage

### CLI Mode

Once running, type your questions and press Enter. The system will:

1. Retrieve relevant context from Pinecone RAG system (top K results, configurable via `RAG_TOP_K`)
2. Generate an answer using OpenAI
3. Send evaluation data to RagMetrics API
4. Display evaluation results and regenerate answer if needed

Type `quit`, `exit`, or `q` to end the session.

### Web UI Mode

The web interface provides a single scrollable conversation panel:

- **Conversation Panel**: 
  - Shows all conversation history with questions and answers
  - Displays evaluation results inline with each conversation entry
  - Shows criteria name and score (e.g., "Hallucination: 2")
  - When regeneration occurs, displays "Criteria: Score | Answer Regenerated" in red
  - Shows original question and truncated answer when regeneration is triggered

## Project Structure

```
chat_test/
├── src/
│   ├── chat_engine.py       # Main orchestrator
│   ├── openai_client.py     # OpenAI API client
│   ├── pinecone_rag.py      # Pinecone RAG integration
│   ├── ragmetrics_client.py # RagMetrics API client
│   └── utils.py             # Utility functions
├── config/
│   └── settings.py          # Configuration management
├── main.py                  # CLI entry point
├── web_ui.py                # Streamlit web UI entry point
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables
└── README.md               # This file
```

## Configuration

### Environment Variables

All configuration is managed through environment variables (loaded via `pydantic-settings`):

- **OpenAI**: `OPENAI_API_KEY` (required), `OPEN_AI_MODEL` (default: "gpt-3.5-turbo")
- **Pinecone**: `PINECONE_API_KEY` (required), `PINECONE_INDEX` (required), `PINECONE_NAMESPACE` (optional, auto-detected if not set)
- **RagMetrics**: `RAGMETRICS_API_KEY` (required), `RAGMETRICS_EVAL_GROUP_ID` (required), `RAGMETRICS_CONVERSATION_ID` (required), `RAGMETRICS_URL` (default: "https://api.ragmetrics.ai")
- **RAG Configuration**: `RAG_TOP_K` (default: 5), `EMBEDDING_MODEL` (default: "text-embedding-3-small")
- **Regeneration**: `REG_SCORE` (default: 3) - regenerates if any criteria score >= this value
- **UI Configuration**: `TOPIC` (default: "the US Constitution") - defines the subject/topic displayed in the web UI

### Notes

- **Ground Truth**: Currently set to empty string `""` for evaluation
- **Evaluation Type**: Always `"S"` for RagMetrics submissions
- **Topic/Subject**: Configurable via `TOPIC` environment variable in `config/settings.py`. Default value is "the US Constitution". This controls the subheader text in the web UI.
- **Error Handling**: RagMetrics failures are logged but don't stop the chat

## Deployment to Streamlit Community Cloud

See [STREAMLIT_CLOUD_DEPLOY.md](STREAMLIT_CLOUD_DEPLOY.md) for detailed deployment instructions.

### Quick Deployment Steps:

1. Push your code to GitHub
2. Go to https://share.streamlit.io
3. Connect your GitHub repository
4. Set environment variables in Streamlit Cloud dashboard (Settings → Secrets)
5. Deploy!

### Environment Variables on Streamlit Cloud

**Important**: Streamlit Cloud does NOT use `.env` files. You must set environment variables in the Streamlit Cloud dashboard under "Secrets".

The application uses `pydantic-settings` which automatically reads from:
- Environment variables (set in Streamlit Cloud dashboard)
- `.env` file (for local development)

So your code works in both environments without changes!

All required environment variables are listed in `STREAMLIT_CLOUD_DEPLOY.md`.

## Troubleshooting

- Ensure all API keys are correctly set in `.env` (local) or Streamlit Secrets (cloud)
- Check that Pinecone index name matches your setup
- Verify RagMetrics API endpoint is accessible
- Check logs for detailed error messages
- For Streamlit Cloud: Verify secrets are saved and app is restarted after adding secrets


