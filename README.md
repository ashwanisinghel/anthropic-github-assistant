# GitHub Agent using Claude API

A simple Python-based Agent that uses the Claude API and GitHub's API to answer questions about your GitHub repositories. It utilizes Claude's "tool use" feature to interactively fetch live repository data before generating a final answer.

## Requirements

Ensure you have Python 3.9+ installed.

Dependencies:
- `anthropic`
- `requests`
- `dotenv` (to load environment variables)

## Setup

1. **Install dependencies:**
   You can install the dependencies via pip (or `uv` since a `uv.lock` is present):
   ```bash
   pip install anthropic requests python-dotenv
   ```

2. **Environment Variables:**
   Create a `.env` file in the root directory and configure the following variables:
   ```env
   ANTHROPIC_API_KEY="your_anthropic_api_key"
   GITHUB_TOKEN="your_github_personal_access_token"
   GITHUB_USERNAME="your_github_username"
   ```

## Usage

Simply run `main.py` to start the agent loop:

```bash
python main.py
```

The script runs a few example questions interacting with the assigned `GITHUB_USERNAME`, utilizing the implemented tools to query the GitHub API and provide accurate, context-aware answers.

## Available Tools

The agent has access to the following GitHub API tools:
- **`list_repositories`**: Fetches a list of public repositories for a given user.
- **`get_repository_details`**: Retrieves detailed info (description, language, stars, forks, issues) about a specific repository.
