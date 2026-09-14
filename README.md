# Bookly support agent demo

A small browser-based customer support prototype for a **fictional** bookstore. The backend is Python's standard-library HTTP server; the frontend is plain HTML, CSS, and JavaScript. No framework or database is required.

## Run locally

Requires Python 3.9 or later.

```bash
python3 server.py
```

Open <http://localhost:8000>. With no API key, the app visibly labels itself **Scripted demo** and uses predictable fallback replies. To use a real model, set `OPENAI_API_KEY` in your shell before starting the server. `OPENAI_MODEL` is optional; it defaults to `gpt-5-mini`. The key stays on the server and must never be committed.

The **Demo orders** panel lists the fictional order numbers, emails, and best workflow to try for each one.

```bash
export OPENAI_API_KEY="your-key"
python3 server.py
```

The API-backed chat path calls the OpenAI Responses API directly using `urllib.request`, passes explicit function definitions, executes selected functions in Python, and submits function outputs back to the model. Conversation turns are supplied on each request; API response storage is disabled.

The microphone has two modes. With `OPENAI_API_KEY`, press once to start recording and again to stop; the finished clip is sent through this local server to OpenAI's transcription API, then the text appears in the input for review before sending. Recording stops automatically after 20 seconds. Without a key, the app uses the browser's built-in speech recognition if available; browser support and permission behavior vary. Audio is not stored by this app. A denied microphone permission, missing input device, or speech-service failure now shows a specific message.

## Review scenarios

1. **Multi-turn order lookup:** Say “Where is my order?” → `BK-1042` → `alex@example.com`. The backend calls `get_order_status` and displays the result.
2. **Action:** Say “I want to return my book” → `BK-2088` → `sam@example.com` → “Yes, please create it.” The backend creates fictional request `RET-2088` and shows the tool call. No real refund or email occurs.
3. **Clarification:** Say “I need help with a policy.” The agent asks which policy before using `get_policy`.
4. **Refund request:** Say “I want a refund” → `BK-4120` → `morgan@example.com` → “Yes, please create it.” The order was delivered and its return was received. The backend creates fictional review request `REF-4120`; no money moves.

`BK-2088 / sam@example.com` is delivered but has not been returned, so it works for the return workflow and demonstrates why a refund request is not yet eligible. The in-memory request records reset whenever the server restarts.

Sample orders are in `bookly.py`. The policy wording and action rules are also there. `agent.py` holds orchestration and the agent instructions; `server.py` exposes `/api/chat`. The scripted fallback exists only so reviewers can try the interface without an API account. It is not an LLM.

## Check

```bash
python3 -m unittest discover -s tests
```

## GitHub

Create an empty GitHub repository and, from this directory, run:

```bash
git init
git add .
git commit -m "Build Bookly support agent prototype"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/bookly-support.git
git push -u origin main
```

The repository contains the complete workspace needed to run locally. GitHub stores the code; it does not itself serve the Python backend. Keep API keys in local environment variables, never in Git.
