"""Bookly's fictional data and explicitly bounded support actions."""

ORDERS = {
    "BK-1042": {"email": "alex@example.com", "book": "The Midnight Library", "status": "Shipped", "detail": "Carrier scan: Chicago, IL. Estimated delivery: September 17.", "delivered": False},
    "BK-2088": {"email": "sam@example.com", "book": "Piranesi", "status": "Delivered", "detail": "Delivered September 10.", "delivered": True, "return_received": False},
    "BK-3001": {"email": "jordan@example.com", "book": "Project Hail Mary", "status": "Processing", "detail": "Preparing to ship; no tracking number yet.", "delivered": False},
    "BK-4120": {"email": "morgan@example.com", "book": "The Atlas Six", "status": "Return received", "detail": "Delivered September 6; return received September 12.", "delivered": True, "return_received": True},
}

POLICIES = {
    "shipping": "Standard shipping usually takes 3–5 business days after dispatch. Expedited shipping usually takes 1–2 business days after dispatch. These are fictional demo policies.",
    "returns": "Books can be returned within 30 days of delivery if in original condition. Refunds go to the original payment method after the return is received. These are fictional demo policies.",
    "password": "To reset a password, use the Forgot password link on the sign-in page. Never share your password or reset link with support.",
}

RETURN_REQUESTS = {}
REFUND_REQUESTS = {}


def get_order_status(order_id: str, email: str) -> dict:
    order = ORDERS.get(order_id.strip().upper())
    if not order or order["email"].lower() != email.strip().lower():
        return {"error": "No matching order. Check the order number and email address."}
    return {"order_id": order_id.strip().upper(), "book": order["book"], "status": order["status"], "detail": order["detail"]}


def get_policy(topic: str) -> dict:
    if topic not in POLICIES:
        return {"error": "Unknown policy topic. Ask whether the customer means shipping, returns, or password reset."}
    return {"topic": topic, "policy": POLICIES[topic]}


def create_return_request(order_id: str, email: str) -> dict:
    result = get_order_status(order_id, email)
    if "error" in result:
        return result
    order_id = order_id.strip().upper()
    if not ORDERS[order_id]["delivered"]:
        return {"error": "This order has not been delivered, so a return request cannot be created yet."}
    request_id = f"RET-{order_id[3:]}"
    RETURN_REQUESTS[request_id] = {"order_id": order_id, "email": email.strip().lower()}
    return {"request_id": request_id, "status": "Created (demo only)", "next_step": "A return label would be emailed in a real system."}


def create_refund_request(order_id: str, email: str) -> dict:
    result = get_order_status(order_id, email)
    if "error" in result:
        return result
    order_id = order_id.strip().upper()
    if not ORDERS[order_id].get("return_received", False):
        return {"error": "A refund request can be created after the returned book is received. No return has been received for this order yet."}
    request_id = f"REF-{order_id[3:]}"
    REFUND_REQUESTS[request_id] = {"order_id": order_id, "email": email.strip().lower()}
    return {"request_id": request_id, "status": "Submitted for review (demo only)", "next_step": "No payment has been refunded."}


FUNCTIONS = {
    "get_order_status": get_order_status,
    "get_policy": get_policy,
    "create_return_request": create_return_request,
    "create_refund_request": create_refund_request,
}

TOOLS = [
    {"type": "function", "name": "get_order_status", "description": "Look up a fictional order after collecting both order ID and email.", "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}, "email": {"type": "string"}}, "required": ["order_id", "email"], "additionalProperties": False}, "strict": True},
    {"type": "function", "name": "get_policy", "description": "Read a fictional Bookly policy for shipping, returns, or password reset.", "parameters": {"type": "object", "properties": {"topic": {"type": "string", "enum": ["shipping", "returns", "password"]}}, "required": ["topic"], "additionalProperties": False}, "strict": True},
    {"type": "function", "name": "create_return_request", "description": "Create a fictional return request only after collecting order ID and email and confirming the customer wants a return.", "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}, "email": {"type": "string"}}, "required": ["order_id", "email"], "additionalProperties": False}, "strict": True},
    {"type": "function", "name": "create_refund_request", "description": "Submit a fictional refund review request only after collecting order ID and email, verifying that the return was received, and getting explicit customer confirmation. This does not issue a refund.", "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}, "email": {"type": "string"}}, "required": ["order_id", "email"], "additionalProperties": False}, "strict": True},
]
