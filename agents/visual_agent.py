import json
import re
from pathlib import Path
from agents.base import BaseAgent
from services.mermaid_service import MermaidService
from services.jimeng_service import JimengService

ANALYSIS_PROMPT = """你是一位技术文档视觉设计专家。

分析以下 Markdown 教程内容，识别需要配图的位置（仅分析文本，已有配图的位置不要重复）。

对每个需要配图的位置，输出：
1. 插入位置（在哪个章节标题之后）
2. 图表类型：ai_image（所有图表都用 AI 图片生成）
3. 图表内容描述和英文提示词

严格按以下 JSON 数组格式输出：
[
  {
    "position": "章节标题或段落关键词",
    "type": "ai_image",
    "description": "描述要生成什么图片",
    "prompt": "英文提示词，用于 AI 图片生成，描述技术架构图或示意图"
  }
]

只输出 JSON，不要输出其他内容。
注意：不要输出 mermaid 类型，所有图表都用 ai_image 类型。"""


class VisualAgent(BaseAgent):
    def __init__(self, output_dir: str, llm=None):
        super().__init__(llm)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.mermaid = MermaidService()
        self.jimeng = JimengService()

    def _render_existing_mermaid(self, markdown: str) -> str:
        """将 markdown 中已有的 mermaid 代码块渲染为 PNG 图片"""
        pattern = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)
        matches = list(pattern.finditer(markdown))
        if not matches:
            return markdown

        rendered = markdown
        for i, match in enumerate(matches):
            code = match.group(1).strip()
            img_filename = f"mermaid_{i}.png"
            img_path = str(self.output_dir / img_filename)
            try:
                self.mermaid.render(code, img_path)
                img_ref = f"![mermaid diagram](images/{img_filename})"
                rendered = rendered.replace(match.group(0), img_ref, 1)
            except Exception as e:
                # 渲染失败保留原始代码块
                print(f"Mermaid 渲染失败 (mermaid_{i}): {e}")
        return rendered

    def analyze(self, markdown: str) -> list:
        result = self.cot(ANALYSIS_PROMPT, f"教程内容：\n\n{markdown}")
        text = result.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]
        return json.loads(text.strip())

    def enhance(self, markdown: str, max_images: int = 0) -> str:
        # Step 1: 渲染已有的 mermaid 代码块为 PNG
        enhanced = self._render_existing_mermaid(markdown)

        # Step 2: LLM 分析，添加额外配图
        try:
            items = self.analyze(enhanced)
        except Exception:
            items = []

        # 限制图片数量
        if max_images > 0:
            items = items[:max_images]

        for i, item in enumerate(items):
            img_filename = f"img_{i}.png"
            img_path = str(self.output_dir / img_filename)

            try:
                if item["type"] == "mermaid" and self.mermaid.is_available():
                    self.mermaid.render(item["mermaid_code"], img_path)
                    img_ref = f"\n\n![{item['description']}](images/{img_filename})\n\n"
                elif item["type"] == "ai_image" and self.jimeng.ak:
                    self.jimeng.generate(item["prompt"], img_path)
                    img_ref = f"\n\n![{item['description']}](images/{img_filename})\n\n"
                else:
                    raise Exception("降级到 fallback")
            except Exception:
                if item["type"] == "mermaid":
                    img_ref = f"\n\n```mermaid\n{item.get('mermaid_code', '')}\n```\n\n"
                else:
                    img_ref = f"\n\n> [配图占位] {item['description']}\n\n"

            # 在目标位置插入图片
            position = item.get("position", "")
            if position and position in enhanced:
                enhanced = enhanced.replace(position, position + img_ref, 1)
            else:
                enhanced += img_ref

        return enhanced
