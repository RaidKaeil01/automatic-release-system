import re
from pathlib import Path
from config import CSDN_COOKIE

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


class PublisherAgent:
    CSDN_WRITE_URL = "https://editor.csdn.net/md"

    def __init__(self, cookie=None):
        self.cookie = cookie or CSDN_COOKIE

    def _upload_image_via_browser(self, page, img_path: str) -> str:
        """通过浏览器 csdn.upload.uploadImg 上传图片，返回 CSDN 图片 URL"""
        import base64
        abs_path = str(Path(img_path).resolve())
        img_bytes = Path(abs_path).read_bytes()
        img_b64 = base64.b64encode(img_bytes).decode()
        suffix = Path(abs_path).suffix.lstrip(".").lower()
        if suffix == "jpg":
            suffix = "jpeg"
        mime = f"image/{suffix}"

        result = page.evaluate('''([imgB64, mime, fileName]) => {
            return new Promise((resolve, reject) => {
                try {
                    // 将 base64 转为 File 对象
                    const binaryStr = atob(imgB64);
                    const bytes = new Uint8Array(binaryStr.length);
                    for (let i = 0; i < binaryStr.length; i++) bytes[i] = binaryStr.charCodeAt(i);
                    const file = new File([bytes], fileName, {type: mime});

                    // 调用 CSDN 内置上传函数（自动处理签名）
                    window.csdn.upload.uploadImg({
                        file: file,
                        appName: 'direct_blog_markdown',
                        imageTemplate: ''
                    }).then(r => {
                        const data = r && r[0] && r[0].data && r[0].data.data;
                        if (data && data.imageUrl) {
                            resolve(data.imageUrl);
                        } else {
                            reject('No imageUrl: ' + JSON.stringify(r).substring(0, 200));
                        }
                    }).catch(e => reject(e.message || String(e)));
                } catch(e) {
                    reject(e.message || String(e));
                }
            });
        }''', [img_b64, mime, Path(abs_path).name])
        return result

    def upload_images(self, page, md_content: str, md_dir: str) -> str:
        """将 markdown 中的本地图片通过浏览器上传到 CSDN，替换为在线 URL"""
        md_dir_path = Path(md_dir)
        uploaded_count = 0

        def replace_img(match):
            nonlocal uploaded_count
            alt = match.group(1)
            local_path = match.group(2)
            if local_path.startswith("http://") or local_path.startswith("https://"):
                return match.group(0)

            img_file = md_dir_path / local_path
            if not img_file.exists():
                print(f"  图片不存在，跳过: {local_path}")
                return match.group(0)

            try:
                url = self._upload_image_via_browser(page, str(img_file))
                uploaded_count += 1
                print(f"  已上传 ({uploaded_count}): {local_path} -> {url}")
                return f"![{alt}]({url})"
            except Exception as e:
                print(f"  上传失败 {local_path}: {e}")
                return match.group(0)

        return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace_img, md_content)

    def _inject_markdown_content(self, page, md_content: str):
        """向 CSDN Markdown 编辑器注入内容（兼容 CodeMirror）"""
        # 方法1: 尝试通过 CodeMirror API 注入
        injected = page.evaluate("""(mdContent) => {
            // 尝试找到 CodeMirror 实例
            const cmEl = document.querySelector('.CodeMirror');
            if (cmEl && cmEl.CodeMirror) {
                cmEl.CodeMirror.setValue(mdContent);
                return 'codemirror';
            }
            // 尝试找到编辑器 textarea
            const ta = document.querySelector('.editor__inner, textarea.editor-textarea, .cm-content');
            if (ta) {
                // 如果是 textarea
                if (ta.tagName === 'TEXTAREA') {
                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLTextAreaElement.prototype, 'value').set;
                    nativeInputValueSetter.call(ta, mdContent);
                    ta.dispatchEvent(new Event('input', { bubbles: true }));
                    ta.dispatchEvent(new Event('change', { bubbles: true }));
                    return 'textarea';
                }
            }
            return null;
        }""", md_content)

        if injected:
            print(f"  内容注入方式: {injected}")
            return

        # 方法2: 通过剪贴板粘贴注入（最可靠）
        print("  尝试剪贴板粘贴方式注入...")
        page.evaluate("""(mdContent) => {
            // 创建一个临时 textarea 来复制内容
            const ta = document.createElement('textarea');
            ta.value = mdContent;
            ta.style.position = 'fixed';
            ta.style.left = '-9999px';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
        }""", md_content)

        # 点击编辑器获取焦点
        editor = page.locator('.editor__inner, .CodeMirror, .cm-content').first
        if editor.is_visible():
            editor.click()
            page.wait_for_timeout(500)
            # 全选现有内容并删除
            page.keyboard.press("Control+a")
            page.wait_for_timeout(200)
            page.keyboard.press("Delete")
            page.wait_for_timeout(200)
            # 粘贴新内容
            page.keyboard.press("Control+v")
            print("  内容已通过剪贴板粘贴注入")
        else:
            # 方法3: 最终回退 - 直接设置 innerText
            page.evaluate("""(mdContent) => {
                const editor = document.querySelector('PRE.editor__inner');
                if (editor) {
                    editor.innerText = mdContent;
                    editor.dispatchEvent(new Event('input', {bubbles: true}));
                }
            }""", md_content)
            print("  内容已通过 innerText 注入（回退方案）")

    @staticmethod
    def _preprocess_for_csdn(md: str) -> str:
        """修复 Markdown 格式以适配 CSDN 编辑器"""

        # 使用状态机逐行处理，避免误修改代码块内部内容
        lines = md.split("\n")
        in_code_block = False
        result_lines = []

        for line in lines:
            stripped = line.strip()

            # 代码块边界检测
            if stripped.startswith("```"):
                if in_code_block:
                    # 结束代码块
                    in_code_block = False
                    result_lines.append("```")
                else:
                    # 开始代码块 - 去掉语言标记
                    in_code_block = True
                    cleaned = re.sub(r"^```[a-zA-Z_]\w*$", "```", stripped)
                    result_lines.append(cleaned)
                continue

            if in_code_block:
                # 代码块内内容原样保留
                result_lines.append(line)
                continue

            # === 以下只处理非代码块内容 ===

            # 1. 标题层级降一级（# → ##, ## → ###, 等）
            #    CSDN 文章标题已经是一级标题，内容不应再有 #
            heading_match = re.match(r"^(#{1,5})\s+(.+)$", line)
            if heading_match:
                hashes = heading_match.group(1)
                title_text = heading_match.group(2)
                line = f"#{hashes} {title_text}"

            # 2. 去掉表格对齐语法中的冒号（CSDN 不认识 :---）
            #    只匹配真正的表格分隔行：行首为 |，内容只有 |、-、:、空格
            if re.match(r"^\|[\s\-:|]+\|$", line):
                line = re.sub(r":?-+:?", "---", line)

            result_lines.append(line)

        md = "\n".join(result_lines)

        # 3. 去掉缩进代码块的缩进（列表内的代码块有4空格缩进，CSDN 不识别）
        def dedent_code_block(m):
            lines = m.group(0).split("\n")
            dedented = []
            for line in lines:
                if line.startswith("    "):
                    dedented.append(line[4:])
                else:
                    dedented.append(line)
            return "\n".join(dedented)
        md = re.sub(r"^    ```[\s\S]*?^    ```", dedent_code_block, md, flags=re.MULTILINE)

        # 4. 缩短过长的图片 alt 文本（超过50字符截断）
        def shorten_alt(m):
            alt = m.group(1)
            url = m.group(2)
            if len(alt) > 50:
                alt = alt[:47] + "..."
            return f"![{alt}]({url})"
        md = re.sub(r"!\[([^\]]+)\]\(([^)]+)\)", shorten_alt, md)

        # 5. 确保图片前后有空行（CSDN 需要空行才能正确渲染图片）
        md = re.sub(r"([^\n])\n(!\[)", r"\1\n\n\2", md)
        md = re.sub(r"(\]\([^)]+\))\n([^\n])", r"\1\n\n\2", md)

        # 6. 确保代码块前后有空行（CSDN 需要空行才能正确渲染代码块）
        md = re.sub(r"([^\n])\n(```)", r"\1\n\n\2", md)
        md = re.sub(r"(```)\n([^\n])", r"\1\n\n\2", md)

        return md

    def save_draft(self, md_content: str, title: str, tags: list = None,
                   categories: list = None, md_dir: str = None) -> str:
        """保存文章为草稿（不发布）"""
        if not sync_playwright:
            raise RuntimeError("playwright 未安装，请运行: pip install playwright && playwright install chromium")
        if not self.cookie:
            raise RuntimeError("CSDN Cookie 未配置，请在 .env 中设置 CSDN_COOKIE")

        output_dir = Path(__file__).parent.parent / "output"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            context.add_cookies(self._parse_cookie(self.cookie))
            page = context.new_page()

            # 1. 进入 CSDN Markdown 写作页面
            page.goto(self.CSDN_WRITE_URL, wait_until="networkidle")
            page.wait_for_timeout(5000)

            # 2. 上传图片到 CSDN
            if md_dir:
                print("正在通过浏览器上传图片到 CSDN...")
                md_content = self.upload_images(page, md_content, md_dir)
                print("图片上传完成")

            # 2.5. 预处理 Markdown 格式
            md_content = self._preprocess_for_csdn(md_content)
            print("Markdown 格式预处理完成")

            # 3. 注入标题
            page.evaluate("""(title) => {
                const input = document.querySelector('input[placeholder*="标题"]');
                if (input) {
                    input.value = title;
                    input.dispatchEvent(new Event('input', {bubbles: true}));
                }
            }""", title)
            print("标题已注入")

            # 4. 注入 Markdown 内容
            self._inject_markdown_content(page, md_content)
            print("内容已注入")
            page.wait_for_timeout(2000)

            # 5. 点击「保存草稿」按钮（直接在顶部工具栏）
            draft_btn = page.locator('button.btn-save').first
            if draft_btn.is_visible():
                draft_btn.click()
                print("已点击「保存草稿」按钮")
            else:
                # 备选：打开发布对话框，点击「存为草稿」
                page.locator('button.btn-publish').first.click()
                page.wait_for_timeout(2000)
                page.locator('.modal .btn-b-normal:has-text("存为草稿")').first.click()
                print("已通过对话框保存草稿")

            page.wait_for_timeout(5000)
            page.screenshot(path=str(output_dir / "csdn_debug_result.png"), full_page=True)
            final_url = page.url
            print(f"最终页面: {final_url}")

            browser.close()

        return f"草稿已保存，页面: {final_url}"

    def publish(self, md_content: str, title: str, tags: list = None,
                categories: list = None, md_dir: str = None) -> str:
        """发布文章"""
        if not sync_playwright:
            raise RuntimeError("playwright 未安装，请运行: pip install playwright && playwright install chromium")
        if not self.cookie:
            raise RuntimeError("CSDN Cookie 未配置，请在 .env 中设置 CSDN_COOKIE")

        output_dir = Path(__file__).parent.parent / "output"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            context.add_cookies(self._parse_cookie(self.cookie))
            page = context.new_page()

            # 1. 进入 CSDN Markdown 写作页面
            page.goto(self.CSDN_WRITE_URL, wait_until="networkidle")
            page.wait_for_timeout(5000)

            # 2. 上传图片到 CSDN
            if md_dir:
                print("正在通过浏览器上传图片到 CSDN...")
                md_content = self.upload_images(page, md_content, md_dir)
                print("图片上传完成")

            # 2.5. 预处理 Markdown 格式
            md_content = self._preprocess_for_csdn(md_content)
            print("Markdown 格式预处理完成")

            # 3. 注入标题
            page.evaluate("""(title) => {
                const input = document.querySelector('input[placeholder*="标题"]');
                if (input) {
                    input.value = title;
                    input.dispatchEvent(new Event('input', {bubbles: true}));
                }
            }""", title)
            print("标题已注入")

            # 4. 注入 Markdown 内容
            self._inject_markdown_content(page, md_content)
            print("内容已注入")
            page.wait_for_timeout(2000)

            # 5. 点击「发布文章」按钮，打开发布对话框
            page.locator('button.btn-publish').first.click()
            print("已点击「发布文章」按钮")
            page.wait_for_timeout(3000)

            # 6. 设置标签
            if tags:
                for tag in tags[:3]:
                    tag_input = page.locator('.modal input[placeholder*="标签"], .modal input[placeholder*="输入"]').first
                    if tag_input.is_visible():
                        tag_input.click()
                        tag_input.fill(tag)
                        page.wait_for_timeout(800)
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(500)
                        print(f"已添加标签: {tag}")

            page.wait_for_timeout(1000)
            page.screenshot(path=str(output_dir / "csdn_debug_dialog.png"), full_page=True)

            # 7. 点击确认发布按钮
            confirm_btn = page.locator('.modal .btn-b-red').first
            if confirm_btn.is_visible():
                confirm_btn.click()
                print("已点击确认发布按钮")

            page.wait_for_timeout(8000)
            page.screenshot(path=str(output_dir / "csdn_debug_result.png"), full_page=True)
            final_url = page.url
            print(f"最终页面: {final_url}")

            browser.close()

        return f"发布完成，页面: {final_url}"

    def _parse_cookie(self, cookie_str: str) -> list:
        """将 Cookie 字符串解析为 Playwright 格式"""
        cookies = []
        for item in cookie_str.split(";"):
            item = item.strip()
            if "=" in item:
                name, value = item.split("=", 1)
                cookies.append({
                    "name": name.strip(),
                    "value": value.strip(),
                    "domain": ".csdn.net",
                    "path": "/",
                })
        return cookies
