"""Bookly's lightweight AOP catalog, traces, and simulated Duet workspace."""

import re


AOPS = [
    {
        "id": "order-status",
        "name": "Track an order",
        "description": "Verify a customer and share the latest fulfillment status.",
        "status": "Live",
        "version": "v3",
        "entry_conditions": "Use when a customer asks where an order is, whether it shipped, or requests tracking details.",
        "tools": ["get_order_status"],
        "guardrails": ["Collect both order ID and email before lookup.", "Never infer a status without the order tool."],
        "steps": [
            {"type": "instruction", "title": "Identify the order", "body": "Ask for the order number if it is missing. Do not suggest a specific sample order."},
            {"type": "instruction", "title": "Verify the customer", "body": "Ask for the email used for the order if it is missing."},
            {"type": "tool", "title": "Look up fulfillment", "body": "Call get_order_status with the verified order ID and email."},
            {"type": "condition", "title": "Respond from the result", "body": "Share status and delivery detail. If no order matches, ask the customer to check both fields."},
        ],
        "test_prompt": "Where is my order?",
    },
    {
        "id": "book-return",
        "name": "Create a book return",
        "description": "Verify eligibility, obtain confirmation, and open a return request.",
        "status": "Live",
        "version": "v5",
        "entry_conditions": "Use when a customer wants to send back a delivered book or start a return.",
        "tools": ["get_order_status", "create_return_request"],
        "guardrails": ["Only delivered orders are eligible.", "Require explicit confirmation before creating a request.", "Do not claim a label was actually emailed."],
        "steps": [
            {"type": "instruction", "title": "Collect identifiers", "body": "Collect the order ID and the email used at checkout."},
            {"type": "tool", "title": "Check the order", "body": "Call get_order_status and explain the current state."},
            {"type": "condition", "title": "Check eligibility", "body": "Continue only if the book was delivered. Otherwise explain why a return cannot start yet."},
            {"type": "instruction", "title": "Confirm the action", "body": "Ask whether the customer wants a return request. Accept a natural affirmative such as yes, sure, or go ahead."},
            {"type": "tool", "title": "Create the request", "body": "Call create_return_request and clearly label the result as a demo action."},
        ],
        "test_prompt": "I want to return my book",
    },
    {
        "id": "refund-review",
        "name": "Submit a refund review",
        "description": "Check that a return arrived before submitting a refund for review.",
        "status": "Live",
        "version": "v4",
        "entry_conditions": "Use when a customer asks for money back or requests a refund after returning a book.",
        "tools": ["get_order_status", "create_refund_request"],
        "guardrails": ["A returned book must be received first.", "Require explicit confirmation.", "Never state that money moved."],
        "steps": [
            {"type": "instruction", "title": "Collect identifiers", "body": "Collect the order ID and customer email."},
            {"type": "tool", "title": "Verify return state", "body": "Call get_order_status and check for Return received."},
            {"type": "condition", "title": "Gate the request", "body": "If the return is not received, explain the requirement and stop."},
            {"type": "instruction", "title": "Confirm submission", "body": "Explain that this submits a review request only, then ask for confirmation."},
            {"type": "tool", "title": "Submit for review", "body": "Call create_refund_request. Never claim the refund was issued."},
        ],
        "test_prompt": "I want to request a refund",
    },
    {
        "id": "policy-help",
        "name": "Answer a policy question",
        "description": "Clarify the topic and answer from Bookly's approved policy source.",
        "status": "Live",
        "version": "v2",
        "entry_conditions": "Use for shipping, returns, or password-reset policy questions that do not require an account action.",
        "tools": ["get_policy"],
        "guardrails": ["Ask one focused question when the topic is unclear.", "Never ask for a password or reset link."],
        "steps": [
            {"type": "condition", "title": "Disambiguate the topic", "body": "If the policy is unclear, ask whether the customer means shipping, returns, or password reset."},
            {"type": "tool", "title": "Load approved policy", "body": "Call get_policy with the selected topic."},
            {"type": "instruction", "title": "Answer concisely", "body": "Summarize only the returned policy and offer another relevant next step."},
        ],
        "test_prompt": "I need help with a policy",
    },
]

AOP_BY_ID = {aop["id"]: aop for aop in AOPS}


