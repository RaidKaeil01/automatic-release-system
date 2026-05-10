import base64
import json
import time
from pathlib import Path
from config import JIMENG_AK, JIMENG_SK

from volcengine.visual.VisualService import VisualService


class JimengService:
    def __init__(self, ak=None, sk=None):
        self.ak = ak or JIMENG_AK
        self.sk = sk or JIMENG_SK
        self._service = None

    @property
    def service(self):
        if self._service is None:
            self._service = VisualService()
            self._service.set_ak(self.ak)
            self._service.set_sk(self.sk)
        return self._service

    def _submit_task(self, prompt, width=None, height=None, size=None, force_single=True):
        """提交异步生成任务"""
        form = {
            "req_key": "jimeng_t2i_v40",
            "prompt": prompt,
            "force_single": force_single,
        }
        if width and height:
            form["width"] = width
            form["height"] = height
        elif size:
            form["size"] = size
        else:
            form["size"] = 2048 * 2048

        resp = self.service.cv_sync2async_submit_task(form)
        if resp is None:
            raise Exception("即梦 API 提交任务返回空响应")

        code = resp.get("code", -1)
        if code != 10000:
            msg = resp.get("message", "未知错误")
            raise Exception(f"即梦 API 提交失败 (code={code}): {msg}")

        task_id = resp.get("data", {}).get("task_id")
        if not task_id:
            raise Exception(f"即梦 API 未返回 task_id: {resp}")
        return task_id

    def _query_result(self, task_id, timeout=120):
        """轮询查询任务结果"""
        form = {
            "req_key": "jimeng_t2i_v40",
            "task_id": task_id,
        }

        start = time.time()
        while time.time() - start < timeout:
            resp = self.service.cv_sync2async_get_result(form)
            if resp is None:
                time.sleep(2)
                continue

            code = resp.get("code", -1)
            if code != 10000:
                msg = resp.get("message", "未知错误")
                raise Exception(f"即梦 API 查询失败 (code={code}): {msg}")

            data = resp.get("data", {})
            status = data.get("status", "")

            if status == "done":
                return data
            elif status in ("not_found", "expired"):
                raise Exception(f"任务已过期或未找到: {status}")
            # in_queue 或 generating，继续等待
            time.sleep(3)

        raise Exception(f"等待超时 ({timeout}s)")

    def generate(self, prompt: str, output_path: str, width=None, height=None) -> str:
        """调用即梦 4.0 生成图片（异步：提交→轮询→获取结果）"""
        task_id = self._submit_task(prompt, width, height)
        result = self._query_result(task_id)

        # 提取图片
        img_list = result.get("binary_data_base64", [])
        url_list = result.get("image_urls", [])

        if img_list:
            img_bytes = base64.b64decode(img_list[0])
        elif url_list:
            import httpx
            with httpx.Client(timeout=60) as client:
                img_bytes = client.get(url_list[0]).content
        else:
            raise Exception(f"即梦 API 未返回图片: {json.dumps(result, ensure_ascii=False)[:500]}")

        Path(output_path).write_bytes(img_bytes)
        return output_path
