import random
import hashlib
import time
from typing import Dict, List, Tuple
import requests

from .base import BaseTranslator


class BaiduTranslator(BaseTranslator):
    """百度翻译API实现"""

    BATCH_SIZE = 20  # 每批翻译的条目数

    def __init__(self, app_id: str, secret_key: str):
        self.app_id = app_id
        self.secret_key = secret_key
        self.api_url = "https://fanyi-api.baidu.com/api/trans/vip/translate"

    def check_config(self) -> bool:
        if not self.app_id or not self.secret_key:
            print("[错误] 百度翻译的 app_id 或 secret_key 未配置，请检查 config.json")
            return False
        return True

    def _make_sign(self, query: str, salt: str) -> str:
        """生成签名"""
        sign_str = self.app_id + query + salt + self.secret_key
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest()

    def _translate_batch(self, texts_list: List[Tuple[str, str]]) -> Dict[str, str]:
        """
        翻译一批文本
        :param texts_list: [(key, english_text), ...]
        :return: {key: chinese_text}
        """
        # 将所有文本用换行符连接
        query = "\n".join(text for _, text in texts_list)
        salt = str(random.randint(10000, 99999))
        sign = self._make_sign(query, salt)

        params = {
            "q": query,
            "from": "en",
            "to": "zh",
            "appid": self.app_id,
            "salt": salt,
            "sign": sign,
        }

        try:
            response = requests.post(self.api_url, data=params, timeout=30)
            result = response.json()

            if "trans_result" not in result:
                error_msg = result.get("error_msg", "未知错误")
                error_code = result.get("error_code", "未知")
                print(f"[错误] 百度翻译API返回错误: [{error_code}] {error_msg}")
                return {}

            # 解析翻译结果
            translated_lines = [item["dst"] for item in result["trans_result"]]
            translated_dict = {}

            for i, (key, _) in enumerate(texts_list):
                if i < len(translated_lines):
                    translated_dict[key] = translated_lines[i]

            return translated_dict

        except requests.exceptions.RequestException as e:
            print(f"[错误] 百度翻译API请求失败: {e}")
            return {}
        except (KeyError, ValueError) as e:
            print(f"[错误] 解析百度翻译结果失败: {e}")
            return {}

    def translate(self, texts: Dict[str, str]) -> Dict[str, str]:
        """
        翻译文本，自动分批处理
        :param texts: {key: english_text}
        :return: {key: chinese_text}
        """
        if not texts:
            return {}

        items = list(texts.items())
        translated = {}
        total = len(items)

        for i in range(0, total, self.BATCH_SIZE):
            batch = items[i:i + self.BATCH_SIZE]
            batch_num = i // self.BATCH_SIZE + 1
            total_batches = (total + self.BATCH_SIZE - 1) // self.BATCH_SIZE
            print(f"  [百度翻译] 正在翻译第 {batch_num}/{total_batches} 批 ({len(batch)} 条)...")

            result = self._translate_batch(batch)
            translated.update(result)

            # 控制调用频率，避免被限制
            if i + self.BATCH_SIZE < total:
                time.sleep(1)

        return translated