def select_aop(history: list, activity: list) -> dict:
    latest = history[-1]["content"].lower() if history else ""
    tool_names = [call.get("tool") for call in activity]
    if "create_refund_request" in tool_names or re.search(r"\brefund\b", latest):
        aop_id, reason = "refund-review", "The customer requested a refund or the refund tool ran."
    elif "create_return_request" in tool_names or (re.search(r"\breturn\b", latest) and "policy" not in latest):
        aop_id, reason = "book-return", "The customer asked to return a book or the return tool ran."
    elif "get_policy" in tool_names or any(word in latest for word in ("policy", "shipping", "password", "reset")):
        aop_id, reason = "policy-help", "The message is informational and matches an approved policy topic."
    elif "get_order_status" in tool_names or any(word in latest for word in ("order", "tracking", "package", "where is", "status")):
        aop_id, reason = "order-status", "The message asks for fulfillment information or triggered an order lookup."
    else:
        aop_id, reason = "policy-help", "No action workflow matched, so the agent used its clarification fallback."
    aop = AOP_BY_ID[aop_id]
    events = [{"kind": "aop", "label": f"Loaded {aop['name']}", "detail": reason}]
    for call in activity:
        result = call.get("result", {})
        events.append({
            "kind": "tool",
            "label": f"Called {call.get('tool', 'tool')}",
            "detail": result.get("error") or result.get("status") or result.get("detail") or "Tool returned successfully.",
        })
    if not activity:
        events.append({"kind": "decision", "label": "Waiting for customer input", "detail": "The procedure needs clarification or a required identifier before using a tool."})
    return {"aop_id": aop_id, "aop_name": aop["name"], "version": aop["version"], "reason": reason, "events": events}


