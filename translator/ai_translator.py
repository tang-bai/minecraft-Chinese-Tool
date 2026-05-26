import json
import time
from typing import Dict, List, Tuple
import requests

from .base import BaseTranslator


class AITranslator(BaseTranslator):
    """OpenAI兼容API翻译器实现"""

    BATCH_SIZE = 30  # 每批翻译的条目数

    DEFAULT_SYSTEM_PROMPT = """你是一个专业的Minecraft模组翻译专家。请将以下英文游戏文本翻译为简体中文。

翻译要求：
1. 保持Minecraft中文社区的通用译名，如：
   - Crafting Table → 工作台
   - Redstone → 红石
   - Nether → 下界
   - Enderman → 末影人
   - Pickaxe → 镐
   - Sword → 剑
2. 物品/方块名称保留游戏风格，简洁明了
3. 界面文字（按钮、菜单等）符合中文习惯
4. 保留原文中的格式化代码（如 §a, §b 等）
5. 保留原文中的变量占位符（如 %s, %d, {0}, {name} 等）
6. 长度尽量与原文接近，避免过长影响界面显示
7. 对于专业术语保持一致性，同一mod中的相同词汇用相同的翻译
8. 只输出翻译结果，JSON格式与输入保持一致，key不变，只翻译value"""

    def __init__(self, api_url: str, api_key: str, model: str, system_prompt: str = ""):
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT

    def check_config(self) -> bool:
        if not self.api_url:
            print("[错误] AI API的地址未配置，请检查 config.json 中的 ai.api_url")
            return False
        if not self.api_key:
            print("[错误] AI API的密钥未配置，请检查 config.json 中的 ai.api_key")
            return False
        if not self.model:
            print("[错误] AI模型名称未配置，请检查 config.json 中的 ai.model")
            return False
        return True

    def _translate_batch(self, texts_list: List[Tuple[str, str]]) -> Dict[str, str]:
        """
        翻译一批文本
        :param texts_list: [(key, english_text), ...]
        :return: {key: chinese_text}
        """
        # 构造输入JSON
        input_dict = {key: text for key, text in texts_list}
        input_json = json.dumps(input_dict, ensure_ascii=False, indent=2)

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": input_json}
        ]

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 4096
        }

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            result = response.json()

            content = result["choices"][0]["message"]["content"].strip()

            # 尝试从返回内容中提取JSON
            # 处理可能被markdown代码块包裹的情况
            if content.startswith("```"):
                # 去掉markdown代码块标记
                lines = content.split("\n")
                # 移除第一行和最后一行的```标记
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                content = "\n".join(lines)

            translated_dict = json.loads(content)

            # 确保所有key都是字符串类型，且与输入匹配
            result_dict = {}
            for key, _ in texts_list:
                str_key = str(key)
                if str_key in translated_dict:
                    result_dict[key] = str(translated_dict[str_key])
                elif key in translated_dict:
                    result_dict[key] = str(translated_dict[key])

            return result_dict

        except requests.exceptions.RequestException as e:
            print(f"[错误] AI API请求失败: {e}")
            return {}
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            print(f"[错误] 解析AI翻译结果失败: {e}")
            if 'content' in dir():
                print(f"[调试] AI返回的原始内容: {content[:500]}")
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
            print(f"  [AI翻译] 正在翻译第 {batch_num}/{total_batches} 批 ({len(batch)} 条)...")

            result = self._translate_batch(batch)
            translated.update(result)

            # 控制调用频率
            if i + self.BATCH_SIZE < total:
                time.sleep(1)

        return translated
