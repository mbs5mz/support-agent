# Bookly support agent demo

Bookly is a **fictional** online bookstore. This browser-based prototype handles order status, return and refund requests, and common policy questions. It also includes a lightweight agent-building workspace inspired by modern CX platforms: a dashboard, inspectable Agent Operating Procedures (AOPs), execution traces, Watchtower-style quality monitoring, and a simulated Duet-style optimization assistant. The backend uses Python's standard-library HTTP server; the frontend is plain HTML, CSS, and JavaScript. No package installation or database setup is needed.

## Start the demo

1. Download and extract the repository. Open a terminal in the extracted folder—the one containing `server.py`, `agent.py`, `bookly.py`, and `static/`.
2. Check that Python 3.9 or newer is installed: `python3 --version`. On Windows, use `py --version` if `python3` is unavailable.
3. Start the server:

   ```bash
   python3 server.py
   ```

   On Windows, `py server.py` is an alternative. Leave the terminal running. You should see `Bookly demo: http://localhost:8000`.

4. Open [http://localhost:8000](http://localhost:8000) in a browser. Start on **Overview**, inspect a procedure under **AOPs**, monitor simulated quality in **Watchtower**, ask the simulated builder a question under **Duet**, or open **Playground** to chat with the customer-facing agent. The Playground's **Demo data** tab lists sample credentials, while **Trace** shows the selected AOP and tool activity. The Tools, Knowledge, and Guardrails links under **Build** open their respective resource catalogs.

The app works immediately without an API key. Its status badge says **Scripted demo**: replies follow deterministic rules, so anyone can test the workflows, but this mode is not an LLM. Press **Reset conversation** to start a new chat and clear visible tool activity. To stop the server, press `Ctrl+C` in its terminal.

## Optional: use the OpenAI-backed agent

Set an API key in the **same terminal** before starting the server. No OpenAI Python package is required; the backend calls the Responses API directly with `urllib.request`.

macOS / Linux:

```bash
export OPENAI_API_KEY="your-api-key"
python3 server.py
```

Windows PowerShell:

```powershell
$env:OPENAI_API_KEY = "your-api-key"
py server.py
```

The badge says **OpenAI API** after the first reply. `OPENAI_MODEL` is optional and defaults to `gpt-5-mini`; set it in the terminal before launch if you want another model. API-backed chat and transcription require network access and may incur API charges. Keep the key in your local environment, never in the repository or browser code.

## Walk through the scenarios

Use the values below exactly as shown. They are fictional and are also listed in the browser's **Demo orders** panel.

| Order | Email | Starting state | Good scenario |
| --- | --- | --- | --- |
| `BK-1042` | `alex@example.com` | Shipped | Order status; return blocked before delivery |
| `BK-2088` | `sam@example.com` | Delivered, no return received | Return request; refund blocked |
| `BK-3001` | `jordan@example.com` | Processing | Order status; no tracking number yet |
| `BK-4120` | `morgan@example.com` | Return received | Refund review request |

Try these as separate conversations, using **Reset conversation** between them:

1. **Multi-turn lookup:** Send “Where is my order?” The agent asks for an order number; reply `BK-1042`. It then asks for the email; reply `alex@example.com`. The activity panel shows `get_order_status` and the shipped status.
2. **Return action:** Send “I want to return my book.” Supply `BK-2088` and `sam@example.com` when asked. After the agent offers to create a return request, reply `yes`, `sure`, or `go ahead`. The activity panel shows `create_return_request`; the fictional request ID is `RET-2088`.
3. **Clarification:** Send “I need help with a policy.” The agent asks whether you mean shipping, returns, or password reset. Reply “shipping” to see `get_policy` in the activity panel.
4. **Refund action:** Send “I want a refund.” Supply `BK-4120` and `morgan@example.com`, then confirm with `yes`. The agent submits fictional review request `REF-4120` via `create_refund_request`. **No money moves.**
5. **Guardrails and topic changes:** Try a wrong email, ask to return `BK-1042` before delivery, or request a refund for `BK-2088` before its return is received. After an order lookup, ask a shipping-policy question or start a return to check that the agent follows your new request.

The model-backed path may phrase questions differently, but the same sample data and Python tool rules apply. The scripted path is predictable and useful for a quick walkthrough without API access.

## Explore AOPs and Duet

The **AOPs** page exposes the four Bookly workflows as natural-language operating procedures. Select one to review its entry conditions, referenced tools, guardrails, and ordered steps. **Test in playground** carries its sample prompt into the customer chat. During a chat, the Trace panel explains which AOP was selected and records each tool call.

The **Duet** page simulates three agent-development tasks using deterministic Bookly demo data:

- Analyze recent workflow performance and produce an optimization report.
- Draft a new damaged-book AOP for human review.
- Generate a compact simulation suite for a selected AOP.

These outputs are illustrative and intentionally review-only: the demo does not autonomously publish workflow changes. This is an independent product simulation, not Decagon software or a connection to Decagon's platform.

## Monitor with Watchtower

The **Watchtower** page demonstrates an always-on QA and analytics workspace using fictional metrics and conversations. It includes deflection rate, verified resolution, simulated CSAT, escalation rate, separate outcome graphs, custom rubric health, and a filterable conversation review queue. Each headline is the average of the points plotted for that window. The windows also roll up consistently: the latest week in the 30-day graph equals the 7-day headline, and the latest month in the 90-day graph equals the 30-day headline. Together, the 90-day, 30-day, and 7-day views show performance improving as Bookly adds AOPs and policy coverage. No production conversations or customer data are collected.

## Voice input

With `OPENAI_API_KEY`, press the microphone once to start recording and again to stop (or wait for the 20-second limit). The server sends the clip to OpenAI's transcription API. Review the resulting text in the input box, then press **Send**. Without a key, the demo uses the browser's built-in speech recognition when available. Voice support depends on browser and microphone permissions; typing always works. The app does not save audio clips.

## What is stored and where

The browser sends conversation history with each chat request; **Reset conversation** clears that browser session. Sample orders, policies, and created request records live in Python memory in `bookly.py`. Restarting the server clears created return and refund requests. There is no persistent database, account login, real order connection, email delivery, or payment action. API-backed chat sets OpenAI response storage to `false`.

`server.py` serves the page and exposes `/api/chat`, `/api/platform`, `/api/duet`, `/api/config`, and optional `/api/transcribe`. `agent.py` contains the customer-agent instructions, conversation orchestration, and confirmation handling. `bookly.py` contains sample records and the four action tools. `agent_workspace.py` contains the AOP catalog, trace routing, Watchtower metrics, build resources, dashboard data, and simulated Duet artifacts. `static/` contains the browser UI.

## Troubleshooting and checks

- **The page does not load:** Confirm the terminal still shows the running server, that you started it from the folder containing `server.py`, and that the address is `http://localhost:8000` (not `https`). If port 8000 is already in use, stop the other process using it before starting this server.
- **The badge says Scripted demo:** `OPENAI_API_KEY` was not present in the server's environment when it started. Set it and restart the server.
- **An API request fails:** Check that the key is valid, the machine has internet access, and the chosen `OPENAI_MODEL` is available to the account. Restart without a key to use the scripted demo.
- **The microphone fails:** Allow microphone access for localhost in browser and system settings, check the input device, or type the question instead. Browser speech recognition is not supported everywhere.

To run the included automated checks from the repository folder:

```bash
python3 -m unittest discover -s tests
```
