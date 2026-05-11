import json
import re
import sys
import time
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from agents.planner_agent import PlannerAgent
from agents.writer_agent import WriterAgent
from agents.visual_agent import VisualAgent
from agents.publisher_agent import PublisherAgent

console = Console()


def outline_to_markdown(outline: dict) -> str:
    """将 outline dict 转为可编辑的 markdown 大纲"""
    lines = []
    lines.append(f"# {outline.get('title', '')}")
    lines.append("")
    lines.append(outline.get("description", ""))
    lines.append("")
    tags = outline.get("tags", [])
    if tags:
        lines.append(f"标签：{', '.join(tags)}")
        lines.append("")
    lines.append("---")

    for sec in outline.get("sections", []):
        lines.append("")
        lines.append(f"## {sec['id']}. {sec['title']}")
        lines.append("")
        lines.append(sec.get("description", ""))
        lines.append("")
        for kp in sec.get("key_points", []):
            lines.append(f"- {kp}")
        lang = sec.get("code_language", "")
        if lang:
            lines.append("")
            lines.append(f"代码语言：{lang}")
        lines.append("")
        lines.append("---")

    return "\n".join(lines)


def parse_outline_markdown(md_text: str, word_count: int = 5000) -> dict:
    """将编辑后的 markdown 大纲解析回 outline dict"""
    outline = {
        "title": "",
        "description": "",
        "tags": [],
        "word_count": word_count,
        "sections": [],
    }

    # 按 --- 分割章节块
    blocks = re.split(r"\n---\s*\n", md_text.strip())

    for i, block in enumerate(blocks):
        block = block.strip()
        if not block:
            continue

        if i == 0:
            # 第一块是标题、简介、标签
            lines = block.split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("# "):
                    outline["title"] = line[2:].strip()
                elif line.startswith("标签：") or line.startswith("标签:"):
                    tags_str = line.split("：", 1)[-1].split(":", 1)[-1]
                    outline["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]
                elif line and not outline["description"] and not line.startswith("#"):
                    outline["description"] = line
        else:
            # 后续块是章节
            section = {
                "id": len(outline["sections"]) + 1,
                "title": "",
                "description": "",
                "key_points": [],
                "code_language": "",
            }
            lines = block.split("\n")
            desc_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("## "):
                    # 去掉 "1. " 这种编号前缀
                    title = re.sub(r"^\d+\.\s*", "", stripped[3:].strip())
                    section["title"] = title
                elif stripped.startswith("- ") and stripped[2:].strip():
                    section["key_points"].append(stripped[2:].strip())
                elif stripped.startswith("代码语言：") or stripped.startswith("代码语言:"):
                    lang = stripped.split("：", 1)[-1].split(":", 1)[-1].strip()
                    section["code_language"] = lang
                elif stripped and not stripped.startswith("#"):
                    desc_lines.append(stripped)
            section["description"] = " ".join(desc_lines)
            if section["title"]:
                outline["sections"].append(section)

    return outline


def generate_outline(topic: str, word_count: int = 5000, output_dir: Path = None, style: str = "detailed") -> dict:
    """只生成大纲，返回 outline dict，同时保存 json 和 md"""
    planner = PlannerAgent()
    outline = planner.plan(topic, word_count=word_count, style=style)

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "outline.json").write_text(
            json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (output_dir / "outline.md").write_text(
            outline_to_markdown(outline), encoding="utf-8"
        )

    return outline


def continue_pipeline(outline: dict, topic: str, save_as_draft: bool = True, max_images: int = 0, style: str = "detailed"):
    """从已确认的大纲继续执行 pipeline（Step 2-4）"""
    output_dir = Path("output") / topic.replace(" ", "_").replace("/", "_")
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)

    # 保存大纲
    outline_path = output_dir / "outline.json"
    outline_path.write_text(json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8")

    # Step 2: 内容生成
    console.print(Panel("[bold cyan]Step 2: 生成教程内容[/bold cyan]"))
    writer = WriterAgent()
    markdown = writer.write(outline, style=style)
    md_path = output_dir / "tutorial.md"
    md_path.write_text(markdown, encoding="utf-8")
    console.print(f"  Markdown 已保存: {md_path} ({len(markdown)} 字符)")

    # Step 3: 配图
    console.print(Panel("[bold cyan]Step 3: 生成配图（流程图 + AI 图片）[/bold cyan]"))
    visual = VisualAgent(str(images_dir))
    final_md = visual.enhance(markdown, max_images=max_images)
    final_path = output_dir / "tutorial_final.md"
    final_path.write_text(final_md, encoding="utf-8")
    console.print(f"  最终文档已保存: {final_path}")

    # Step 4: 发布
    if save_as_draft:
        console.print(Panel("[bold cyan]Step 4: 保存草稿到 CSDN[/bold cyan]"))
        publisher = PublisherAgent()
        result = publisher.save_draft(final_md, title=outline["title"], tags=outline.get("tags"), md_dir=str(output_dir))
        console.print(f"  {result}")

    console.print(Panel("[bold green]Pipeline 完成![/bold green]"))
    return str(final_path)


def run_pipeline(topic: str, skip_publish: bool = False, save_as_draft: bool = True, max_images: int = 0, word_count: int = 5000, style: str = "detailed"):
    output_dir = Path("output") / topic.replace(" ", "_").replace("/", "_")
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)

    # ── Step 1: 规划 ──
    console.print(Panel(f"[bold cyan]Step 1: 规划教程大纲（目标 {word_count} 字，{'精简' if style == 'concise' else '详细'}模式）[/bold cyan]"))
    planner = PlannerAgent()
    outline = planner.plan(topic, word_count=word_count, style=style)
    outline_path = output_dir / "outline.json"
    outline_path.write_text(json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "outline.md").write_text(outline_to_markdown(outline), encoding="utf-8")
    console.print(f"  标题: {outline['title']}")
    console.print(f"  章节数: {len(outline['sections'])}")
    console.print(f"  大纲已保存: {outline_path}")

    # ── Step 2: 内容生成 ──
    console.print(Panel("[bold cyan]Step 2: 生成教程内容[/bold cyan]"))
    writer = WriterAgent()
    markdown = writer.write(outline, style=style)
    md_path = output_dir / "tutorial.md"
    md_path.write_text(markdown, encoding="utf-8")
    console.print(f"  Markdown 已保存: {md_path} ({len(markdown)} 字符)")

    # ── Step 3: 视觉配图 ──
    console.print(Panel("[bold cyan]Step 3: 生成配图（流程图 + AI 图片）[/bold cyan]"))
    visual = VisualAgent(str(images_dir))
    final_md = visual.enhance(markdown, max_images=max_images)
    final_path = output_dir / "tutorial_final.md"
    final_path.write_text(final_md, encoding="utf-8")
    diagrams_dir = images_dir / "diagrams"
    ai_dir = images_dir / "ai"
    diagram_count = len(list(diagrams_dir.glob("*.png"))) if diagrams_dir.exists() else 0
    ai_img_count = len(list(ai_dir.glob("*.png"))) if ai_dir.exists() else 0
    console.print(f"  流程图: {diagram_count} 张, AI 图片: {ai_img_count} 张")
    console.print(f"  最终文档已保存: {final_path}")

    # ── Step 4: 发布/保存草稿 ──
    if skip_publish:
        console.print(Panel("[bold yellow]Step 4: 发布（已跳过）[/bold yellow]"))
        console.print("  跳过发布，使用 --publish 参数启用")
    else:
        publisher = PublisherAgent()
        if save_as_draft:
            console.print(Panel("[bold cyan]Step 4: 保存草稿到 CSDN[/bold cyan]"))
            result = publisher.save_draft(
                final_md, title=outline["title"], tags=outline.get("tags"),
                md_dir=str(output_dir),
            )
        else:
            console.print(Panel("[bold cyan]Step 4: 发布到 CSDN[/bold cyan]"))
            result = publisher.publish(
                final_md, title=outline["title"], tags=outline.get("tags"),
                md_dir=str(output_dir),
            )
        console.print(f"  {result}")

    console.print(Panel("[bold green]Pipeline 完成![/bold green]"))
    return str(final_path)


