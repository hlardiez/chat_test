# Deploying to Streamlit Community Cloud

This guide explains how to deploy the RagMetrics Self Corrected Chatbot to Streamlit Community Cloud.

## Prerequisites

1. GitHub account with the repository pushed
2. Streamlit Cloud account (free at https://share.streamlit.io)
3. All environment variables ready

## Step 1: Push to GitHub

Make sure your code is pushed to GitHub (see `GITHUB_SETUP.md` for instructions).

## Step 2: Deploy on Streamlit Cloud

1. Go to https://share.streamlit.io
2. Sign in with your GitHub account
3. Click "New app"
4. Select your repository: `chat_test`
5. Main file path: `web_ui.py`
6. Python version: 3.10 or 3.11 (recommended)

## Step 3: Configure Environment Variables

**IMPORTANT**: Streamlit Cloud does NOT use `.env` files. You must set environment variables in the Streamlit Cloud dashboard.

### Required Environment Variables

Set these in the Streamlit Cloud app settings (under "⚙️ Settings" → "Secrets"):

**Format**: Streamlit Cloud uses TOML format. Paste this into the secrets editor:

```toml
OPENAI_API_KEY = "your_openai_api_key_here"
OPEN_AI_MODEL = "gpt-3.5-turbo"
PINECONE_API_KEY = "your_pinecone_api_key_here"
PINECONE_INDEX = "your_index_name"
RAGMETRICS_API_KEY = "your_ragmetrics_api_key_here"
RAGMETRICS_URL = "https://ragmetrics-staging-docker-c9ana3hgacg3fbbt.centralus-01.azurewebsites.net"
RAGMETRICS_EVAL_GROUP_ID = "your_eval_group_id"
RAGMETRICS_EVAL_TYPE = "S"
RAGMETRICS_CONVERSATION_ID = "Conv_ID_1"
EMBEDDING_MODEL = "text-embedding-3-small"
RAG_TOP_K = "5"
REG_SCORE = "3"
PASSCODE = "Messi2022"
```

### Optional Environment Variables

```toml
PINECONE_HOST = "your_pinecone_host"  # if needed
PINECONE_NAMESPACE = "your_namespace"  # if needed, otherwise auto-detected
```

## Step 4: Setting Secrets in Streamlit Cloud

1. In your app dashboard, click "⚙️" (Settings) → "Secrets"
2. Paste the TOML format secrets (as shown above) with your actual values
3. Click "Save"
4. The app will automatically redeploy

**Note**: Values in Streamlit Cloud secrets are automatically available as environment variables, which `pydantic-settings` will read automatically.

**Alternative Method**: You can also create a `.streamlit/secrets.toml` file in your repository (but this is less secure for sensitive keys).

## Step 5: Deploy

1. Click "Deploy" or wait for automatic deployment
2. Streamlit Cloud will install dependencies from `requirements.txt`
3. The app will be available at: `https://your-app-name.streamlit.app`

## Important Notes

### Environment Variables vs .env File

- **Local Development**: Uses `.env` file (loaded by `pydantic-settings`)
- **Streamlit Cloud**: Uses secrets configured in the dashboard (also loaded by `pydantic-settings`)

The `config/settings.py` file uses `pydantic-settings` which automatically reads from:
1. Environment variables (set in Streamlit Cloud dashboard)
2. `.env` file (for local development)

So your code will work in both environments without changes!

### Security Best Practices

1. **Never commit `.env` file** - Already excluded in `.gitignore`
2. **Use Streamlit Secrets** - More secure than hardcoding
3. **Rotate API keys** - Change them periodically
4. **Use different passcodes** - Don't use default "Messi2022" in production

### Troubleshooting

**App fails to start:**
- Check that all required environment variables are set
- Verify API keys are correct
- Check the logs in Streamlit Cloud dashboard

**Import errors:**
- Ensure `requirements.txt` includes all dependencies
- Check Python version compatibility

**Environment variables not working:**
- Verify secrets are saved in Streamlit Cloud dashboard
- Check variable names match exactly (case-sensitive)
- Restart the app after adding secrets

## File Structure for Deployment

Make sure these files are in your repository:
- ✅ `web_ui.py` (main Streamlit app)
- ✅ `requirements.txt` (dependencies)
- ✅ `config/settings.py` (configuration)
- ✅ `src/` directory (all source modules)
- ✅ `.gitignore` (excludes .env, venv, etc.)
- ❌ `.env` (should NOT be in repository)

## Example Streamlit Cloud Configuration

```
Repository: your-username/chat_test
Branch: main
Main file: web_ui.py
Python version: 3.10
```

## Monitoring

After deployment, you can:
- View logs in the Streamlit Cloud dashboard
- Monitor usage and performance
- Update secrets without redeploying
- View app analytics

## Updating the App

1. Make changes to your code
2. Push to GitHub
3. Streamlit Cloud automatically redeploys
4. Or manually trigger redeploy from dashboard

