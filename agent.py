"""Conversation orchestration: OpenAI Responses API or deterministic demo mode."""

import json
import os
import re
from urllib.request import Request, urlopen

from bookly import FUNCTIONS, TOOLS

INSTRUCTIONS = """You are Bookly's customer support agent. Bookly and all records are fictional.
Keep replies concise and friendly. Never invent order status or policy details; use tools.
For an order lookup, collect both order ID and email before calling get_order_status.
For a return, collect both fields and explicit intent to create a request before calling create_return_request.
If a request is ambiguous, ask one focused clarifying question before answering or using a tool.
Never ask for a password or password-reset link. Do not claim a real refund or email was sent.
If a tool reports an error, explain it without guessing.
"""


def call_responses(input_items: list, model: str) -> dict:
    body = json.dumps({"model": model, "instructions": INSTRUCTIONS, "input": input_items, "tools": TOOLS, "store": False}).encode()
    request = Request("https://api.openai.com/v1/responses", data=body, headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"})
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def respond_ai(history: list) -> tuple[str, list]:
    items = [{"role": turn["role"], "content": turn["content"]} for turn in history]
    activity = []
    model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    for _ in range(4):
        response = call_responses(items, model)
        output = response.get("output", [])
        items.extend(output)
        calls = [item for item in output if item.get("type") == "function_call"]
        if not calls:
            text = "".join(part.get("text", "") for item in output if item.get("type") == "message" for part in item.get("content", []) if part.get("type") == "output_text")
            return text or "I couldn't complete that response. Please try again.", activity
        for call in calls:
            name = call.get("name")
            args = {}
            try:
                args = json.loads(call.get("arguments", "{}"))
                if name == "create_return_request" and not any(phrase in history[-1]["content"].lower() for phrase in ("yes", "create", "go ahead", "please do")):
                    result = {"error": "Ask the customer to confirm creating the return request first."}
                else:
                    result = FUNCTIONS[name](**args) if name in FUNCTIONS else {"error": "Unknown tool"}
            except (ValueError, TypeError, KeyError) as error:
                result = {"error": f"Invalid tool arguments: {error}"}
            activity.append({"tool": name, "arguments": args, "result": result})
            items.append({"type": "function_call_output", "call_id": call["call_id"], "output": json.dumps(result)})
    return "I couldn't finish the lookup. Please try again.", activity


def respond_demo(history: list) -> tuple[str, list]:
    """Predictable fallback for reviewers without an API key; not presented as an LLM."""
    user_text = " ".join(turn["content"] for turn in history if turn["role"] == "user")
    latest = history[-1]["content"].lower()
    order = re.search(r"\bBK-\d{4}\b", user_text, re.I)
    email = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", user_text)
    wants_return = any(word in user_text.lower() for word in ("return", "refund"))
    wants_order = any(word in user_text.lower() for word in ("order", "package", "tracking", "where is", "where's", "status"))
    if wants_return or wants_order:
        if not order:
            return "What is your order number? It looks like BK-1042.", []
        if not email:
            return "What email address was used for that order?", []
        if wants_return:
            if latest.strip() in ("no", "no thanks", "cancel"):
                return "Okay, I haven't created a return request.", []
            if not any(phrase in latest for phrase in ("yes", "create", "please do", "go ahead")):
                result = FUNCTIONS["get_order_status"](order.group(), email.group())
                activity = [{"tool": "get_order_status", "arguments": {"order_id": order.group(), "email": email.group()}, "result": result}]
                if "error" in result:
                    return result["error"], activity
                return f"I found {result['book']} ({result['status']}). Would you like me to create a return request?", activity
            result = FUNCTIONS["create_return_request"](order.group(), email.group())
            activity = [{"tool": "create_return_request", "arguments": {"order_id": order.group(), "email": email.group()}, "result": result}]
            return (result.get("error") or f"Demo return request {result['request_id']} created. {result['next_step']}"), activity
        result = FUNCTIONS["get_order_status"](order.group(), email.group())
        activity = [{"tool": "get_order_status", "arguments": {"order_id": order.group(), "email": email.group()}, "result": result}]
        return (result.get("error") or f"Order {result['order_id']} for {result['book']} is {result['status'].lower()}. {result['detail']}"), activity
    topics = [topic for topic in ("shipping", "returns", "password") if topic in latest or (topic == "password" and "reset" in latest)]
    if len(topics) != 1:
        return "Can you tell me whether you mean shipping, returns, or password reset?", []
    result = FUNCTIONS["get_policy"](topics[0])
    return result["policy"], [{"tool": "get_policy", "arguments": {"topic": topics[0]}, "result": result}]


def respond(history: list) -> tuple[str, list, str]:
    if os.getenv("OPENAI_API_KEY"):
        answer, activity = respond_ai(history)
        return answer, activity, "OpenAI API"
    answer, activity = respond_demo(history)
    return answer, activity, "Scripted demo"
