import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent import pending_request_kind, respond_ai


class ConfirmationTests(unittest.TestCase):
    def test_plain_yes_completes_return_without_another_model_call(self):
        history = [
            {"role": "user", "content": "I'd like to return BK-2088. My email is sam@example.com."},
            {"role": "assistant", "content": "I found your delivered order. Shall I start the return for you?"},
            {"role": "user", "content": "yes"},
        ]
        with patch("agent.call_responses") as model_call:
            answer, activity = respond_ai(history)
        model_call.assert_not_called()
        self.assertIn("RET-2088", answer)
        self.assertEqual(activity[0]["tool"], "create_return_request")

    def test_natural_confirmation_completes_refund(self):
        history = [
            {"role": "user", "content": "Refund for BK-4120, morgan@example.com"},
            {"role": "assistant", "content": "The return was received. Would you like me to submit a refund request?"},
            {"role": "user", "content": "Sure, go ahead"},
        ]
        with patch("agent.call_responses") as model_call:
            answer, activity = respond_ai(history)
        model_call.assert_not_called()
        self.assertIn("REF-4120", answer)
        self.assertIn("No payment has been refunded", answer)
        self.assertEqual(activity[0]["tool"], "create_refund_request")

    def test_yes_after_unrelated_question_does_not_create_action(self):
        self.assertIsNone(pending_request_kind("Is that the order you meant?"))
        history = [
            {"role": "user", "content": "BK-2088 sam@example.com"},
            {"role": "assistant", "content": "Is that the order you meant?"},
            {"role": "user", "content": "yes"},
        ]
        model_response = {"output": [{"type": "message", "content": [{"type": "output_text", "text": "Thanks for confirming."}]}]}
        with patch("agent.call_responses", return_value=model_response) as model_call:
            answer, activity = respond_ai(history)
        model_call.assert_called_once()
        self.assertEqual(answer, "Thanks for confirming.")
        self.assertFalse(activity)


if __name__ == "__main__":
    unittest.main()
