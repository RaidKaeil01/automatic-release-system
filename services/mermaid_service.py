import subprocess
import tempfile
from pathlib import Path

# puppeteer 配置文件路径（指向系统 Chrome）
_PUPPETEER_CONFIG = str(Path(__file__).parent.parent / "puppeteer-config.json")


class MermaidService:
    """调用 mmdc (Mermaid CLI) 将 Mermaid 代码渲染为 PNG"""

    def __init__(self, mmdc_path=None):
        if mmdc_path is None:
            import shutil
            import platform
            found = shutil.which("mmdc")
            if found:
                self.mmdc_path = found
            elif platform.system() == "Windows":
                # Windows npm 全局安装路径
                self.mmdc_path = "C:\\Program Files\\nodejs\\node_global\\mmdc.cmd"
            else:
                self.mmdc_path = "mmdc"
        else:
            self.mmdc_path = mmdc_path

    def render(self, mermaid_code: str, output_path: str) -> str:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False, encoding="utf-8") as f:
            f.write(mermaid_code)
            input_file = f.name

        try:
            cmd = [self.mmdc_path, "-i", input_file, "-o", output_path, "-b", "transparent"]
            if Path(_PUPPETEER_CONFIG).exists():
                cmd.extend(["-p", _PUPPETEER_CONFIG])
            subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
            return output_path
        finally:
            Path(input_file).unlink(missing_ok=True)

    def is_available(self) -> bool:
        try:
            subprocess.run([self.mmdc_path, "--version"], capture_output=True)
            return True
        except FileNotFoundError:
            return False
