from openai import OpenAI
import os

class LLMClient:

    def __init__(self):

        self.client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key="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",
)

        self.model = "mistralai/Mistral-7B-Instruct-v0.2:featherless-ai"

    def generate(self, prompt):

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a log analysis assistant."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=200,
            temperature=0.3
        )

        # ✅ SAFE extraction
        return completion.choices[0].message.content