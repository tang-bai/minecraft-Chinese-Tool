#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minecraft Mod 自动汉化工具
自动扫描mod文件夹中的jar文件，提取en_us.json并翻译为中文，打包为资源包
"""

import os
import sys
import json
import shutil
import argparse
from typing import Optional

from mod_processor import process_all_mods, load_en_us_json
from import_handler import import_from_path, merge_translations
from cache import TranslationCache
from translator import BaiduTranslator, AITranslator
from resource_pack import create_resource_pack


# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')
CACHE_DIR = os.path.join(BASE_DIR, 'cache')
TEMP_DIR = os.path.join(BASE_DIR, 'temp')


def load_config() -> dict:
    """加载配置文件"""
    if not os.path.isfile(CONFIG_FILE):
        print(f"[错误] 配置文件不存在: {CONFIG_FILE}")
        print("请运行 python main.py --init 生成配置文件模板")
        sys.exit(1)

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"[错误] 配置文件加载失败: {e}")
        sys.exit(1)


def init_config():
    """初始化配置文件"""
    if os.path.isfile(CONFIG_FILE):
        overwrite = input(f"配置文件已存在: {CONFIG_FILE}\n是否覆盖？(y/N): ").strip().lower()
        if overwrite != 'y':
            print("已取消")
            return

    config = {
        "translator": "ai",
        "baidu": {
            "app_id": "",
            "secret_key": ""
        },
        "ai": {
            "api_url": "https://api.openai.com/v1/chat/completions",
            "api_key": "",
            "model": "gpt-4o-mini",
            "system_prompt": ""
        },
        "resource_pack_name": "Mod中文翻译资源包",
        "resource_pack_description": "自动翻译的Mod中文语言包",
        "game_version": "1.20.1"
    }

    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"[信息] 配置文件已生成: {CONFIG_FILE}")
    print("请编辑配置文件，填入翻译API的密钥信息")


def create_translator(config: dict):
    """根据配置创建翻译器实例"""
    translator_type = config.get('translator', 'ai').lower()

    if translator_type == 'baidu':
        baidu_config = config.get('baidu', {})
        translator = BaiduTranslator(
            app_id=baidu_config.get('app_id', ''),
            secret_key=baidu_config.get('secret_key', '')
        )
    elif translator_type == 'ai':
        ai_config = config.get('ai', {})
        translator = AITranslator(
            api_url=ai_config.get('api_url', ''),
            api_key=ai_config.get('api_key', ''),
            model=ai_config.get('model', ''),
            system_prompt=ai_config.get('system_prompt', '')
        )
    else:
        print(f"[错误] 不支持的翻译器类型: {translator_type}")
        print("支持的类型: baidu, ai")
        sys.exit(1)

    if not translator.check_config():
        sys.exit(1)

    return translator


def print_banner():
    """打印工具横幅"""
    print("=" * 60)
    print("  Minecraft Mod 自动汉化工具")
    print("  自动扫描 → 提取语言文件 → 翻译 → 打包资源包")
    print("=" * 60)
    print()


def find_minecraft_mods_path() -> str:
    """尝试自动查找Minecraft的mods文件夹"""
    username = os.environ.get('USERNAME', '')
    possible_paths = [
        os.path.join(os.environ.get('APPDATA', ''), '.minecraft', 'mods'),
        os.path.join('C:\\Users', username, 'AppData', 'Roaming', '.minecraft', 'mods'),
    ]
    for path in possible_paths:
        if os.path.isdir(path):
            return path
    return ''


def interactive_mode():
    """交互式模式 - 通过菜单引导用户操作"""
    print_banner()

    # 加载配置
    config = load_config()

    # ===== 主菜单 =====
    print("请选择操作:")
    print("  [1] 开始汉化（扫描mod文件夹）")
    print("  [2] 初始化配置文件")
    print("  [3] 退出")
    print()

    choice = input("请输入选项编号 (1/2/3): ").strip()

    if choice == '2':
        init_config()
        return
    elif choice == '3':
        print("已退出")
        return
    elif choice != '1':
        print("[错误] 无效选项")
        return

    # ===== 选择mod文件夹 =====
    default_path = find_minecraft_mods_path()
    print()
    if default_path:
        print(f"检测到Minecraft mods文件夹: {default_path}")
        use_default = input(f"是否使用此路径？(Y/n): ").strip().lower()
        if use_default == 'n':
            default_path = ''

    if not default_path:
        print("请输入mod文件夹的完整路径:")
        mods_path = input("路径: ").strip().strip('"').strip("'")
        if not mods_path:
            print("[错误] 未输入路径，已退出")
            return
    else:
        mods_path = default_path

    if not os.path.isdir(mods_path):
        print(f"[错误] 路径不存在: {mods_path}")
        return

    # ===== 选择翻译引擎 =====
    translator_type = config.get('translator', 'ai')
    print()
    print(f"当前翻译引擎: {translator_type}")
    print("  [1] AI翻译 (OpenAI兼容API)")
    print("  [2] 百度翻译")
    print("  [3] 使用当前配置")
    print()

    translator_choice = input("请选择翻译引擎 (1/2/3): ").strip()
    if translator_choice == '1':
        translator_type = 'ai'
    elif translator_choice == '2':
        translator_type = 'baidu'
    elif translator_choice == '3':
        pass  # 使用当前配置
    else:
        print("[提示] 无效选项，使用当前配置")

    config['translator'] = translator_type

    # ===== 是否导入已有汉化 =====
    print()
    print("是否导入已有的汉化资源包？（可跳过已翻译内容，减少API调用）")
    print("  [1] 不导入，直接翻译")
    print("  [2] 导入已有汉化资源包（zip文件或文件夹）")
    print()

    import_choice = input("请选择 (1/2): ").strip()
    import_pack: Optional[str] = None
    if import_choice == '2':
        print("请输入汉化资源包的路径（zip文件或文件夹）:")
        import_path = input("路径: ").strip().strip('"').strip("'")
        if import_path and os.path.exists(import_path):
            import_pack = import_path
        elif import_path:
            print(f"[警告] 路径不存在: {import_path}，将跳过导入")

    # ===== 确认并开始 =====
    print()
    print("=" * 50)
    print(f"  mod文件夹: {mods_path}")
    print(f"  翻译引擎: {translator_type}")
    print(f"  导入汉化: {import_pack if import_pack else '无'}")
    print("=" * 50)
    print()

    confirm = input("确认开始汉化？(Y/n): ").strip().lower()
    if confirm == 'n':
        print("已取消")
        return

    # 调用核心处理流程
    run_process(config, mods_path, import_pack)


def run_process(config: dict, mods_path: str, import_pack: Optional[str] = None):
    """核心处理流程"""
    # 确定输出文件名
    pack_name = config.get('resource_pack_name', 'Mod中文翻译资源包')
    output_filename = f"{pack_name}.zip"
    output_path = os.path.join(BASE_DIR, output_filename)

    # 初始化翻译缓存
    cache = TranslationCache(CACHE_DIR)

    # ========== Step 1: 扫描并提取语言文件 ==========
    print("[Step 1/4] 扫描mod文件夹，提取语言文件...")
    print(f"  mod路径: {mods_path}\n")

    # 清理临时目录
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR, exist_ok=True)

    extracted_mods = process_all_mods(mods_path, TEMP_DIR)

    if not extracted_mods:
        print("\n[信息] 未找到需要翻译的语言文件")
        print("  - 所有mod可能都已有中文翻译")
        print("  - 或者mod文件夹中没有包含语言文件的jar")
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
        return

    print(f"\n[信息] 共提取 {len(extracted_mods)} 个mod的语言文件")

    # ========== Step 2: 导入已有汉化 ==========
    print("\n[Step 2/4] 检查已有汉化...")
    existing_translations = {}

    if import_pack:
        print(f"  导入路径: {import_pack}")
        existing_translations = import_from_path(import_pack)
    else:
        print("  未指定导入汉化包，跳过")

    # ========== Step 3: 比对并翻译 ==========
    print("\n[Step 3/4] 翻译语言文件...")
    translator = create_translator(config)

    final_translations = {}
    total_cached = 0
    total_imported = 0
    total_translated = 0
    total_keys = 0

    for modid, en_us_path in extracted_mods.items():
        print(f"\n--- 处理 mod: {modid} ---")

        # 加载en_us.json
        en_us_data = load_en_us_json(en_us_path)
        if not en_us_data:
            print(f"  [跳过] en_us.json 为空或加载失败")
            continue

        total_keys += len(en_us_data)
        zh_cn_result = {}

        # 比对导入的汉化
        if modid in existing_translations:
            need_translate, already_translated = merge_translations(
                en_us_data, existing_translations[modid]
            )
            zh_cn_result.update(already_translated)
            total_imported += len(already_translated)
            print(f"  从导入汉化中匹配: {len(already_translated)} 条")
            print(f"  仍需翻译: {len(need_translate)} 条")
        else:
            need_translate = en_us_data.copy()

        # 查找翻译缓存
        if need_translate:
            cached, uncached = cache.get_multiple(need_translate)
            zh_cn_result.update(cached)
            total_cached += len(cached)
            print(f"  从缓存中匹配: {len(cached)} 条")
            print(f"  需要调用API翻译: {len(uncached)} 条")

            # 调用翻译API
            if uncached:
                print(f"  开始翻译 {len(uncached)} 条文本...")
                translated = translator.translate(uncached)
                zh_cn_result.update(translated)
                total_translated += len(translated)

                # 更新缓存
                cache.update_from_result(uncached, translated)
                print(f"  翻译完成: {len(translated)}/{len(uncached)} 条")
        else:
            print(f"  全部从导入汉化中匹配，无需翻译")

        final_translations[modid] = zh_cn_result

    # 保存缓存
    cache.save_cache()
    print(f"\n[信息] 翻译缓存已保存 ({cache.size} 条)")

    # 删除临时文件夹中的en_us.json
    print("\n[信息] 清理临时文件...")
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    print("  临时文件已清理")

    # ========== Step 4: 打包资源包 ==========
    print(f"\n[Step 4/4] 打包资源包...")

    pack_description = config.get('resource_pack_description', '自动翻译的Mod中文语言包')
    game_version = config.get('game_version', '1.20.1')

    success = create_resource_pack(
        translations=final_translations,
        output_path=output_path,
        pack_description=pack_description,
        game_version=game_version
    )

    if success:
        print("\n" + "=" * 60)
        print("  ✅ 汉化资源包制作完成！")
        print("=" * 60)
        print(f"\n  统计信息:")
        print(f"    - 处理mod数量: {len(final_translations)}")
        print(f"    - 总翻译条目: {total_keys}")
        print(f"    - 从导入汉化匹配: {total_imported}")
        print(f"    - 从缓存匹配: {total_cached}")
        print(f"    - API翻译: {total_translated}")
        print(f"\n  输出文件: {output_path}")
        print(f"\n  使用方法: 将资源包放入 .minecraft/resourcepacks 文件夹中")
    else:
        print("\n[错误] 资源包创建失败")
        sys.exit(1)

    # 等待用户确认后退出
    print()
    input("按回车键退出...")


def main():
    # 如果没有命令行参数，进入交互式模式
    if len(sys.argv) == 1:
        interactive_mode()
        return

    parser = argparse.ArgumentParser(
        description='Minecraft Mod 自动汉化工具 - 自动翻译mod语言文件并打包为资源包',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py
      进入交互式模式（推荐）

  python main.py --init
      生成配置文件模板

  python main.py --mods-path "C:\\Users\\xxx\\.minecraft\\mods"
      扫描mod文件夹，翻译并打包

  python main.py --mods-path ./mods --import-pack 汉化包.zip
      导入已有汉化包，只翻译缺失部分

  python main.py --mods-path ./mods --translator baidu --output 中文包.zip
      使用百度翻译，指定输出文件名

  python main.py --mods-path ./mods --import-pack 已有汉化.zip --no-translate
      只导入已有汉化，不调用翻译API
        """
    )

    parser.add_argument('--init', action='store_true',
                        help='生成配置文件模板')
    parser.add_argument('--mods-path', type=str,
                        help='mod文件夹路径')
    parser.add_argument('--import-pack', type=str, dest='import_pack',
                        help='导入已有的汉化资源包（zip文件或文件夹路径）')
    parser.add_argument('--translator', type=str, choices=['baidu', 'ai'],
                        help='翻译引擎类型 (baidu/ai)，覆盖配置文件中的设置')
    parser.add_argument('--output', '-o', type=str,
                        help='输出资源包文件名（默认: Mod中文翻译资源包.zip）')
    parser.add_argument('--no-translate', action='store_true', dest='no_translate',
                        help='不调用翻译API，只使用导入的汉化和缓存')

    args = parser.parse_args()

    print_banner()

    # 初始化配置
    if args.init:
        init_config()
        return

    # 检查必要参数
    if not args.mods_path:
        parser.print_help()
        print("\n[错误] 请指定mod文件夹路径: --mods-path <路径>")
        sys.exit(1)

    # 加载配置
    config = load_config()

    # 覆盖翻译器类型
    if args.translator:
        config['translator'] = args.translator

    # 确定输出文件名
    output_filename = args.output
    if not output_filename:
        pack_name = config.get('resource_pack_name', 'Mod中文翻译资源包')
        output_filename = f"{pack_name}.zip"

    # 确保输出文件名以.zip结尾
    if not output_filename.endswith('.zip'):
        output_filename += '.zip'

    output_path = os.path.join(BASE_DIR, output_filename)

    # 初始化翻译缓存
    cache = TranslationCache(CACHE_DIR)

    # ========== Step 1: 扫描并提取语言文件 ==========
    print("[Step 1/4] 扫描mod文件夹，提取语言文件...")
    print(f"  mod路径: {args.mods_path}\n")

    # 清理临时目录
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR, exist_ok=True)

    extracted_mods = process_all_mods(args.mods_path, TEMP_DIR)

    if not extracted_mods:
        print("\n[信息] 未找到需要翻译的语言文件")
        print("  - 所有mod可能都已有中文翻译")
        print("  - 或者mod文件夹中没有包含语言文件的jar")
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
        return

    print(f"\n[信息] 共提取 {len(extracted_mods)} 个mod的语言文件")

    # ========== Step 2: 导入已有汉化 ==========
    print("\n[Step 2/4] 检查已有汉化...")
    existing_translations = {}

    if args.import_pack:
        print(f"  导入路径: {args.import_pack}")
        existing_translations = import_from_path(args.import_pack)
    else:
        print("  未指定导入汉化包，跳过")

    # ========== Step 3: 比对并翻译 ==========
    print("\n[Step 3/4] 翻译语言文件...")
    translator = None
    if not args.no_translate:
        translator = create_translator(config)

    final_translations = {}
    total_cached = 0
    total_imported = 0
    total_translated = 0
    total_keys = 0

    for modid, en_us_path in extracted_mods.items():
        print(f"\n--- 处理 mod: {modid} ---")

        # 加载en_us.json
        en_us_data = load_en_us_json(en_us_path)
        if not en_us_data:
            print(f"  [跳过] en_us.json 为空或加载失败")
            continue

        total_keys += len(en_us_data)
        zh_cn_result = {}

        # 比对导入的汉化
        if modid in existing_translations:
            need_translate, already_translated = merge_translations(
                en_us_data, existing_translations[modid]
            )
            zh_cn_result.update(already_translated)
            total_imported += len(already_translated)
            print(f"  从导入汉化中匹配: {len(already_translated)} 条")
            print(f"  仍需翻译: {len(need_translate)} 条")
        else:
            need_translate = en_us_data.copy()

        # 查找翻译缓存
        if need_translate:
            cached, uncached = cache.get_multiple(need_translate)
            zh_cn_result.update(cached)
            total_cached += len(cached)
            print(f"  从缓存中匹配: {len(cached)} 条")
            print(f"  需要调用API翻译: {len(uncached)} 条")

            # 调用翻译API
            if uncached and translator:
                print(f"  开始翻译 {len(uncached)} 条文本...")
                translated = translator.translate(uncached)
                zh_cn_result.update(translated)
                total_translated += len(translated)

                # 更新缓存
                cache.update_from_result(uncached, translated)
                print(f"  翻译完成: {len(translated)}/{len(uncached)} 条")
            elif uncached and not translator:
                print(f"  [警告] 有 {len(uncached)} 条文本未翻译（已禁用翻译API）")
        else:
            print(f"  全部从导入汉化中匹配，无需翻译")

        final_translations[modid] = zh_cn_result

    # 保存缓存
    cache.save_cache()
    print(f"\n[信息] 翻译缓存已保存 ({cache.size} 条)")

    # 删除临时文件夹中的en_us.json
    print("\n[信息] 清理临时文件...")
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    print("  临时文件已清理")

    # ========== Step 4: 打包资源包 ==========
    print(f"\n[Step 4/4] 打包资源包...")

    pack_description = config.get('resource_pack_description', '自动翻译的Mod中文语言包')
    game_version = config.get('game_version', '1.20.1')

    success = create_resource_pack(
        translations=final_translations,
        output_path=output_path,
        pack_description=pack_description,
        game_version=game_version
    )

    if success:
        print("\n" + "=" * 60)
        print("  ✅ 汉化资源包制作完成！")
        print("=" * 60)
        print(f"\n  统计信息:")
        print(f"    - 处理mod数量: {len(final_translations)}")
        print(f"    - 总翻译条目: {total_keys}")
        print(f"    - 从导入汉化匹配: {total_imported}")
        print(f"    - 从缓存匹配: {total_cached}")
        print(f"    - API翻译: {total_translated}")
        print(f"\n  输出文件: {output_path}")
        print(f"\n  使用方法: 将资源包放入 .minecraft/resourcepacks 文件夹中")
    else:
        print("\n[错误] 资源包创建失败")
        sys.exit(1)


if __name__ == '__main__':
    main()
