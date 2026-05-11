import json
from agents.base import BaseAgent

SYSTEM_PROMPT_DETAILED = """你是一位单片机（STM32/STC51/ESP32 等）领域的技术教程规划专家。

你的任务是将一个技术主题拆解为结构严谨的教程大纲。

要求：
1. 从「芯片基础 → 外设驱动 → 开发环境搭建 → 编程实战 → 调试优化」的单片机开发全栈角度拆解
2. 保证逻辑链完整：前置依赖 → 核心实现 → 调试验证
3. 每个章节需明确：标题、描述、关键知识点、涉及的代码语言
4. 章节数量根据目标字数合理分配（每章约 3000-5000 字）
5. 目标总字数：{word_count} 字

严格按以下 JSON 格式输出，不要输出任何其他内容：
{{{{
  "title": "教程主标题",
  "description": "教程简介（1-2句话）",
  "tags": ["标签1", "标签2"],
  "word_count": {word_count},
  "sections": [
    {{{{
      "id": 1,
      "title": "章节标题",
      "description": "本章要讲什么",
      "key_points": ["知识点1", "知识点2"],
      "code_language": "c/python/bash/cmake"
    }}}}
  ]
}}}}"""

SYSTEM_PROMPT_CONCISE = """你是一位单片机（STM32/STC51/ESP32 等）领域的技术教程规划专家。

你的任务是将一个技术主题拆解为精简实用的教程大纲。

要求：
1. 聚焦核心技术点和实现流程，省略基础概念和过多的原理铺垫
2. 结构紧凑：「环境准备 → 核心配置 → 关键代码 → 调试验证」
3. 每个章节只保留关键知识点，代码以核心片段为主
4. 章节数量控制在 3-5 章，每章目标字数约 1000-2000 字
5. 目标总字数：{word_count} 字

严格按以下 JSON 格式输出，不要输出任何其他内容：
{{{{
  "title": "教程主标题",
  "description": "教程简介（1-2句话）",
  "tags": ["标签1", "标签2"],
  "word_count": {word_count},
  "sections": [
    {{{{
      "id": 1,
      "title": "章节标题",
      "description": "本章要讲什么",
      "key_points": ["知识点1", "知识点2"],
      "code_language": "c/python/bash/cmake"
    }}}}
  ]
}}}}"""


class PlannerAgent(BaseAgent):
    def plan(self, topic: str, word_count: int = 5000, style: str = "detailed") -> dict:
        is_concise = style == "concise"

        if is_concise:
            # 精简模式：固定 3-5 章
            if word_count <= 1500:
                section_count = "2-3"
            elif word_count <= 3000:
                section_count = "3-4"
            else:
                section_count = "4-5"
            system = SYSTEM_PROMPT_CONCISE.format(word_count=word_count)
        else:
            # 详细模式：根据字数计算章节数量
            if word_count <= 2000:
                section_count = "3-4"
            elif word_count <= 5000:
                section_count = "5-6"
            elif word_count <= 8000:
                section_count = "6-7"
            elif word_count <= 12000:
                section_count = "7-8"
            else:
                section_count = "8-10"
            system = SYSTEM_PROMPT_DETAILED.format(word_count=word_count)

        user_prompt = f"请为以下技术主题规划教程大纲（章节数量：{section_count} 章）：\n\n{topic}"
        result = self.cot(system, user_prompt)
        # 提取 JSON（兼容 markdown 代码块包裹的情况）
        text = result.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]
        outline = json.loads(text.strip())
        outline["word_count"] = word_count
        return outline