def run_pipeline_stream(topic: str, save_as_draft: bool = True, max_images: int = 0,
                        word_count: int = 5000, outline: dict = None,
                        max_diagrams: int = 0, max_ai_images: int = 0,
                        style: str = "detailed", output_mode: str = "local"):
    """流式版本的 pipeline，yield 进度事件供 SSE 使用

    Args:
        topic: 技术主题
        save_as_draft: 是否保存草稿
        max_images: 最大配图总数限制（0=不限制）
        word_count: 目标字数
        outline: 已确认的大纲（跳过 Step 1）
        max_diagrams: 流程图数量限制（0=不限制）
        max_ai_images: AI 图片数量限制（0=不限制）
        style: 文章风格 "detailed"（详细）或 "concise"（精简）
        output_mode: 输出方式 "local"（本地）/ "draft"（草稿）/ "publish"（发布）
    """
    output_dir = Path("output") / topic.replace(" ", "_").replace("/", "_")
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)

    def emit(step, status, detail="", data=None):
        event = {"step": step, "status": status, "detail": detail, "data": data or {}}
        return event

    # ── Step 1: 规划 ──
    if outline:
        # 使用传入的大纲，跳过生成，但确保文件已保存
        outline_path = output_dir / "outline.json"
        outline_path.write_text(json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8")
        (output_dir / "outline.md").write_text(outline_to_markdown(outline), encoding="utf-8")
        yield emit(1, "done", f"标题: {outline['title']}，共 {len(outline['sections'])} 章（使用已确认大纲）",
                   {"title": outline["title"], "sections": len(outline["sections"])})
    else:
        style_label = "精简" if style == "concise" else "详细"
        yield emit(1, "running", f"正在规划教程大纲（目标 {word_count} 字，{style_label}模式）...")
        try:
            planner = PlannerAgent()
            outline = planner.plan(topic, word_count=word_count, style=style)
            outline_path = output_dir / "outline.json"
            outline_path.write_text(json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8")
            (output_dir / "outline.md").write_text(outline_to_markdown(outline), encoding="utf-8")
            yield emit(1, "done", f"标题: {outline['title']}，共 {len(outline['sections'])} 章",
                       {"title": outline["title"], "sections": len(outline["sections"])})
        except Exception as e:
            yield emit(1, "error", f"规划失败: {str(e)}")
            return

    # ── Step 2: 内容生成 ──
    yield emit(2, "running", "正在生成教程内容...")
    try:
        writer = WriterAgent()
        markdown = writer.write(outline, style=style)
        md_path = output_dir / "tutorial.md"
        md_path.write_text(markdown, encoding="utf-8")
        yield emit(2, "done", f"已生成 {len(markdown)} 字符的 Markdown 内容",
                   {"chars": len(markdown)})
    except Exception as e:
        yield emit(2, "error", f"内容生成失败: {str(e)}")
        return

    # ── Step 3: 视觉配图 ──
    yield emit(3, "running", "正在分析配图需求...")
    try:
        visual = VisualAgent(str(images_dir))
        final_md = visual.enhance(markdown, max_images=max_images,
                                   max_diagrams=max_diagrams, max_ai_images=max_ai_images)
        final_path = output_dir / "tutorial_final.md"
        final_path.write_text(final_md, encoding="utf-8")
        diagrams_dir = images_dir / "diagrams"
        ai_dir = images_dir / "ai"
        diagram_count = len(list(diagrams_dir.glob("diagram_*.png"))) if diagrams_dir.exists() else 0
        ai_img_count = len(list(ai_dir.glob("img_*.png"))) if ai_dir.exists() else 0
        mermaid_count = len(list(diagrams_dir.glob("mermaid_*.png"))) if diagrams_dir.exists() else 0
        total = diagram_count + ai_img_count + mermaid_count
        parts = []
        if diagram_count > 0:
            parts.append(f"{diagram_count} 张流程图")
        if ai_img_count > 0:
            parts.append(f"{ai_img_count} 张 AI 图")
        if mermaid_count > 0:
            parts.append(f"{mermaid_count} 张 Mermaid 图")
        detail = f"已生成 {total} 张配图（{' + '.join(parts)}）" if parts else f"已生成 {total} 张配图"
        yield emit(3, "done", detail, {"image_count": total, "diagrams": diagram_count, "ai_images": ai_img_count})
    except Exception as e:
        yield emit(3, "error", f"配图生成失败: {str(e)}")
        return

    # ── Step 4: 输出处理 ──
    if output_mode == "local":
        yield emit(4, "done", "已保存到本地",
                   {"name": output_dir.name, "title": outline["title"], "action": "已保存到本地"})
    else:
        action_name = "保存草稿" if output_mode == "draft" else "发布"
        yield emit(4, "running", f"正在{action_name}到 CSDN...")
        try:
            publisher = PublisherAgent()
            if output_mode == "draft":
                result = publisher.save_draft(
                    final_md, title=outline["title"], tags=outline.get("tags"),
                    md_dir=str(output_dir),
                )
            else:
                result = publisher.publish(
                    final_md, title=outline["title"], tags=outline.get("tags"),
                    md_dir=str(output_dir),
                )
            yield emit(4, "done", result,
                       {"name": output_dir.name, "title": outline["title"], "action": f"{action_name}成功", "url": result})
        except Exception as e:
            yield emit(4, "error", f"{action_name}失败: {str(e)}")
            return

    yield emit(0, "done", "Pipeline 完成!",
               {"name": output_dir.name, "title": outline["title"], "action": ""})


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="单片机技术教程自动生成与发布系统")
    parser.add_argument("topic", help="技术主题，如 'STM32 GPIO 输出控制 LED' 或 'STC51 定时器中断编程'")
    parser.add_argument("--publish", action="store_true", help="发布到 CSDN（默认保存草稿）")
    parser.add_argument("--draft", action="store_true", default=True, help="保存为草稿（默认）")
    parser.add_argument("--max-images", type=int, default=0, help="最大配图数量（0 表示不限制）")
    parser.add_argument("--word-count", type=int, default=5000, help="目标文章字数（默认 5000）")
    args = parser.parse_args()

    if args.publish:
        run_pipeline(args.topic, save_as_draft=False, max_images=args.max_images, word_count=args.word_count)
    else:
        run_pipeline(args.topic, max_images=args.max_images, word_count=args.word_count)
