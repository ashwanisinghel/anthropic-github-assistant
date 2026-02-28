"""
GitHub Agent using Claude API
-------------------------------
This agent can answer questions about your GitHub repositories.
It uses Claude's "tool use" feature to call GitHub API functions
and return real data before generating a final answer.

SETUP:
    pip install anthropic requests

    Set environment variables:
        export ANTHROPIC_API_KEY="your_anthropic_key"
        export GITHUB_TOKEN="your_github_personal_access_token"
        export GITHUB_USERNAME="your_github_username"
"""


import os
import json
import dotenv
import requests
import anthropic


dotenv.load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")

GITHUB_HEADERS = {
   "Authorization": f"Bearer {GITHUB_TOKEN}",
   "Accept": "application/vnd.github+json",
}


# ─────────────────────────────────────────────
# 1. CONFIGURATION
# ─────────────────────────────────────────────

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "YOUR_ANTHROPIC_KEY")
GITHUB_TOKEN      = os.environ.get("GITHUB_TOKEN", "YOUR_GITHUB_TOKEN")
GITHUB_USERNAME   = os.environ.get("GITHUB_USERNAME", "YOUR_GITHUB_USERNAME")

GITHUB_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# ─────────────────────────────────────────────
# 2. TOOL FUNCTIONS  (real GitHub API calls)
# ─────────────────────────────────────────────

def list_repositories(username: str) -> dict:
    """Return a list of repos for the given GitHub username."""
    url = f"https://api.github.com/users/{username}/repos"
    response = requests.get(url, headers=GITHUB_HEADERS, params={"per_page": 50})
    if response.status_code != 200:
        return {"error": f"GitHub API error: {response.status_code}", "repos": []}
    repos = [
        {
            "name": r["name"],
            "description": r["description"] or "No description",
            "language": r["language"] or "Unknown",
            "stars": r["stargazers_count"],
            "url": r["html_url"],
        }
        for r in response.json()
    ]
    return {"repos": repos, "count": len(repos)}


def get_repository_details(username: str, repo_name: str) -> dict:
    """Return detailed info about a specific repository."""
    url = f"https://api.github.com/repos/{username}/{repo_name}"
    response = requests.get(url, headers=GITHUB_HEADERS)
    if response.status_code == 404:
        return {"error": "NOT_FOUND", "message": f"Repository '{repo_name}' not found."}
    if response.status_code != 200:
        return {"error": f"GitHub API error: {response.status_code}"}
    r = response.json()
    return {
        "name": r["name"],
        "description": r["description"] or "No description",
        "language": r["language"] or "Unknown",
        "stars": r["stargazers_count"],
        "forks": r["forks_count"],
        "open_issues": r["open_issues_count"],
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
        "url": r["html_url"],
        "topics": r.get("topics", []),
    }


# ─────────────────────────────────────────────
# 3. TOOL DEFINITIONS  (tell Claude what tools exist)
# ─────────────────────────────────────────────

TOOLS = [
    {
        "name": "list_repositories",
        "description": (
            "Lists all GitHub repositories for a user. "
            "Use this when the user asks about what repos they have."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "The GitHub username to list repos for.",
                }
            },
            "required": ["username"],
        },
    },
    {
        "name": "get_repository_details",
        "description": (
            "Gets detailed information about a specific repository. "
            "Returns NOT_FOUND error if the repo doesn't exist."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "The GitHub username.",
                },
                "repo_name": {
                    "type": "string",
                    "description": "The exact repository name.",
                },
            },
            "required": ["username", "repo_name"],
        },
    },
]


# ─────────────────────────────────────────────
# 4. TOOL ROUTER  (maps tool name → actual function)
# ─────────────────────────────────────────────

def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool by name and return its result as a JSON string."""
    if tool_name == "list_repositories":
        result = list_repositories(tool_input["username"])
    elif tool_name == "get_repository_details":
        result = get_repository_details(tool_input["username"], tool_input["repo_name"])
    else:
        result = {"error": f"Unknown tool: {tool_name}"}
    return json.dumps(result, indent=2)


# ─────────────────────────────────────────────
# 5. AGENT LOOP  (the core of how agents work)
# ─────────────────────────────────────────────

def run_agent(user_question: str) -> str:
    """
    Agent loop:
      1. Send user message + tools to Claude.
      2. If Claude wants to call a tool → run it → feed result back.
      3. Repeat until Claude gives a final text answer.
    """
    print(f"\n{'='*60}")
    print(f"USER: {user_question}")
    print(f"{'='*60}")

    messages = [{"role": "user", "content": user_question}]

    system_prompt = (
        f"You are a helpful GitHub assistant for the user '{GITHUB_USERNAME}'. "
        "Use the provided tools to look up real repository data before answering. "
        "If a repository is not found, clearly say 'Not Found' and suggest alternatives. "
        "Always be concise and factual."
    )

    # Agent loop — keeps running until Claude stops calling tools
    while True:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )

        print(f"\n[Agent thinking... stop_reason={response.stop_reason}]")

        # ── Case 1: Claude wants to call a tool ──
        if response.stop_reason == "tool_use":
            # Add Claude's response (which includes the tool call) to history
            messages.append({"role": "assistant", "content": response.content})

            # Process every tool call Claude requested
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  → Calling tool: {block.name}({block.input})")
                    result = execute_tool(block.name, block.input)
                    print(f"  ← Tool result: {result[:200]}...")  # preview
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            # Feed tool results back to Claude
            messages.append({"role": "user", "content": tool_results})

        # ── Case 2: Claude has a final answer ──
        elif response.stop_reason == "end_turn":
            final_answer = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_answer += block.text
            print(f"\nAGENT: {final_answer}")
            return final_answer

        # ── Case 3: Unexpected stop ──
        else:
            return f"Unexpected stop reason: {response.stop_reason}"


# ─────────────────────────────────────────────
# 6. MAIN  — example questions to try
# ─────────────────────────────────────────────

if __name__ == "__main__":
    questions = [
        f"What repositories does {GITHUB_USERNAME} have?",
        f"Tell me about the repo called 'TimeDashboard' by {GITHUB_USERNAME}",
        f"What languages does {GITHUB_USERNAME} mostly use?",
    ]

    for question in questions:
        run_agent(question)
        print("\n")