def platform_summary() -> dict:
    return {
        "aops": AOPS,
        "metrics": [
            {"label": "Published AOPs", "value": "4", "change": "All healthy"},
            {"label": "Demo resolution", "value": "96%", "change": "+8 pts simulated"},
            {"label": "Tool success", "value": "96%", "change": "Last 30 runs"},
            {"label": "Needs review", "value": "2", "change": "Duet suggestions"},
        ],
        "recent_runs": [
            {"intent": "Order status", "aop": "Track an order", "outcome": "Resolved", "time": "2m ago"},
            {"intent": "Refund", "aop": "Submit a refund review", "outcome": "Guardrail", "time": "18m ago"},
            {"intent": "Return", "aop": "Create a book return", "outcome": "Resolved", "time": "34m ago"},
        ],
        "watchtower": {
            "metrics": [
                {"label": "Deflection rate", "value": "94%", "change": "+2.8 pts", "tone": "positive", "detail": "Resolved without a human handoff"},
                {"label": "Verified resolution", "value": "96%", "change": "+2.2 pts", "tone": "positive", "detail": "Outcome confirmed by tool or customer"},
                {"label": "Customer satisfaction", "value": "4.9", "change": "+0.2", "tone": "positive", "detail": "Simulated CSAT out of 5"},
                {"label": "Escalation rate", "value": "4%", "change": "-2.0 pts", "tone": "positive", "detail": "Transferred for human review"},
            ],
            "trend": [
                {"label": "Mon", "deflection": 92, "resolution": 94},
                {"label": "Tue", "deflection": 93, "resolution": 95},
                {"label": "Wed", "deflection": 94, "resolution": 96},
                {"label": "Thu", "deflection": 95, "resolution": 96},
                {"label": "Fri", "deflection": 94, "resolution": 97},
                {"label": "Sat", "deflection": 95, "resolution": 97},
                {"label": "Sun", "deflection": 95, "resolution": 97},
            ],
            "periods": {
                "7": {
                    "metrics": [
                        {"label": "Deflection rate", "value": "94%", "change": "+2.8 pts", "detail": "Resolved without a human handoff"},
                        {"label": "Verified resolution", "value": "96%", "change": "+2.2 pts", "detail": "Outcome confirmed by tool or customer"},
                        {"label": "Customer satisfaction", "value": "4.9", "change": "+0.2", "detail": "Simulated CSAT out of 5"},
                        {"label": "Escalation rate", "value": "4%", "change": "-2.0 pts", "detail": "Transferred for human review"},
                    ],
                    "trend": [
                        {"label": "Mon", "deflection": 92, "resolution": 94}, {"label": "Tue", "deflection": 93, "resolution": 95},
                        {"label": "Wed", "deflection": 94, "resolution": 96}, {"label": "Thu", "deflection": 95, "resolution": 96},
                        {"label": "Fri", "deflection": 94, "resolution": 97}, {"label": "Sat", "deflection": 95, "resolution": 97},
                        {"label": "Sun", "deflection": 95, "resolution": 97},
                    ],
                    "context": "Seven-day values are averages of the daily points shown below.",
                },
                "30": {
                    "metrics": [
                        {"label": "Deflection rate", "value": "90%", "change": "+5.0 pts", "detail": "Resolved without a human handoff"},
                        {"label": "Verified resolution", "value": "92%", "change": "+4.0 pts", "detail": "Outcome confirmed by tool or customer"},
                        {"label": "Customer satisfaction", "value": "4.7", "change": "+0.3", "detail": "Simulated CSAT out of 5"},
                        {"label": "Escalation rate", "value": "8%", "change": "-4.0 pts", "detail": "Transferred for human review"},
                    ],
                    "trend": [
                        {"label": "W1", "deflection": 86, "resolution": 88}, {"label": "W2", "deflection": 89, "resolution": 91},
                        {"label": "W3", "deflection": 91, "resolution": 93}, {"label": "Latest 7d", "deflection": 94, "resolution": 96},
                    ],
                    "context": "Thirty-day values average the four weekly points. Latest 7d matches the seven-day headline.",
                },
                "90": {
                    "metrics": [
                        {"label": "Deflection rate", "value": "85%", "change": "+9.0 pts to current", "detail": "Resolved without a human handoff"},
                        {"label": "Verified resolution", "value": "88%", "change": "+8.0 pts to current", "detail": "Outcome confirmed by tool or customer"},
                        {"label": "Customer satisfaction", "value": "4.4", "change": "+0.5 to current", "detail": "Simulated CSAT out of 5"},
                        {"label": "Escalation rate", "value": "12%", "change": "-8.0 pts to current", "detail": "Transferred for human review"},
                    ],
                    "trend": [
                        {"label": "Month 1", "deflection": 80, "resolution": 84},
                        {"label": "Month 2", "deflection": 85, "resolution": 88},
                        {"label": "Latest 30d", "deflection": 90, "resolution": 92},
                    ],
                    "context": "Ninety-day values average the three monthly points. Latest 30d matches the thirty-day headline.",
                },
            },
            "rubrics": [
                {"name": "Action confirmation", "score": 98, "flags": 1, "description": "Sensitive actions require a clear customer confirmation."},
                {"name": "Grounded answers", "score": 96, "flags": 2, "description": "Order and policy claims must come from an approved tool."},
                {"name": "Customer sentiment", "score": 91, "flags": 3, "description": "Detect frustration, confusion, or repeated questions."},
                {"name": "Policy compliance", "score": 100, "flags": 0, "description": "Never request passwords or claim money moved."},
            ],
            "queue": [
                {"id": "CV-1048", "category": "Sentiment", "intent": "Refund", "summary": "Customer repeated the eligibility question after the return had not arrived.", "severity": "Medium", "score": "2.8", "time": "12m ago"},
                {"id": "CV-1041", "category": "Grounding", "intent": "Shipping policy", "summary": "Answer required a clarification turn before the approved policy was loaded.", "severity": "Low", "score": "3.9", "time": "1h ago"},
                {"id": "CV-1033", "category": "Confirmation", "intent": "Return", "summary": "Customer used an indirect confirmation; request was correctly held for clarification.", "severity": "Medium", "score": "3.4", "time": "3h ago"},
                {"id": "CV-1027", "category": "Sentiment", "intent": "Order status", "summary": "Processing order had no tracking number and the customer expressed frustration.", "severity": "High", "score": "2.1", "time": "Yesterday"},
            ],
        },
        "resources": {
            "tools": [
                {"name": "get_order_status", "status": "Connected", "description": "Reads a fictional order after validating order ID and email.", "used_by": "3 AOPs"},
                {"name": "get_policy", "status": "Connected", "description": "Returns approved shipping, returns, or password-reset policy text.", "used_by": "1 AOP"},
                {"name": "create_return_request", "status": "Connected", "description": "Creates an in-memory return request for an eligible delivered order.", "used_by": "1 AOP"},
                {"name": "create_refund_request", "status": "Connected", "description": "Submits an in-memory refund review after a return is received.", "used_by": "1 AOP"},
            ],
            "knowledge": [
                {"name": "Shipping policy", "status": "Published", "description": "Standard and expedited shipping timeframes.", "used_by": "Updated in bookly.py"},
                {"name": "Returns and refunds", "status": "Published", "description": "Thirty-day return window and refund eligibility.", "used_by": "Updated in bookly.py"},
                {"name": "Password reset", "status": "Published", "description": "Safe reset instructions without collecting credentials.", "used_by": "Updated in bookly.py"},
            ],
            "guardrails": [
                {"name": "Verify before lookup", "status": "Active", "description": "Require both order ID and matching email before exposing order data.", "used_by": "Order workflows"},
                {"name": "Confirm before action", "status": "Active", "description": "Require a natural affirmative after the exact return or refund offer.", "used_by": "Return and refund"},
                {"name": "Refund eligibility", "status": "Active", "description": "Block refund review until the returned book is received.", "used_by": "Refund review"},
                {"name": "Credential safety", "status": "Active", "description": "Never request a password or password-reset link.", "used_by": "All conversations"},
            ],
        },
    }


