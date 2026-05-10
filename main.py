import json
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


def run_pipeline(topic: str, skip_publish: bool = False, save_as_draft: bool = True, max_images: int = 0):
    output_dir = Path("output") / topic.replace(" ", "_").replace("/", "_")
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)

    # ── Step 1: 规划 ──
    console.print(Panel("[bold cyan]Step 1: 规划教程大纲[/bold cyan]"))
    planner = PlannerAgent()
    outline = planner.plan(topic)
    outline_path = output_dir / "outline.json"
    outline_path.write_text(json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"  标题: {outline['title']}")
    console.print(f"  章节数: {len(outline['sections'])}")
    console.print(f"  大纲已保存: {outline_path}")

    # ── Step 2: 内容生成 ──
    console.print(Panel("[bold cyan]Step 2: 生成教程内容[/bold cyan]"))
    writer = WriterAgent()
    markdown = writer.write(outline)
    md_path = output_dir / "tutorial.md"
    md_path.write_text(markdown, encoding="utf-8")
    console.print(f"  Markdown 已保存: {md_path} ({len(markdown)} 字符)")

    # ── Step 3: 视觉配图 ──
    console.print(Panel("[bold cyan]Step 3: 生成配图[/bold cyan]"))
    visual = VisualAgent(str(images_dir))
    final_md = visual.enhance(markdown, max_images=max_images)
    final_path = output_dir / "tutorial_final.md"
    final_path.write_text(final_md, encoding="utf-8")
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


def run_pipeline_stream(topic: str, save_as_draft: bool = True, max_images: int = 0):
    """流式版本的 pipeline，yield 进度事件供 SSE 使用"""
    output_dir = Path("output") / topic.replace(" ", "_").replace("/", "_")
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)

    def emit(step, status, detail="", data=None):
        event = {"step": step, "status": status, "detail": detail, "data": data or {}}
        return event

    # ── Step 1: 规划 ──
    yield emit(1, "running", "正在规划教程大纲...")
    try:
        planner = PlannerAgent()
        outline = planner.plan(topic)
        outline_path = output_dir / "outline.json"
        outline_path.write_text(json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8")
        yield emit(1, "done", f"标题: {outline['title']}，共 {len(outline['sections'])} 章",
                   {"title": outline["title"], "sections": len(outline["sections"])})
    except Exception as e:
        yield emit(1, "error", f"规划失败: {str(e)}")
        return

    # ── Step 2: 内容生成 ──
    yield emit(2, "running", "正在生成教程内容...")
    try:
        writer = WriterAgent()
        markdown = writer.write(outline)
        md_path = output_dir / "tutorial.md"
        md_path.write_text(markdown, encoding="utf-8")
        yield emit(2, "done", f"已生成 {len(markdown)} 字符的 Markdown 内容",
                   {"chars": len(markdown)})
    except Exception as e:
        yield emit(2, "error", f"内容生成失败: {str(e)}")
        return

    # ── Step 3: 视觉配图 ──
    yield emit(3, "running", "正在生成配图...")
    try:
        visual = VisualAgent(str(images_dir))
        final_md = visual.enhance(markdown, max_images=max_images)
        final_path = output_dir / "tutorial_final.md"
        final_path.write_text(final_md, encoding="utf-8")
        img_count = len(list(images_dir.glob("*")))
        yield emit(3, "done", f"已生成 {img_count} 张配图", {"image_count": img_count})
    except Exception as e:
        yield emit(3, "error", f"配图生成失败: {str(e)}")
        return

    # ── Step 4: 发布/保存草稿 ──
    yield emit(4, "running", "正在上传到 CSDN..." if not save_as_draft else "正在保存草稿到 CSDN...")
    try:
        publisher = PublisherAgent()
        if save_as_draft:
            result = publisher.save_draft(
                final_md, title=outline["title"], tags=outline.get("tags"),
                md_dir=str(output_dir),
            )
        else:
            result = publisher.publish(
                final_md, title=outline["title"], tags=outline.get("tags"),
                md_dir=str(output_dir),
            )
        yield emit(4, "done", result, {"url": result})
    except Exception as e:
        yield emit(4, "error", f"发布失败: {str(e)}")
        return

    yield emit(0, "done", "Pipeline 完成!",
               {"name": output_dir.name, "title": outline["title"]})


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="单片机技术教程自动生成与发布系统")
    parser.add_argument("topic", help="技术主题，如 'STM32 GPIO 输出控制 LED' 或 'STC51 定时器中断编程'")
    parser.add_argument("--publish", action="store_true", help="发布到 CSDN（默认保存草稿）")
    parser.add_argument("--draft", action="store_true", default=True, help="保存为草稿（默认）")
    parser.add_argument("--max-images", type=int, default=0, help="最大配图数量（0 表示不限制）")
    args = parser.parse_args()

    if args.publish:
        run_pipeline(args.topic, save_as_draft=False, max_images=args.max_images)
    else:
        run_pipeline(args.topic, max_images=args.max_images)
