from services.llm_service import LLMService


class BaseAgent:
    def __init__(self, llm=None):
        self.llm = llm or LLMService()

    def chat(self, messages, **kwargs):
        return self.llm.chat(messages, **kwargs)

    def cot(self, system_prompt, user_prompt):
        return self.llm.chain_of_thought(system_prompt, user_prompt)
