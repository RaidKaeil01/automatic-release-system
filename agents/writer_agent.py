import json
import re
from agents.base import BaseAgent

SYSTEM_PROMPT_DETAILED = """你是一位单片机（STM32/STC51/ESP32 等）领域的高级技术教程作者。

你的任务是根据教程大纲，逐章节编写高质量的 Markdown 教程内容。

写作要求：
1. 每章节需包含：原理讲解、寄存器或 HAL 库配置说明、完整可运行的代码、代码注释、运行结果说明
2. 文风专业但易懂，适合有一定单片机基础的开发者
3. 内容要充实详细，对每个知识点进行充分展开

标题格式（严格遵守）：
- 整篇文档的大标题用 ##（二级标题）
- 每个章节标题用 ###（三级标题）
- 章节内的子节用 ####（四级标题）
- 子节内的小节用 #####（五级标题）
- 绝对不要使用 #（一级标题），因为 CSDN 文章标题已经是一级标题

代码块格式（严格遵守）：
- 代码块使用三个反引号包裹，不要标注语言（不要写 ```c，只写 ```）
- 代码块必须顶格写，不要缩进（即使在列表项内也不缩进）
- 代码块前后必须各留一个空行
- 代码块内不要使用 | 字符来画 ASCII 表格（CSDN 会误解析为 Markdown 表格）

表格格式（严格遵守）：
- 如果需要表格，使用标准 Markdown 表格语法
- 表格分隔行只用 ---，不要用 :--- 或 ---:（不支持对齐语法）
- 表格单元格内容不要包含 | 字符

一致性保障（关键）：
- 你将收到「全局配置上下文」，包含芯片型号、内核版本、工具链版本等
- 所有章节中引用的硬件型号、软件版本、变量名必须与全局配置一致
- 后续章节可引用前序章节定义的变量和配置

输出要求：
- 只输出 Markdown 正文，不要输出 JSON 或其他格式
- 每个章节以 ### 开头"""

SYSTEM_PROMPT_CONCISE = """你是一位单片机（STM32/STC51/ESP32 等）领域的技术教程作者。

你的任务是根据教程大纲，编写精简实用的 Markdown 教程内容。

写作要求：
1. 聚焦关键技术点和实现流程，省略过多的原理铺垫
2. 代码以核心片段为主，附简要注释即可，不需要逐行解释
3. 每个知识点直击要点，用最少的文字传达最核心的信息
4. 适合有基础的开发者快速上手

标题格式（严格遵守）：
- 整篇文档的大标题用 ##（二级标题）
- 每个章节标题用 ###（三级标题）
- 章节内的子节用 ####（四级标题）
- 绝对不要使用 #（一级标题），因为 CSDN 文章标题已经是一级标题

代码块格式（严格遵守）：
- 代码块使用三个反引号包裹，不要标注语言（不要写 ```c，只写 ```）
- 代码块必须顶格写，不要缩进（即使在列表项内也不缩进）
- 代码块前后必须各留一个空行

输出要求：
- 只输出 Markdown 正文，不要输出 JSON 或其他格式
- 每个章节以 ### 开头"""


class WriterAgent(BaseAgent):
    def _build_context(self, outline: dict) -> str:
        total_words = outline.get("word_count", 5000)
        section_count = len(outline["sections"])
        words_per_section = max(1500, total_words // section_count)
        ctx_parts = [
            f"教程标题：{outline['title']}",
            f"教程简介：{outline['description']}",
            f"标签：{', '.join(outline.get('tags', []))}",
            f"总目标字数：{total_words} 字（共 {section_count} 章，每章约 {words_per_section} 字）",
            "",
            "章节规划：",
        ]
        for s in outline["sections"]:
            ctx_parts.append(f"  第{s['id']}章：{s['title']} - {s['description']}")
            ctx_parts.append(f"    关键知识点：{', '.join(s['key_points'])}")
        return "\n".join(ctx_parts)

    def write(self, outline: dict, style: str = "detailed") -> str:
        is_concise = style == "concise"
        system_prompt = SYSTEM_PROMPT_CONCISE if is_concise else SYSTEM_PROMPT_DETAILED
        context = self._build_context(outline)
        all_markdown = []

        total_words = outline.get("word_count", 5000)
        section_count = len(outline["sections"])
        words_per_section = max(500 if is_concise else 1500, total_words // section_count)

        for i, section in enumerate(outline["sections"]):
            extra = ""
            if i == 0:
                extra = "\n- 注意：不要重复输出教程大标题（## 标题），直接从 ### 章节标题开始写"

            if is_concise:
                word_req = f"- 字数要求：本章目标字数约 {words_per_section} 字，内容精简，聚焦核心技术点"
            else:
                word_req = f"- 字数要求：本章目标字数约 {words_per_section} 字（不少于 {int(words_per_section * 0.7)} 字），内容要充实详细"

            user_prompt = f"""{context}

---

请编写第{section['id']}章：{section['title']}

本章要求：
- 主题：{section['description']}
- 关键知识点：{', '.join(section['key_points'])}
- 主要代码语言：{section.get('code_language', 'bash')}
- 标题层级：章节标题用 ###，子节用 ####，子子节用 #####
{word_req}{extra}

请直接输出本章的 Markdown 内容。"""

            section_md = self.cot(system_prompt, user_prompt)
            all_markdown.append(section_md.strip())

        # 组装完整文档（## 为文档大标题，因为 CSDN 文章标题已经是一级标题）
        header = f"## {outline['title']}\n\n{outline['description']}\n\n---\n\n"
        body = "\n\n---\n\n".join(all_markdown)

        # 去掉第一个章节开头可能重复的文档标题
        title_pattern = rf"^##\s+{re.escape(outline['title'])}\s*\n"
        body = re.sub(title_pattern, "", body, count=1)

        return header + body

    def write_single(self, outline: dict, section_id: int, style: str = "detailed") -> str:
        """单独生成某一章，用于调试或增量更新"""
        section = next(s for s in outline["sections"] if s["id"] == section_id)
        is_concise = style == "concise"
        system_prompt = SYSTEM_PROMPT_CONCISE if is_concise else SYSTEM_PROMPT_DETAILED
        context = self._build_context(outline)
        total_words = outline.get("word_count", 5000)
        section_count = len(outline["sections"])
        words_per_section = max(500 if is_concise else 1500, total_words // section_count)

        if is_concise:
            word_req = f"- 字数要求：本章目标字数约 {words_per_section} 字，内容精简，聚焦核心技术点"
        else:
            word_req = f"- 字数要求：本章目标字数约 {words_per_section} 字（不少于 {int(words_per_section * 0.7)} 字），内容要充实详细"

        user_prompt = f"""{context}

---

请编写第{section['id']}章：{section['title']}

本章要求：
- 主题：{section['description']}
- 关键知识点：{', '.join(section['key_points'])}
- 主要代码语言：{section.get('code_language', 'bash')}
- 标题层级：章节标题用 ###，子节用 ####，子子节用 #####
{word_req}

请直接输出本章的 Markdown 内容。"""
        return self.cot(system_prompt, user_prompt).strip()
