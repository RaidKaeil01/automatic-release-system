"""
CSDN Cookie 自动提取脚本
用 Playwright 打开 CSDN 登录页，用户手动登录后自动提取 Cookie 并写入 .env
"""
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("请先安装 playwright: pip install playwright && playwright install chromium")
    sys.exit(1)


def extract_cookie():
    print("正在启动浏览器，请在打开的窗口中登录 CSDN...")
    print("登录成功后，脚本会自动提取 Cookie 并保存。")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # 打开 CSDN 登录页
        page.goto("https://passport.csdn.net/login", wait_until="networkidle")

        # 等待用户登录（检测跳转到首页或出现用户头像）
        print("\n等待登录... 请在浏览器中完成登录操作")
        page.wait_for_url("**/www.csdn.net/**", timeout=300000)  # 5分钟超时
        page.wait_for_timeout(3000)  # 额外等待 Cookie 写入

        # 提取所有 Cookie
        cookies = context.cookies()
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies if "csdn.net" in c.get("domain", ""))

        if not cookie_str:
            print("未检测到 CSDN Cookie，请确认已登录成功。")
            browser.close()
            return

        browser.close()

    # 写入 .env 文件
    env_path = Path(__file__).parent / ".env"
    env_content = env_path.read_text(encoding="utf-8")

    if "CSDN_COOKIE=" in env_content:
        # 替换已有的 CSDN_COOKIE 行
        lines = env_content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("CSDN_COOKIE="):
                lines[i] = f"CSDN_COOKIE={cookie_str}"
                break
        env_content = "\n".join(lines)
    else:
        env_content += f"\nCSDN_COOKIE={cookie_str}\n"

    env_path.write_text(env_content, encoding="utf-8")
    print(f"\nCookie 已保存到 {env_path}")
    print(f"Cookie 长度: {len(cookie_str)} 字符")


if __name__ == "__main__":
    extract_cookie()
