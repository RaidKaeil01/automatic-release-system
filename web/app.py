import json
import queue
import shutil
import sys
import threading
from pathlib import Path

import markdown
from flask import Flask, Response, jsonify, render_template, request, send_from_directory

# 将项目根目录加入 sys.path，以便导入 agents
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT_DIR = PROJECT_ROOT / "output"

app = Flask(__name__)


# ── 工具函数 ──────────────────────────────────────────────


def get_articles() -> list[dict]:
    """扫描 output/ 目录，返回所有文章的摘要信息"""
    articles = []
    if not OUTPUT_DIR.exists():
        return articles

    for d in sorted(OUTPUT_DIR.iterdir()):
        if not d.is_dir():
            continue
        outline_path = d / "outline.json"
        if not outline_path.exists():
            continue

        outline = json.loads(outline_path.read_text(encoding="utf-8"))
        images_dir = d / "images"
        image_count = len(list(images_dir.glob("*"))) if images_dir.exists() else 0

        # 检查是否已发布到 CSDN（通过检查是否有 tutorial_final.md）
        has_final = (d / "tutorial_final.md").exists()

        articles.append({
            "name": d.name,
            "title": outline.get("title", d.name),
            "description": outline.get("description", ""),
            "tags": outline.get("tags", []),
            "sections_count": len(outline.get("sections", [])),
            "image_count": image_count,
            "has_final": has_final,
        })

    return articles


def get_article_dir(name: str) -> Path | None:
    """获取文章目录，不存在则返回 None"""
    article_dir = OUTPUT_DIR / name
    if article_dir.exists() and article_dir.is_dir():
        return article_dir
    return None


# ── 页面路由 ──────────────────────────────────────────────


@app.route("/")
def index():
    articles = get_articles()
    return render_template("index.html", articles=articles)


@app.route("/article/<name>")
def article_detail(name):
    article_dir = get_article_dir(name)
    if not article_dir:
        return "文章不存在", 404

    outline = json.loads((article_dir / "outline.json").read_text(encoding="utf-8"))

    # 读取最终 Markdown 并转为 HTML
    md_file = article_dir / "tutorial_final.md"
    if not md_file.exists():
        md_file = article_dir / "tutorial.md"
    md_content = md_file.read_text(encoding="utf-8")

    # 提取图片列表
    images_dir = article_dir / "images"
    images = sorted([f.name for f in images_dir.iterdir()]) if images_dir.exists() else []

    html_content = markdown.markdown(
        md_content,
        extensions=["fenced_code", "tables", "toc", "codehilite"],
        extension_configs={
            "codehilite": {"guess_lang": False, "css_class": "highlight"}
        },
    )

    return render_template(
        "detail.html",
        name=name,
        outline=outline,
        html_content=html_content,
        md_content=md_content,
        images=images,
    )


# ── API 路由 ──────────────────────────────────────────────


@app.route("/api/articles")
def api_articles():
    return jsonify(get_articles())


@app.route("/api/article/<name>/outline")
def api_outline(name):
    article_dir = get_article_dir(name)
    if not article_dir:
        return jsonify({"error": "文章不存在"}), 404
    outline = json.loads((article_dir / "outline.json").read_text(encoding="utf-8"))
    return jsonify(outline)


@app.route("/api/article/<name>/content")
def api_content(name):
    article_dir = get_article_dir(name)
    if not article_dir:
        return jsonify({"error": "文章不存在"}), 404
    md_file = article_dir / "tutorial_final.md"
    if not md_file.exists():
        md_file = article_dir / "tutorial.md"
    return jsonify({"content": md_file.read_text(encoding="utf-8")})


@app.route("/api/article/<name>", methods=["DELETE"])
def api_delete(name):
    article_dir = get_article_dir(name)
    if not article_dir:
        return jsonify({"error": "文章不存在"}), 404
    shutil.rmtree(article_dir)
    return jsonify({"message": f"文章 '{name}' 已删除"})


@app.route("/api/article/<name>/publish", methods=["POST"])
def api_publish(name):
    article_dir = get_article_dir(name)
    if not article_dir:
        return jsonify({"error": "文章不存在"}), 404

    data = request.get_json(silent=True) or {}
    save_as_draft = data.get("draft", True)

    # 在后台线程中执行发布（因为 Playwright 比较耗时）
    def do_publish():
        from agents.publisher_agent import PublisherAgent
        from agents.visual_agent import VisualAgent

        outline = json.loads((article_dir / "outline.json").read_text(encoding="utf-8"))
        md_file = article_dir / "tutorial_final.md"
        if not md_file.exists():
            md_file = article_dir / "tutorial.md"
        md_content = md_file.read_text(encoding="utf-8")

        publisher = PublisherAgent()
        if save_as_draft:
            result = publisher.save_draft(
                md_content, title=outline["title"], tags=outline.get("tags"),
                md_dir=str(article_dir),
            )
        else:
            result = publisher.publish(
                md_content, title=outline["title"], tags=outline.get("tags"),
                md_dir=str(article_dir),
            )
        app.logger.info(f"发布结果: {result}")

    thread = threading.Thread(target=do_publish, daemon=True)
    thread.start()

    action = "保存草稿" if save_as_draft else "发布"
    return jsonify({"message": f"正在{action}，请稍候..."})


# ── 文章生成 SSE ─────────────────────────────────────────


@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.get_json(silent=True) or {}
    topic = data.get("topic", "").strip()
    if not topic:
        return jsonify({"error": "请输入主题"}), 400

    max_images = data.get("max_images", 3)
    save_as_draft = data.get("draft", True)

    from main import run_pipeline_stream

    q = queue.Queue()

    def run_in_background():
        try:
            for event in run_pipeline_stream(topic, save_as_draft=save_as_draft, max_images=max_images):
                q.put(event)
        except Exception as e:
            q.put({"step": -1, "status": "error", "detail": str(e)})
        finally:
            q.put(None)  # 结束信号

    thread = threading.Thread(target=run_in_background, daemon=True)
    thread.start()

    def event_stream():
        while True:
            event = q.get()
            if event is None:
                break
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return Response(event_stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── 图片静态服务 ──────────────────────────────────────────


@app.route("/images/<name>/<filename>")
def serve_image(name, filename):
    images_dir = OUTPUT_DIR / name / "images"
    if not images_dir.exists():
        return "Not found", 404
    return send_from_directory(str(images_dir), filename)


# ── 启动 ──────────────────────────────────────────────────


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
