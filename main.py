"""
GitHub Agent using LangChain + Claude
---------------------------------------
Same agent as before but LangChain handles the agent loop for you.

SETUP:
    pip install langchain langchain-anthropic requests

    Set environment variables:
        export ANTHROPIC_API_KEY="your_anthropic_key"
        export GITHUB_TOKEN="your_github_personal_access_token"
        export GITHUB_USERNAME="your_github_username"
"""

import os
import json
import dotenv
import requests
from langchain_anthropic import ChatAnthropic
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool


dotenv.load_dotenv()

# ─────────────────────────────────────────────
# 1. CONFIGURATION
# ─────────────────────────────────────────────

GITHUB_TOKEN    = os.environ.get("GITHUB_TOKEN")
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

GITHUB_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}

# ─────────────────────────────────────────────
# 2. TOOLS  (just decorate normal functions with @tool)
# ─────────────────────────────────────────────

@tool
def list_repositories(username: str) -> str:
    """Lists all GitHub repositories for a given username."""
    url = f"https://api.github.com/users/{username}/repos"
    response = requests.get(url, headers=GITHUB_HEADERS, params={"per_page": 50})
    if response.status_code != 200:
        return f"Error fetching repos: {response.status_code}"
    repos = [
        {
            "name": r["name"],
            "description": r["description"] or "No description",
            "language": r["language"] or "Unknown",
            "stars": r["stargazers_count"],
        }
        for r in response.json()
    ]
    return json.dumps(repos, indent=2)


@tool
def get_repository_details(username: str, repo_name: str) -> str:
    """Gets detailed info about a specific GitHub repository. Returns NOT_FOUND if it doesn't exist."""
    url = f"https://api.github.com/repos/{username}/{repo_name}"
    response = requests.get(url, headers=GITHUB_HEADERS)
    if response.status_code == 404:
        return "NOT_FOUND: Repository does not exist."
    if response.status_code != 200:
        return f"Error: {response.status_code}"
    r = response.json()
    return json.dumps({
        "name": r["name"],
        "description": r["description"] or "No description",
        "language": r["language"] or "Unknown",
        "stars": r["stargazers_count"],
        "forks": r["forks_count"],
        "open_issues": r["open_issues_count"],
        "updated_at": r["updated_at"],
        "url": r["html_url"],
    }, indent=2)


# ─────────────────────────────────────────────
# 3. AGENT SETUP  (LangChain handles the loop)
# ─────────────────────────────────────────────

# Choose your model — swap to haiku for lower cost
llm = ChatAnthropic(
    model="claude-haiku-4-5-20251001",  # cost-effective
    max_tokens=512,
    api_key=ANTHROPIC_API_KEY,
)

tools = [list_repositories, get_repository_details]

prompt = ChatPromptTemplate.from_messages([
    ("system", 
     f"You are a helpful GitHub assistant for the user '{GITHUB_USERNAME}'. "
     "Use tools to fetch real data before answering. "
     "If a repo is not found, clearly say 'Not Found'."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),  # required for tool call history
])

# Create the agent and executor — this replaces your manual while loop
agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)


# ─────────────────────────────────────────────
# 4. RUN  (one line to invoke!)
# ─────────────────────────────────────────────

def ask(question: str) -> str:
    result = agent_executor.invoke({"input": question})
    return result["output"]


if __name__ == "__main__":
    questions = [
        f"What repos does {GITHUB_USERNAME} have?",
        f"Tell me about the repo 'anthropic-github-assistant' by {GITHUB_USERNAME}",
        f"What's the most starred repo of {GITHUB_USERNAME}?",
    ]

    for q in questions:
        print(f"\nQ: {q}")
        print(f"A: {ask(q)}")
        print("-" * 60)