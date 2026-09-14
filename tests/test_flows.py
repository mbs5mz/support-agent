import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent import respond_demo
from bookly import REFUND_REQUESTS, RETURN_REQUESTS, create_refund_request


class DemoFlows(unittest.TestCase):
    def test_order_multiturn(self):
        history = [{"role": "user", "content": "Where is my order?"}]
        answer, calls = respond_demo(history)
        self.assertIn("order number", answer)
        self.assertFalse(calls)
        history += [{"role": "assistant", "content": answer}, {"role": "user", "content": "BK-1042"}]
        answer, calls = respond_demo(history)
        self.assertIn("email", answer)
        self.assertFalse(calls)
        history += [{"role": "assistant", "content": answer}, {"role": "user", "content": "alex@example.com"}]
        answer, calls = respond_demo(history)
        self.assertIn("shipped", answer)
        self.assertEqual(calls[0]["tool"], "get_order_status")

    def test_return_requires_confirmation(self):
        history = [{"role": "user", "content": "I want to return BK-2088, sam@example.com"}]
        answer, calls = respond_demo(history)
        self.assertIn("Would you like", answer)
        self.assertEqual(calls[0]["tool"], "get_order_status")
        self.assertFalse(RETURN_REQUESTS)
        history += [{"role": "assistant", "content": answer}, {"role": "user", "content": "Yes, please create it"}]
        answer, calls = respond_demo(history)
        self.assertIn("RET-2088", answer)
        self.assertEqual(calls[0]["tool"], "create_return_request")

    def test_ambiguous_policy(self):
        answer, calls = respond_demo([{"role": "user", "content": "I need help with a policy"}])
        self.assertIn("shipping", answer)
        self.assertFalse(calls)

    def test_switch_from_order_to_policy_and_return(self):
        history = [{"role": "user", "content": "Where is BK-2088? My email is sam@example.com"}]
        answer, calls = respond_demo(history)
        self.assertEqual(calls[0]["tool"], "get_order_status")
        history += [{"role": "assistant", "content": answer}, {"role": "user", "content": "What is your shipping policy?"}]
        answer, calls = respond_demo(history)
        self.assertIn("Standard shipping", answer)
        self.assertEqual(calls[0]["tool"], "get_policy")
        history += [{"role": "assistant", "content": answer}, {"role": "user", "content": "I want to return my book"}]
        answer, calls = respond_demo(history)
        self.assertIn("Would you like", answer)
        self.assertEqual(calls[0]["tool"], "get_order_status")
        history += [{"role": "assistant", "content": answer}, {"role": "user", "content": "No thanks"}]
        answer, calls = respond_demo(history)
        self.assertIn("haven't created", answer)
        self.assertFalse(calls)

    def test_return_policy_after_order_does_not_start_return(self):
        history = [
            {"role": "user", "content": "Where is BK-1042, alex@example.com?"},
            {"role": "assistant", "content": "Order BK-1042 is shipped."},
            {"role": "user", "content": "What is your return policy?"},
        ]
        answer, calls = respond_demo(history)
        self.assertIn("30 days", answer)
        self.assertEqual(calls[0]["tool"], "get_policy")

    def test_refund_requires_received_return_and_confirmation(self):
        history = [{"role": "user", "content": "I want a refund for BK-4120, morgan@example.com"}]
        answer, calls = respond_demo(history)
        self.assertIn("create a refund request?", answer)
        self.assertEqual(calls[0]["tool"], "get_order_status")
        self.assertFalse(REFUND_REQUESTS)
        history += [{"role": "assistant", "content": answer}, {"role": "user", "content": "Yes, please create it"}]
        answer, calls = respond_demo(history)
        self.assertIn("REF-4120", answer)
        self.assertIn("No payment has been refunded", answer)
        self.assertEqual(calls[0]["tool"], "create_refund_request")

    def test_refund_rejected_before_return_received(self):
        history = [{"role": "user", "content": "I want a refund for BK-2088, sam@example.com"}]
        answer, calls = respond_demo(history)
        self.assertIn("not been received", answer)
        self.assertEqual(calls[0]["tool"], "get_order_status")
        self.assertIn("error", create_refund_request("BK-2088", "sam@example.com"))


if __name__ == "__main__":
    unittest.main()
