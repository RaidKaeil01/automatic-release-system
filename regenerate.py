"""重新生成教程内容（复用已有大纲），跳过规划和发布步骤"""
import json
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from agents.writer_agent import WriterAgent
from agents.visual_agent import VisualAgent

console = Console()

topic = "STM32_HAL_ADC高级用法：双ADC交替采样与DMA高效传输实战"
output_dir = Path("output") / topic
images_dir = output_dir / "images"
images_dir.mkdir(parents=True, exist_ok=True)

# 复用已有大纲
outline_path = output_dir / "outline.json"
outline = json.loads(outline_path.read_text(encoding="utf-8"))
console.print(f"已加载大纲: {outline['title']} ({len(outline['sections'])} 章)")

# Step 1: 重新生成内容
console.print(Panel("[bold cyan]Step 1: 重新生成教程内容[/bold cyan]"))
writer = WriterAgent()
markdown = writer.write(outline)
md_path = output_dir / "tutorial.md"
md_path.write_text(markdown, encoding="utf-8")
console.print(f"  Markdown 已保存: {md_path} ({len(markdown)} 字符)")

# Step 2: 生成配图
console.print(Panel("[bold cyan]Step 2: 生成配图[/bold cyan]"))
visual = VisualAgent(str(images_dir))
final_md = visual.enhance(markdown)
final_path = output_dir / "tutorial_final.md"
final_path.write_text(final_md, encoding="utf-8")
console.print(f"  最终文档已保存: {final_path}")

console.print(Panel("[bold green]终稿生成完成![/bold green]"))
