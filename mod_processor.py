import os
import json
import zipfile
from typing import Dict, List, Tuple


def scan_mods_folder(mods_path: str) -> List[str]:
    """
    扫描mods文件夹，返回所有jar文件路径
    :param mods_path: mods文件夹路径
    :return: jar文件路径列表
    """
    if not os.path.isdir(mods_path):
        print(f"[错误] mods文件夹不存在: {mods_path}")
        return []

    jar_files = []
    for filename in os.listdir(mods_path):
        if filename.endswith('.jar'):
            jar_files.append(os.path.join(mods_path, filename))

    print(f"[信息] 在 {mods_path} 中找到 {len(jar_files)} 个jar文件")
    return jar_files


def extract_lang_files(jar_path: str, temp_dir: str) -> Dict[str, str]:
    """
    从jar文件中提取en_us.json语言文件
    如果jar中已有zh_cn.json则跳过
    :param jar_path: jar文件路径
    :param temp_dir: 临时目录路径
    :return: {modid: en_us.json的临时路径} 提取成功的mod字典
    """
    extracted = {}

    try:
        with zipfile.ZipFile(jar_path, 'r') as zf:
            # 查找所有 assets/*/lang/ 目录下的语言文件
            lang_files = {}
            for name in zf.namelist():
                # 匹配 assets/<modid>/lang/en_us.json 或 assets/<modid>/lang/zh_cn.json
                parts = name.split('/')
                if len(parts) >= 4 and parts[0] == 'assets' and parts[2] == 'lang':
                    modid = parts[1]
                    filename = parts[3]
                    if filename == 'en_us.json':
                        lang_files.setdefault(modid, {})['en_us'] = name
                    elif filename == 'zh_cn.json':
                        lang_files.setdefault(modid, {})['zh_cn'] = name

            for modid, files in lang_files.items():
                # 如果已有zh_cn.json，跳过
                if 'zh_cn' in files:
                    print(f"  [跳过] {modid} - jar中已包含中文翻译 (zh_cn.json)")
                    continue

                # 提取en_us.json
                if 'en_us' in files:
                    en_us_path = files['en_us']
                    try:
                        content = zf.read(en_us_path)
                        # 尝试解析JSON确保文件有效
                        json_content = json.loads(content.decode('utf-8'))

                        # 创建临时目录并保存
                        mod_temp_dir = os.path.join(temp_dir, modid)
                        os.makedirs(mod_temp_dir, exist_ok=True)
                        temp_file_path = os.path.join(mod_temp_dir, 'en_us.json')

                        with open(temp_file_path, 'w', encoding='utf-8') as f:
                            json.dump(json_content, f, ensure_ascii=False, indent=2)

                        extracted[modid] = temp_file_path
                        print(f"  [提取] {modid} - en_us.json ({len(json_content)} 条目)")
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        print(f"  [错误] {modid} - en_us.json 解析失败: {e}")
                    except Exception as e:
                        print(f"  [错误] {modid} - 提取失败: {e}")

    except zipfile.BadZipFile:
        print(f"  [错误] 无法打开jar文件(可能损坏): {jar_path}")
    except Exception as e:
        print(f"  [错误] 处理jar文件时出错: {jar_path} - {e}")

    return extracted


def process_all_mods(mods_path: str, temp_dir: str) -> Dict[str, str]:
    """
    处理所有mod文件夹中的jar文件
    :param mods_path: mods文件夹路径
    :param temp_dir: 临时目录路径
    :return: {modid: en_us.json临时路径}
    """
    jar_files = scan_mods_folder(mods_path)
    if not jar_files:
        return {}

    all_extracted = {}
    skipped_count = 0
    error_count = 0

    print(f"\n[信息] 开始扫描jar文件中的语言文件...\n")

    for jar_path in jar_files:
        jar_name = os.path.basename(jar_path)
        print(f"处理: {jar_name}")

        before_count = len(all_extracted)
        extracted = extract_lang_files(jar_path, temp_dir)
        all_extracted.update(extracted)

        if len(all_extracted) == before_count and not extracted:
            # 可能是跳过或没有语言文件
            pass

    print(f"\n[信息] 扫描完成:")
    print(f"  - 提取语言文件的mod: {len(all_extracted)} 个")
    print(f"  - 总计处理jar文件: {len(jar_files)} 个")

    return all_extracted


def load_en_us_json(file_path: str) -> Dict[str, str]:
    """
    加载en_us.json文件
    :param file_path: 文件路径
    :return: {key: value} 字典
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"[错误] 加载文件失败 {file_path}: {e}")
        return {}
