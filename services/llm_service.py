from openai import OpenAI
from config import MIMO_API_KEY, MIMO_BASE_URL, MIMO_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS


class LLMService:
    def __init__(self, api_key=None, base_url=None, model=None):
        self.client = OpenAI(
            api_key=api_key or MIMO_API_KEY,
            base_url=base_url or MIMO_BASE_URL,
        )
        self.model = model or MIMO_MODEL

    def chat(self, messages, temperature=None, max_tokens=None):
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature or LLM_TEMPERATURE,
            max_tokens=max_tokens or LLM_MAX_TOKENS,
        )
        return resp.choices[0].message.content

    def chain_of_thought(self, system_prompt, user_prompt):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self.chat(messages)
