# GitHub Repository Setup Instructions

## Step 1: Create Repository on GitHub
1. Go to https://github.com/new
2. Repository name: `chat_test`
3. Choose Public or Private
4. **Do NOT** initialize with README, .gitignore, or license
5. Click "Create repository"

## Step 2: Connect and Push

After creating the repository, GitHub will show you commands. Use these:

```bash
# Add the remote repository (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/chat_test.git

# Rename branch to main (if needed)
git branch -M main

# Push to GitHub
git push -u origin main
```

## Alternative: Using SSH

If you prefer SSH:

```bash
git remote add origin git@github.com:YOUR_USERNAME/chat_test.git
git branch -M main
git push -u origin main
```

## Files Included

The repository includes:
- All source code files
- Configuration files
- README.md with setup instructions
- requirements.txt
- .gitignore (excludes .env, venv, __pycache__, etc.)

## Files Excluded (via .gitignore)

- `.env` file (contains sensitive API keys)
- `venv/` directory (virtual environment)
- `__pycache__/` directories
- IDE and OS-specific files

## Important Notes

- **Never commit your `.env` file** - it contains sensitive API keys
- The `.env.txt` file is included as a template
- Users need to create their own `.env` file from `.env.txt`

