import unittest
import os
import json
from openai import OpenAI

class TestOpenAI(unittest.TestCase):
    def test_openai_api(self):
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'triangulum_config.json')
        with open(config_path, 'r') as f:
            config = json.load(f)

        client = OpenAI(api_key=config["llm"]["api_key"])

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": "Say this is a test",
                }
            ],
            model=config["llm"]["model"],
        )
        self.assertIn("test", chat_completion.choices[0].message.content)

if __name__ == '__main__':
    unittest.main()
