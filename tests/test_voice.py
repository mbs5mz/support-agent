import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import transcribe_clip


class TranscriptionTests(unittest.TestCase):
    def test_recorded_audio_is_sent_as_multipart_and_transcript_returned(self):
        clip = b"demo-audio-bytes"
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-only-key"}), patch("server.urlopen", return_value=io.BytesIO(json.dumps({"text": "Where is my order?"}).encode())) as open_url:
            text = transcribe_clip(clip, "audio/webm")
        self.assertEqual(text, "Where is my order?")
        request = open_url.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.openai.com/v1/audio/transcriptions")
        self.assertIn(b"gpt-transcribe", request.data)
        self.assertIn(clip, request.data)
        self.assertIn(b'recording.webm', request.data)


if __name__ == "__main__":
    unittest.main()
