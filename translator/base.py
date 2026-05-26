from abc import ABC, abstractmethod
from typing import Dict


class BaseTranslator(ABC):
    """翻译器基类"""

    @abstractmethod
    def translate(self, texts: Dict[str, str]) -> Dict[str, str]:
        """
        翻译文本
        :param texts: 待翻译的字典 {key: english_text}
        :return: 翻译后的字典 {key: chinese_text}
        """
        pass

    @abstractmethod
    def check_config(self) -> bool:
        """
        检查翻译器配置是否有效
        :return: 配置是否有效
        """
        pass