def duet_assist(prompt: str, aop_id: str = "") -> dict:
    text = prompt.lower().strip()
    aop = AOP_BY_ID.get(aop_id)
    if any(word in text for word in ("test", "simulate", "edge case")):
        target = aop or AOP_BY_ID["refund-review"]
        return {
            "answer": f"I generated a compact simulation suite for {target['name']}. The happy path passes, and two edge cases verify that Bookly stops before a sensitive action.",
            "artifact": {
                "kind": "Simulation suite",
                "title": f"{target['name']} · pre-release check",
                "summary": "4 of 4 scenarios passed",
                "items": [
                    {"label": "Happy path", "detail": "Valid identifiers and explicit confirmation", "status": "Pass"},
                    {"label": "Missing email", "detail": "Agent asks one focused follow-up", "status": "Pass"},
                    {"label": "Ineligible order", "detail": "Procedure stops before the action tool", "status": "Pass"},
                    {"label": "Topic switch", "detail": "Agent reroutes to the new AOP", "status": "Pass"},
                ],
            },
            "suggestions": ["Open the AOP", "Draft a stricter guardrail", "Compare another workflow"],
        }
    if any(word in text for word in ("draft", "create", "write", "aop")):
        return {
            "answer": "I drafted an AOP for damaged-book replacements using Bookly's existing verification and confirmation patterns. It is staged for review and is not connected to a live tool.",
            "artifact": {
                "kind": "Draft AOP",
                "title": "Replace a damaged book",
                "summary": "Draft · 5 sections · human review required",
                "items": [
                    {"label": "Entry condition", "detail": "Customer reports a delivered book arrived damaged", "status": "Draft"},
                    {"label": "Verify", "detail": "Collect order ID and email, then look up the order", "status": "Draft"},
                    {"label": "Assess", "detail": "Ask for a concise description; escalate suspected abuse", "status": "Draft"},
                    {"label": "Confirm", "detail": "Ask before opening a replacement request", "status": "Draft"},
                ],
            },
            "suggestions": ["Generate simulations", "Review required tools", "Add an escalation rule"],
        }
    if any(word in text for word in ("analy", "performance", "trend", "improve", "recommend")):
        return {
            "answer": "The largest simulated opportunity is refund eligibility. Customers often ask for a refund before Bookly has received the return. I recommend making that requirement explicit earlier and offering a return-status next step.",
            "artifact": {
                "kind": "Optimization report",
                "title": "Bookly support · workflow opportunities",
                "summary": "30 demo runs analyzed · 2 recommendations",
                "items": [
                    {"label": "Refund eligibility", "detail": "5 conversations stopped after the return-received guardrail", "status": "High impact"},
                    {"label": "Policy ambiguity", "detail": "3 conversations required an extra clarification turn", "status": "Medium"},
                    {"label": "Order verification", "detail": "No unsafe lookups observed", "status": "Healthy"},
                ],
            },
            "suggestions": ["Draft the refund update", "Generate regression tests", "Inspect failed conversations"],
        }
    return {
        "answer": "I can help analyze Bookly's demo performance, draft an AOP, or generate simulations. Choose a prompt below or ask about a specific workflow.",
        "artifact": None,
        "suggestions": ["Analyze recent performance", "Draft a damaged-book AOP", "Test the refund AOP"],
    }
