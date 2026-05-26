import os
import json
from typing import Dict, Optional


class TranslationCache:
    """翻译缓存管理器，避免重复翻译"""

    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, 'translation_cache.json')
        self.cache: Dict[str, str] = {}
        self._load_cache()

    def _load_cache(self):
        """加载缓存文件"""
        if os.path.isfile(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                print(f"[信息] 已加载翻译缓存 ({len(self.cache)} 条)")
            except (json.JSONDecodeError, FileNotFoundError):
                self.cache = {}
                print("[警告] 缓存文件损坏，将重新创建")

    def save_cache(self):
        """保存缓存到文件"""
        os.makedirs(self.cache_dir, exist_ok=True)
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[警告] 保存缓存失败: {e}")

    def get(self, key: str) -> Optional[str]:
        """从缓存中获取翻译"""
        return self.cache.get(key)

    def get_multiple(self, texts: Dict[str, str]) -> tuple:
        """
        批量查找缓存
        :param texts: {key: english_text}
        :return: (cached, uncached)
            - cached: 缓存命中 {key: chinese_text}
            - uncached: 未命中 {key: english_text}
        """
        cached = {}
        uncached = {}

        for key, en_value in texts.items():
            cached_value = self.cache.get(en_value)
            if cached_value:
                cached[key] = cached_value
            else:
                uncached[key] = en_value

        return cached, uncached

    def update(self, en_zh_pairs: Dict[str, str]):
        """
        更新缓存
        :param en_zh_pairs: {english_text: chinese_text}
        """
        self.cache.update(en_zh_pairs)

    def update_from_result(self, original_texts: Dict[str, str], translated: Dict[str, str]):
        """
        根据翻译结果更新缓存
        :param original_texts: 原始文本 {key: english_text}
        :param translated: 翻译结果 {key: chinese_text}
        """
        for key in translated:
            if key in original_texts:
                en_text = original_texts[key]
                zh_text = translated[key]
                self.cache[en_text] = zh_text

    @property
    def size(self) -> int:
        return len(self.cache)
