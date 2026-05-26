import os
import json
import zipfile
import tempfile
import shutil
from typing import Dict


def import_existing_pack(pack_path: str) -> Dict[str, Dict[str, str]]:
    """
    导入已有的汉化资源包（zip文件），提取其中的zh_cn.json文件
    :param pack_path: 资源包zip文件路径
    :return: {modid: {key: chinese_value}} 字典
    """
    if not os.path.isfile(pack_path):
        print(f"[错误] 资源包文件不存在: {pack_path}")
        return {}

    existing_translations = {}

    try:
        with zipfile.ZipFile(pack_path, 'r') as zf:
            # 查找所有 assets/*/lang/zh_cn.json
            for name in zf.namelist():
                parts = name.split('/')
                if len(parts) >= 4 and parts[0] == 'assets' and parts[2] == 'lang' and parts[3] == 'zh_cn.json':
                    modid = parts[1]
                    try:
                        content = zf.read(name)
                        json_content = json.loads(content.decode('utf-8'))
                        existing_translations[modid] = json_content
                        print(f"  [导入] {modid} - zh_cn.json ({len(json_content)} 条目)")
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        print(f"  [错误] {modid} - zh_cn.json 解析失败: {e}")
                    except Exception as e:
                        print(f"  [错误] {modid} - 读取失败: {e}")

    except zipfile.BadZipFile:
        print(f"[错误] 无法打开资源包文件(可能损坏): {pack_path}")
    except Exception as e:
        print(f"[错误] 处理资源包时出错: {pack_path} - {e}")

    if not existing_translations:
        print("[警告] 资源包中未找到任何 zh_cn.json 文件")
    else:
        print(f"\n[信息] 从资源包中导入了 {len(existing_translations)} 个mod的汉化")

    return existing_translations


def import_existing_pack_folder(pack_folder_path: str) -> Dict[str, Dict[str, str]]:
    """
    导入已有的汉化资源包（文件夹形式），提取其中的zh_cn.json文件
    :param pack_folder_path: 资源包文件夹路径
    :return: {modid: {key: chinese_value}} 字典
    """
    if not os.path.isdir(pack_folder_path):
        print(f"[错误] 资源包文件夹不存在: {pack_folder_path}")
        return {}

    existing_translations = {}
    assets_dir = os.path.join(pack_folder_path, 'assets')

    if not os.path.isdir(assets_dir):
        print(f"[错误] 资源包文件夹中未找到 assets 目录")
        return {}

    for modid in os.listdir(assets_dir):
        lang_dir = os.path.join(assets_dir, modid, 'lang')
        if os.path.isdir(lang_dir):
            zh_cn_path = os.path.join(lang_dir, 'zh_cn.json')
            if os.path.isfile(zh_cn_path):
                try:
                    with open(zh_cn_path, 'r', encoding='utf-8') as f:
                        json_content = json.load(f)
                    existing_translations[modid] = json_content
                    print(f"  [导入] {modid} - zh_cn.json ({len(json_content)} 条目)")
                except (json.JSONDecodeError, FileNotFoundError) as e:
                    print(f"  [错误] {modid} - zh_cn.json 读取失败: {e}")

    if not existing_translations:
        print("[警告] 资源包文件夹中未找到任何 zh_cn.json 文件")
    else:
        print(f"\n[信息] 从资源包文件夹中导入了 {len(existing_translations)} 个mod的汉化")

    return existing_translations


def merge_translations(
    en_us_data: Dict[str, str],
    existing_zh_cn: Dict[str, str]
) -> tuple:
    """
    比对en_us.json和已有的zh_cn.json，返回需要翻译的条目和已有翻译的条目
    :param en_us_data: en_us.json的内容 {key: english_value}
    :param existing_zh_cn: 已有的zh_cn.json内容 {key: chinese_value}
    :return: (need_translate, already_translated)
        - need_translate: 需要翻译的条目 {key: english_value}
        - already_translated: 已有翻译的条目 {key: chinese_value}
    """
    need_translate = {}
    already_translated = {}

    for key, en_value in en_us_data.items():
        if key in existing_zh_cn and existing_zh_cn[key]:
            # 已有翻译，跳过
            already_translated[key] = existing_zh_cn[key]
        else:
            # 需要翻译
            need_translate[key] = en_value

    return need_translate, already_translated


def import_from_path(import_path: str) -> Dict[str, Dict[str, str]]:
    """
    自动判断导入路径是zip文件还是文件夹，并导入汉化
    :param import_path: 资源包路径（zip文件或文件夹）
    :return: {modid: {key: chinese_value}}
    """
    if not os.path.exists(import_path):
        print(f"[错误] 导入路径不存在: {import_path}")
        return {}

    if os.path.isfile(import_path) and import_path.lower().endswith('.zip'):
        return import_existing_pack(import_path)
    elif os.path.isdir(import_path):
        return import_existing_pack_folder(import_path)
    else:
        print(f"[错误] 不支持的导入路径类型: {import_path}")
        print("  支持的类型: .zip 文件或资源包文件夹")
        return {}
