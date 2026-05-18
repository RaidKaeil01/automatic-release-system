import json
import queue
import re
import shutil
import sys
import threading
from datetime import datetime
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

    for d in OUTPUT_DIR.iterdir():
        if not d.is_dir():
            continue
        outline_path = d / "outline.json"
        if not outline_path.exists():
            continue

        outline = json.loads(outline_path.read_text(encoding="utf-8"))
        images_dir = d / "images"

        # 分类统计图片
        diagrams_dir = images_dir / "diagrams"
        ai_dir = images_dir / "ai"
        diagram_count = len(list(diagrams_dir.glob("*.png"))) if diagrams_dir.exists() else 0
        ai_count = len(list(ai_dir.glob("*.png"))) if ai_dir.exists() else 0
        # 兼容旧格式（图片直接在 images/ 下）
        legacy_diagrams = len(list(images_dir.glob("diagram_*.png"))) + len(list(images_dir.glob("mermaid_*.png")))
        legacy_ai = len(list(images_dir.glob("img_*.png")))
        diagram_count += legacy_diagrams
        ai_count += legacy_ai
        image_count = diagram_count + ai_count

        # 检查是否已发布到 CSDN（通过检查是否有 tutorial_final.md）
        has_final = (d / "tutorial_final.md").exists()

        # 统计字数/字符数
        md_file = d / "tutorial_final.md"
        if not md_file.exists():
            md_file = d / "tutorial.md"
        char_count = 0
        word_count = 0
        if md_file.exists():
            content = md_file.read_text(encoding="utf-8")
            char_count = len(content)
            # 中文按字数统计：中文字符 + 英文单词数
            chinese_chars = len(re.findall(r'[一-鿿]', content))
            english_words = len(re.findall(r'[a-zA-Z]+', content))
            word_count = chinese_chars + english_words

        # 获取创建时间（使用目录修改时间）
        created_at = datetime.fromtimestamp(d.stat().st_mtime).strftime("%Y-%m-%d %H:%M")

        articles.append({
            "name": d.name,
            "title": outline.get("title", d.name),
            "description": outline.get("description", ""),
            "tags": outline.get("tags", []),
            "sections_count": len(outline.get("sections", [])),
            "image_count": image_count,
            "diagram_count": diagram_count,
            "ai_count": ai_count,
            "has_final": has_final,
            "char_count": char_count,
            "word_count": word_count,
            "created_at": created_at,
        })

    # 按时间倒序排列（最新的在前面）
    articles.sort(key=lambda x: x["created_at"], reverse=True)
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


@app.route("/toutiao")
def toutiao():
    return render_template("toutiao.html")


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

    # 提取图片列表（分目录 + 兼容旧格式）
    images_dir = article_dir / "images"
    diagrams = []
    ai_images = []
    if images_dir.exists():
        diagrams_dir = images_dir / "diagrams"
        ai_dir = images_dir / "ai"
        if diagrams_dir.exists():
            diagrams = [f"diagrams/{f.name}" for f in sorted(diagrams_dir.iterdir())]
        if ai_dir.exists():
            ai_images = [f"ai/{f.name}" for f in sorted(ai_dir.iterdir())]
        # 兼容旧格式
        for f in sorted(images_dir.iterdir()):
            if f.is_file():
                if f.name.startswith(("diagram_", "mermaid_")):
                    diagrams.append(f.name)
                elif f.name.startswith("img_"):
                    ai_images.append(f.name)
    images = diagrams + ai_images

    # 统计字数/字符数
    import re
    char_count = len(md_content)
    chinese_chars = len(re.findall(r'[一-鿿]', md_content))
    english_words = len(re.findall(r'[a-zA-Z]+', md_content))
    word_count = chinese_chars + english_words

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
        diagrams=diagrams,
        ai_images=ai_images,
        char_count=char_count,
        word_count=word_count,
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

    max_images = data.get("max_images", 0)
    max_diagrams = data.get("max_diagrams", 0)
    max_ai_images = data.get("max_ai_images", 0)
    save_as_draft = data.get("draft", True)
    word_count = data.get("word_count", 5000)
    outline = data.get("outline")  # 可选：已确认的大纲
    style = data.get("style", "detailed")  # "detailed" 或 "concise"
    output_mode = data.get("output_mode", "local")  # "local" / "draft" / "publish"

    from main import run_pipeline_stream

    q = queue.Queue()

    def run_in_background():
        try:
            for event in run_pipeline_stream(
                topic, save_as_draft=save_as_draft, max_images=max_images,
                word_count=word_count, outline=outline,
                max_diagrams=max_diagrams, max_ai_images=max_ai_images,
                style=style, output_mode=output_mode
            ):
                q.put(event)
        except Exception as e:
            q.put({"step": -1, "status": "error", "detail": str(e)})
        finally:
            q.put(None)

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


@app.route("/api/outline", methods=["POST"])
def api_outline_generate():
    """只生成大纲，不继续后续步骤"""
    data = request.get_json(silent=True) or {}
    topic = data.get("topic", "").strip()
    if not topic:
        return jsonify({"error": "请输入主题"}), 400

    word_count = data.get("word_count", 5000)
    style = data.get("style", "detailed")
    output_dir = OUTPUT_DIR / topic.replace(" ", "_").replace("/", "_")

    from main import generate_outline, outline_to_markdown

    try:
        outline = generate_outline(topic, word_count=word_count, output_dir=output_dir, style=style)
        md_content = outline_to_markdown(outline)
        return jsonify({"outline": outline, "outline_md": md_content, "name": output_dir.name})
    except Exception as e:
        return jsonify({"error": f"大纲生成失败: {str(e)}"}), 500


