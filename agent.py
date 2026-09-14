"""Conversation orchestration: OpenAI Responses API or deterministic demo mode."""

import json
import os
import re
from urllib.request import Request, urlopen

from bookly import FUNCTIONS, TOOLS

INSTRUCTIONS = """You are Bookly's customer support agent. Bookly and all records are fictional.
Keep replies concise, warm, and lightly upbeat, like a helpful bookseller. Use natural phrases such as "Happy to help" or "I found it" where they fit; avoid excessive exclamation points. Never invent order status or policy details; use tools.
For an order lookup, collect both order ID and email before calling get_order_status.
When asking for an order number, do not suggest a particular sample order; direct the user to the Demo orders panel if helpful.
For a return, collect both fields and explicit confirmation before calling create_return_request.
For a refund, collect both fields, check order status, explain that a returned book must have been received, and ask for explicit confirmation before calling create_refund_request. A request is only submitted for review; no money moves.
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
                previous_answer = next((turn["content"].lower() for turn in reversed(history[:-1]) if turn["role"] == "assistant"), "")
                confirmed = history[-1]["content"].strip().lower() in ("yes", "yes please", "please do", "go ahead", "create it", "yes, please create it", "submit it", "yes, submit it")
                request_kind = "return" if name == "create_return_request" else "refund"
                pending_request = re.search(rf"\b(create|submit) (a |the )?{request_kind} request\b", previous_answer)
                if name in ("create_return_request", "create_refund_request") and not (confirmed and pending_request):
                    result = {"error": "Ask the customer to confirm this specific request first."}
                else:
                    result = FUNCTIONS[name](**args) if name in FUNCTIONS else {"error": "Unknown tool"}
            except (ValueError, TypeError, KeyError) as error:
                result = {"error": f"Invalid tool arguments: {error}"}
            activity.append({"tool": name, "arguments": args, "result": result})
            items.append({"type": "function_call_output", "call_id": call["call_id"], "output": json.dumps(result)})
    return "I couldn't finish the lookup. Please try again.", activity


def respond_demo(history: list) -> tuple[str, list]:
    """Predictable fallback for reviewers without an API key; not presented as an LLM."""
    latest = history[-1]["content"].lower()
    previous_answer = next((turn["content"].lower() for turn in reversed(history[:-1]) if turn["role"] == "assistant"), "")
    user_text = " ".join(turn["content"] for turn in history if turn["role"] == "user")
    order = re.search(r"\bBK-\d{4}\b", user_text, re.I)
    email = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", user_text)

    # Route new requests from the current turn. Earlier turns only supply missing fields.
    policy_topic = next((topic for topic in ("shipping", "returns", "password") if topic in latest or (topic == "password" and "reset" in latest)), None)
    if "return policy" in latest or "refund policy" in latest or "returns" in latest:
        policy_topic = "returns"
    policy_request = "policy" in latest or "shipping" in latest or "password" in latest or "reset" in latest or "returns" in latest
    refund_request = bool(re.search(r"\brefund\b", latest)) and not policy_request
    return_request = bool(re.search(r"\breturn\b", latest)) and not policy_request
    order_request = any(word in latest for word in ("order", "package", "tracking", "where is", "where's", "status"))
    confirming_return = "create a return request?" in previous_answer and latest.strip() in ("yes", "yes please", "please do", "go ahead", "create it", "yes, please create it")
    declining_return = "create a return request?" in previous_answer and latest.strip() in ("no", "no thanks", "cancel")
    confirming_refund = "create a refund request?" in previous_answer and latest.strip() in ("yes", "yes please", "please do", "go ahead", "create it", "yes, please create it", "submit it", "yes, submit it")
    declining_refund = "create a refund request?" in previous_answer and latest.strip() in ("no", "no thanks", "cancel")

    if declining_return:
        return "No problem! I haven't created a return request. Let me know if you'd like help with anything else.", []
    if declining_refund:
        return "No problem! I haven't created a refund request. I'm here if you need anything else.", []
    if policy_request:
        if not policy_topic:
            return "Happy to help! Do you mean shipping, returns, or password reset?", []
        result = FUNCTIONS["get_policy"](policy_topic)
        return f"Of course! {result['policy']}", [{"tool": "get_policy", "arguments": {"topic": policy_topic}, "result": result}]

    if refund_request:
        intent = "refund"
    elif return_request:
        intent = "return"
    elif order_request:
        intent = "order"
    elif confirming_return:
        intent = "return_confirmed"
    elif confirming_refund:
        intent = "refund_confirmed"
    elif any(prompt in previous_answer for prompt in ("what is your order number?", "what email address was used")):
        # A bare ID or email continues the question the agent just asked.
        prior_requests = [turn["content"].lower() for turn in history[:-1] if turn["role"] == "user"]
        prior_intent = next((text for text in reversed(prior_requests) if re.search(r"\b(return|refund|order|tracking|status)\b", text) and "policy" not in text), "")
        intent = "refund" if "refund" in prior_intent else "return" if "return" in prior_intent else "order"
    else:
        return "I'm happy to help! Is this about an order, a return, a refund, shipping, or password reset?", []

    if intent in ("return", "return_confirmed", "refund", "refund_confirmed", "order"):
        if not order:
            return "Happy to look into that! What is your order number? You can find the sample options in the Demo orders panel.", []
        if not email:
            return "Thanks! What email address was used for that order?", []
        if intent in ("return", "return_confirmed"):
            if intent != "return_confirmed":
                result = FUNCTIONS["get_order_status"](order.group(), email.group())
                activity = [{"tool": "get_order_status", "arguments": {"order_id": order.group(), "email": email.group()}, "result": result}]
                if "error" in result:
                    return result["error"], activity
                return f"I found it! {result['book']} is marked {result['status'].lower()}. Would you like me to create a return request?", activity
            result = FUNCTIONS["create_return_request"](order.group(), email.group())
            activity = [{"tool": "create_return_request", "arguments": {"order_id": order.group(), "email": email.group()}, "result": result}]
            return (result.get("error") or f"All set! Demo return request {result['request_id']} was created. {result['next_step']}"), activity
        if intent in ("refund", "refund_confirmed"):
            if intent != "refund_confirmed":
                result = FUNCTIONS["get_order_status"](order.group(), email.group())
                activity = [{"tool": "get_order_status", "arguments": {"order_id": order.group(), "email": email.group()}, "result": result}]
                if "error" in result:
                    return result["error"], activity
                if result["status"] != "Return received":
                    return "I found the order! Its returned book has not been received yet, so I can't submit a refund request until it arrives.", activity
                return f"Good news, I found {result['book']} and its return was received. Would you like me to create a refund request? This only submits it for review.", activity
            result = FUNCTIONS["create_refund_request"](order.group(), email.group())
            activity = [{"tool": "create_refund_request", "arguments": {"order_id": order.group(), "email": email.group()}, "result": result}]
            return (result.get("error") or f"All set! Demo refund request {result['request_id']} was submitted for review. {result['next_step']}"), activity
        result = FUNCTIONS["get_order_status"](order.group(), email.group())
        activity = [{"tool": "get_order_status", "arguments": {"order_id": order.group(), "email": email.group()}, "result": result}]
        return (result.get("error") or f"I found it! Order {result['order_id']} for {result['book']} is {result['status'].lower()}. {result['detail']}"), activity


def respond(history: list) -> tuple[str, list, str]:
    if os.getenv("OPENAI_API_KEY"):
        answer, activity = respond_ai(history)
        return answer, activity, "OpenAI API"
    answer, activity = respond_demo(history)
    return answer, activity, "Scripted demo"
