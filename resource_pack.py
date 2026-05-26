import os
import json
import zipfile
from typing import Dict


# pack.mcmeta 模板
PACK_MCMETA_TEMPLATE = {
    "pack": {
        "pack_format": 15,
        "description": ""
    }
}

# 支持的game_version到pack_format的映射
PACK_FORMAT_MAP = {
    "1.6.1": 1, "1.6.2": 1, "1.6.4": 1,
    "1.7.2": 1, "1.7.4": 1, "1.7.5": 1, "1.7.10": 1,
    "1.8": 1, "1.8.1": 1, "1.8.2": 1, "1.8.3": 1, "1.8.4": 1, "1.8.5": 1, "1.8.6": 1, "1.8.7": 1, "1.8.8": 1, "1.8.9": 1,
    "1.9": 2, "1.9.1": 2, "1.9.2": 2, "1.9.3": 2, "1.9.4": 2,
    "1.10": 2, "1.10.1": 2, "1.10.2": 2,
    "1.11": 3, "1.11.1": 3, "1.11.2": 3,
    "1.12": 3, "1.12.1": 3, "1.12.2": 3,
    "1.13": 4, "1.13.1": 4, "1.13.2": 4,
    "1.14": 4, "1.14.1": 4, "1.14.2": 4, "1.14.3": 4, "1.14.4": 4,
    "1.15": 5, "1.15.1": 5, "1.15.2": 5,
    "1.16": 5, "1.16.1": 5, "1.16.2": 5, "1.16.3": 5, "1.16.4": 5, "1.16.5": 5,
    "1.17": 7, "1.17.1": 7,
    "1.18": 8, "1.18.1": 8, "1.18.2": 8,
    "1.19": 9, "1.19.1": 9, "1.19.2": 9, "1.19.3": 12, "1.19.4": 13,
    "1.20": 15, "1.20.1": 15, "1.20.2": 18, "1.20.3": 22, "1.20.4": 22, "1.20.5": 32, "1.20.6": 32,
    "1.21": 34, "1.21.1": 34, "1.21.2": 34, "1.21.3": 34, "1.21.4": 46,
}


def get_pack_format(game_version: str) -> int:
    """
    根据游戏版本获取pack_format
    :param game_version: 游戏版本号，如 "1.20.1"
    :return: pack_format值
    """
    if game_version in PACK_FORMAT_MAP:
        return PACK_FORMAT_MAP[game_version]
    
    # 尝试匹配主版本号
    for version, fmt in PACK_FORMAT_MAP.items():
        if game_version.startswith(version.rsplit('.', 1)[0]):
            return fmt
    
    # 默认使用较新版本的format
    print(f"[警告] 未知的游戏版本 {game_version}，使用默认pack_format=15")
    return 15


def create_resource_pack(
    translations: Dict[str, Dict[str, str]],
    output_path: str,
    pack_name: str = "Mod中文翻译资源包",
    pack_description: str = "自动翻译的Mod中文语言包",
    game_version: str = "1.20.1"
) -> bool:
    """
    创建Minecraft资源包（zip文件）
    :param translations: {modid: {key: chinese_value}}
    :param output_path: 输出zip文件路径
    :param pack_name: 资源包名称
    :param pack_description: 资源包描述
    :param game_version: 游戏版本号
    :return: 是否成功
    """
    if not translations:
        print("[错误] 没有翻译内容可打包")
        return False

    pack_format = get_pack_format(game_version)

    try:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 创建 pack.mcmeta
            pack_mcmeta = {
                "pack": {
                    "pack_format": pack_format,
                    "description": f"{pack_description} §7({game_version})"
                }
            }
            zf.writestr("pack.mcmeta", json.dumps(pack_mcmeta, ensure_ascii=False, indent=2))

            # 添加每个mod的zh_cn.json
            total_keys = 0
            for modid, zh_cn_data in translations.items():
                if not zh_cn_data:
                    continue
                
                lang_path = f"assets/{modid}/lang/zh_cn.json"
                content = json.dumps(zh_cn_data, ensure_ascii=False, indent=2)
                zf.writestr(lang_path, content)
                total_keys += len(zh_cn_data)
                print(f"  [打包] {modid} - {len(zh_cn_data)} 条目")

        file_size = os.path.getsize(output_path)
        file_size_str = _format_size(file_size)

        print(f"\n[信息] 资源包创建成功:")
        print(f"  - 文件: {output_path}")
        print(f"  - 大小: {file_size_str}")
        print(f"  - 包含mod: {len(translations)} 个")
        print(f"  - 总翻译条目: {total_keys} 条")
        print(f"  - 游戏版本: {game_version} (pack_format: {pack_format})")

        return True

    except Exception as e:
        print(f"[错误] 创建资源包失败: {e}")
        return False


def _format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