@app.route("/api/article/<name>/outline-md", methods=["GET"])
def api_outline_md_get(name):
    """获取大纲 markdown 内容"""
    article_dir = get_article_dir(name)
    if not article_dir:
        return jsonify({"error": "文章不存在"}), 404
    md_path = article_dir / "outline.md"
    if not md_path.exists():
        # 从 outline.json 生成
        from main import outline_to_markdown
        outline = json.loads((article_dir / "outline.json").read_text(encoding="utf-8"))
        md_content = outline_to_markdown(outline)
        md_path.write_text(md_content, encoding="utf-8")
    else:
        md_content = md_path.read_text(encoding="utf-8")
    return jsonify({"content": md_content})


@app.route("/api/article/<name>/outline-md", methods=["POST"])
def api_outline_md_save(name):
    """保存编辑后的大纲 markdown，解析为 JSON 更新 outline.json"""
    article_dir = get_article_dir(name)
    if not article_dir:
        return jsonify({"error": "文章不存在"}), 404

    data = request.get_json(silent=True) or {}
    md_content = data.get("content", "").strip()
    if not md_content:
        return jsonify({"error": "内容为空"}), 400

    from main import parse_outline_markdown, outline_to_markdown

    # 读取原 word_count
    old_outline = json.loads((article_dir / "outline.json").read_text(encoding="utf-8"))
    word_count = old_outline.get("word_count", 5000)

    try:
        new_outline = parse_outline_markdown(md_content, word_count=word_count)
    except Exception as e:
        return jsonify({"error": f"解析失败: {str(e)}"}), 400

    if not new_outline["title"]:
        return jsonify({"error": "缺少教程标题"}), 400
    if not new_outline["sections"]:
        return jsonify({"error": "缺少章节内容"}), 400

    # 保存 json 和 md
    (article_dir / "outline.json").write_text(
        json.dumps(new_outline, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (article_dir / "outline.md").write_text(md_content, encoding="utf-8")

    return jsonify({"outline": new_outline, "message": "大纲已保存"})


# ── 设置 API ─────────────────────────────────────────────

ENV_PATH = PROJECT_ROOT / ".env"

# 定义需要管理的配置项
SETTINGS_FIELDS = [
    {"key": "MIMO_API_KEY", "label": "MIMO API Key", "group": "  MIMO LLM", "type": "password"},
    {"key": "MIMO_BASE_URL", "label": "MIMO Base URL", "group": "  MIMO LLM", "type": "text"},
    {"key": "MIMO_MODEL", "label": "MIMO 模型", "group": "  MIMO LLM", "type": "text"},
    {"key": "JIMENG_AK", "label": "即梦 Access Key", "group": "  即梦 AI 图片", "type": "password"},
    {"key": "JIMENG_SK", "label": "即梦 Secret Key", "group": "  即梦 AI 图片", "type": "password"},
    {"key": "CSDN_COOKIE", "label": "CSDN Cookie", "group": " CSDN 发布", "type": "textarea"},
    {"key": "TOUTIAO_COOKIE", "label": "今日头条 Cookie", "group": " 今日头条", "type": "textarea"},
]


def read_env() -> dict:
    """读取 .env 文件为 dict"""
    env = {}
    if not ENV_PATH.exists():
        return env
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def write_env(env: dict):
    """将 dict 写回 .env 文件，保留注释和格式"""
    lines = []
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                lines.append(line)
                continue
            if "=" in stripped:
                k = stripped.split("=", 1)[0].strip()
                if k in env:
                    lines.append(f"{k}={env[k]}")
                    continue
            lines.append(line)
    # 追加新增的 key
    existing_keys = set()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            existing_keys.add(stripped.split("=", 1)[0].strip())
    for k, v in env.items():
        if k not in existing_keys:
            lines.append(f"{k}={v}")

    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def mask_value(key: str, value: str) -> str:
    """部分遮蔽敏感值"""
    if not value or value.startswith("your_"):
        return value
    # Cookie 太长，只显示前后
    if key == "CSDN_COOKIE":
        if len(value) > 20:
            return value[:10] + "..." + value[-10:]
        return value
    # API Key 类型：显示前缀和后几位
    if any(x in key.upper() for x in ["KEY", "AK", "SK", "SECRET", "TOKEN"]):
        if len(value) > 10:
            return value[:6] + "..." + value[-4:]
        return value
    return value


@app.route("/api/settings", methods=["GET"])
def api_settings_get():
    """获取当前配置"""
    env = read_env()
    groups = {}
    for field in SETTINGS_FIELDS:
        group = field["group"]
        if group not in groups:
            groups[group] = []
        val = env.get(field["key"], "")
        groups[group].append({
            "key": field["key"],
            "label": field["label"],
            "type": field["type"],
            "value": val,
            "masked": mask_value(field["key"], val),
            "configured": bool(val and not val.startswith("your_")),
        })
    return jsonify({"groups": groups})


@app.route("/api/settings", methods=["POST"])
def api_settings_save():
    """保存配置"""
    data = request.get_json(silent=True) or {}
    env = read_env()

    for field in SETTINGS_FIELDS:
        key = field["key"]
        if key in data:
            val = data[key].strip()
            # 空值或占位符不写入
            if val and not val.startswith("your_"):
                env[key] = val

    write_env(env)

    # 重新加载环境变量到 os.environ
    import os
    for k, v in env.items():
        if v:
            os.environ[k] = v

    return jsonify({"message": "配置已保存，重启服务后完全生效"})


# ── 图片静态服务 ──────────────────────────────────────────


@app.route("/images/<name>/<path:filename>")
def serve_image(name, filename):
    images_dir = OUTPUT_DIR / name / "images"
    if not images_dir.exists():
        return "Not found", 404
    return send_from_directory(str(images_dir), filename)


# ── 启动 ──────────────────────────────────────────────────


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
