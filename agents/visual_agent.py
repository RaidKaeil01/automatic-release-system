import json
import re
from pathlib import Path
from agents.base import BaseAgent
from agents.coder_agent import CoderAgent
from services.mermaid_service import MermaidService
from services.jimeng_service import JimengService

ANALYSIS_PROMPT = """你是一位技术文档视觉设计专家。

分析以下 Markdown 教程内容，识别需要配图的位置（仅分析文本，已有配图的位置不要重复）。

对每个需要配图的位置，根据内容性质选择合适的类型：

【diagram 类型】— 适合展示流程、结构、逻辑关系、数据流、状态转换等：
- 程序执行流程（初始化 → 配置 → 运行）
- 硬件架构/模块关系（MCU ↔ 外设 ↔ 传感器）
- 中断处理流程、状态机转换
- 通信时序（I2C、SPI、UART 的时序交互）
- 代码调用关系、数据流向

【ai_image 类型】— 适合展示实物、场景、硬件外观、接线实拍等：
- 开发板实物照片、芯片外观
- 实际接线效果、实验场景
- 波形截图效果、运行结果展示
- 硬件连接示意图（需要写实风格的）

对每个需要配图的位置，输出：
1. 插入位置（在哪个章节标题或段落关键词之后）
2. 图表类型：diagram 或 ai_image
3. 图表内容描述
4. 对于 diagram 类型：mermaid_type（flowchart/sequence/class/state/er/graph）
5. 对于 ai_image 类型：prompt（英文提示词）

严格按以下 JSON 数组格式输出：
[
  {
    "position": "章节标题或段落关键词",
    "type": "diagram",
    "description": "描述图表展示什么内容",
    "mermaid_type": "flowchart"
  },
  {
    "position": "章节标题或段落关键词",
    "type": "ai_image",
    "description": "描述要生成什么图片",
    "prompt": "English prompt for AI image generation"
  }
]

只输出 JSON，不要输出其他内容。"""


class VisualAgent(BaseAgent):
    def __init__(self, output_dir: str, llm=None):
        super().__init__(llm)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.diagrams_dir = self.output_dir / "diagrams"
        self.ai_dir = self.output_dir / "ai"
        self.diagrams_dir.mkdir(exist_ok=True)
        self.ai_dir.mkdir(exist_ok=True)
        self.mermaid = MermaidService()
        self.jimeng = JimengService()
        self.coder = CoderAgent(llm)

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
            img_path = str(self.diagrams_dir / img_filename)
            try:
                self.mermaid.render(code, img_path)
                img_ref = f"![mermaid diagram](images/diagrams/{img_filename})"
                rendered = rendered.replace(match.group(0), img_ref, 1)
            except Exception as e:
                print(f"Mermaid 渲染失败 (mermaid_{i}): {e}")
        return rendered

    def analyze(self, markdown: str) -> list:
        result = self.cot(ANALYSIS_PROMPT, f"教程内容：\n\n{markdown}")
        text = result.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]
        return json.loads(text.strip())

    def enhance(self, markdown: str, max_images: int = 0, max_diagrams: int = 0, max_ai_images: int = 0) -> str:
        """
        Args:
            max_images: 总图片数限制（兼容旧参数，0=不限制）
            max_diagrams: 流程图数量限制（0=不限制）
            max_ai_images: AI 图片数量限制（0=不限制）
        """
        # Step 1: 渲染已有的 mermaid 代码块为 PNG
        enhanced = self._render_existing_mermaid(markdown)

        # Step 2: LLM 分析，添加额外配图
        try:
            items = self.analyze(enhanced)
        except Exception:
            items = []

        # 按类型分开，分别限制数量
        diagram_items = [it for it in items if it.get("type") == "diagram"]
        ai_items = [it for it in items if it.get("type") != "diagram"]

        if max_diagrams > 0:
            diagram_items = diagram_items[:max_diagrams]
        if max_ai_images > 0:
            ai_items = ai_items[:max_ai_images]

        # 总数限制（max_images 作为总上限）
        if max_images > 0:
            total = len(diagram_items) + len(ai_items)
            if total > max_images:
                # 按比例裁剪，优先保留 diagram
                remain = max_images
                diagram_items = diagram_items[:remain]
                remain -= len(diagram_items)
                ai_items = ai_items[:remain]

        # 重新合并，保持原始顺序
        limited_set = set()
        for it in diagram_items:
            limited_set.add(id(it))
        for it in ai_items:
            limited_set.add(id(it))
        items = [it for it in items if id(it) in limited_set]

        diagram_idx = 0  # diagram 文件计数器
        img_idx = 0      # ai_image 文件计数器

        for i, item in enumerate(items):
            item_type = item.get("type", "ai_image")

            try:
                if item_type == "diagram":
                    # ── Mermaid 流程图分支 ──
                    if not self.mermaid.is_available():
                        raise Exception("mmdc 不可用")

                    mermaid_type = item.get("mermaid_type", "flowchart")
                    description = item.get("description", "")

                    # 调用 CoderAgent 生成 Mermaid 代码
                    mermaid_code = self.coder.generate_mermaid(description, mermaid_type)

                    img_filename = f"diagram_{diagram_idx}.png"
                    img_path = str(self.diagrams_dir / img_filename)
                    self.mermaid.render(mermaid_code, img_path)

                    img_ref = f"\n\n![{item['description']}](images/diagrams/{img_filename})\n\n"
                    diagram_idx += 1

                elif item_type == "ai_image" and self.jimeng.ak:
                    # ── 即梦 AI 图片分支 ──
                    img_filename = f"img_{img_idx}.png"
                    img_path = str(self.ai_dir / img_filename)
                    self.jimeng.generate(item["prompt"], img_path)

                    img_ref = f"\n\n![{item['description']}](images/ai/{img_filename})\n\n"
                    img_idx += 1

                else:
                    raise Exception("未知类型或服务不可用")

            except Exception as e:
                # 降级处理
                if item_type == "diagram":
                    # diagram 降级：输出 mermaid 代码块
                    fallback_code = item.get("mermaid_code", "")
                    if not fallback_code:
                        fallback_code = f"graph TD\n    A[{item.get('description', '待补充')}]"
                    img_ref = f"\n\n```mermaid\n{fallback_code}\n```\n\n"
                else:
                    # ai_image 降级：输出占位文字
                    img_ref = f"\n\n> [配图占位] {item['description']}\n\n"

            # 在目标位置插入图片
            position = item.get("position", "")
            if position and position in enhanced:
                enhanced = enhanced.replace(position, position + img_ref, 1)
            else:
                enhanced += img_ref

        return enhanced
