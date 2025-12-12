# RagMetrics - Self Corrected Chatbot

A self-correcting chat engine based on OpenAI that answers questions using data retrieved from a Pinecone RAG system, evaluates responses with RagMetrics API, and automatically regenerates answers when quality thresholds are not met.

## Features

- **RAG-based Chat**: Retrieves relevant context from Pinecone vector database
- **OpenAI Integration**: Uses OpenAI chat completion to generate answers
- **RagMetrics Evaluation**: Automatically sends evaluation data to RagMetrics API
- **Self-Correction**: Automatically regenerates answers when evaluation scores exceed thresholds
- **CLI Interface**: Interactive command-line interface for chat
- **Web UI**: Streamlit-based web interface with inline evaluation results
- **Password Protection**: Secure access with configurable passcode

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the `.env` file and update it with your credentials:

- **OpenAI**: `OPENAI_API_KEY`, `OPENAI_MODEL`
- **Pinecone**: `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`
- **RagMetrics**: `RAGMETRICS_API_KEY`, `EVAL_GROUP_ID`

See `.env` file for all required variables.

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

**Password Protection**: The app requires a passcode to access. Default passcode is "Messi2022" if not configured in `.env`.

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

## Notes

- **Ground Truth**: Currently set to empty string `""` for evaluation
- **Evaluation Group ID**: Constant value from `.env`
- **Type**: Always `"S"` for RagMetrics submissions
- **Top-K Results**: Configurable via `RAG_TOP_K` (default: 5)
- **Regeneration Threshold**: Configurable via `REG_SCORE` (default: 3) - regenerates if any criteria score >= this value
- **Password Protection**: Default passcode is "Messi2022" if `PASSCODE` is not set in `.env`
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


