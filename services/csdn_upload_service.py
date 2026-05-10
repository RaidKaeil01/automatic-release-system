import hashlib
import hmac
import json
import time
from pathlib import Path

import httpx


class CSDNUploadService:
    """将图片上传到 CSDN 图床（华为云 OBS）"""

    SIGNATURE_URL = "https://bizapi.csdn.net/resource-api/v1/image/direct/upload/signature"
    APP_NAME = "direct_blog_markdown"

    def __init__(self, cookie: str):
        self.cookie = cookie
        self._headers = {
            "Cookie": cookie,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://editor.csdn.net/",
            "Origin": "https://editor.csdn.net",
        }

    def upload(self, image_path: str) -> str:
        """上传图片到 CSDN，返回图片 URL"""
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"图片不存在: {image_path}")

        suffix = path.suffix.lstrip(".").lower()
        if suffix == "jpg":
            suffix = "jpeg"
        content_type = f"image/{suffix}"
        image_bytes = path.read_bytes()

        # Step 1: 获取上传签名
        sign_data = self._get_signature(suffix)

        # Step 2: 上传到 OBS
        obs_host = sign_data["host"]
        policy = sign_data["policy"]
        access_id = sign_data["accessId"]
        signature = sign_data["signature"]
        dir_name = sign_data.get("dir", "direct")

        # 从 policy 中解析 key
        policy_decoded = json.loads(
            __import__("base64").b64decode(policy).decode()
        )
        key = policy_decoded["conditions"][2][2]  # "direct/xxx.png"

        # 构建 multipart 表单
        form_data = {
            "key": key,
            "policy": policy,
            "AccessKeyId": access_id,
            "signature": signature,
            "content-type": content_type,
        }

        files = {"file": (path.name, image_bytes, content_type)}

        with httpx.Client(timeout=30) as client:
            resp = client.post(
                obs_host,
                data=form_data,
                files=files,
            )
            if resp.status_code not in (200, 204):
                raise Exception(f"OBS 上传失败 (status={resp.status_code}): {resp.text[:300]}")

        # Step 3: 从签名响应中提取图片 URL
        image_url = f"{sign_data.get('hostname', obs_host)}{key}"
        # 优先用签名响应中返回的 hostname
        return image_url

    def _get_signature(self, suffix: str) -> dict:
        """获取上传签名"""
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                self.SIGNATURE_URL,
                headers=self._headers,
                json={
                    "imageTemplate": "",
                    "appName": self.APP_NAME,
                    "imageSuffix": suffix,
                },
            )
            data = resp.json()
            if data.get("code") != 200:
                raise Exception(f"获取签名失败: {data.get('msg', data)}")
            return data["data"]
