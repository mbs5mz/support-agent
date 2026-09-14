import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent import respond_demo
from bookly import RETURN_REQUESTS


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
        self.assertIn("whether", answer)
        self.assertFalse(calls)


if __name__ == "__main__":
    unittest.main()
