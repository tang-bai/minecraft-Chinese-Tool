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
from ftbquests_translator import process_ftbquests


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

    # 检查是否有临时文件夹中的翻译可继续（有zh_cn.json或en_us.json）
    temp_exists = False
    if os.path.isdir(TEMP_DIR):
        for d in os.listdir(TEMP_DIR):
            mod_path = os.path.join(TEMP_DIR, d)
            if os.path.isdir(mod_path):
                if os.path.isfile(os.path.join(mod_path, 'zh_cn.json')) or \
                   os.path.isfile(os.path.join(mod_path, 'en_us.json')):
                    temp_exists = True
                    break

    # ===== 主菜单 =====
    print("请选择操作:")
    print("  [1] 开始新汉化（扫描mod文件夹）")
    if temp_exists:
        print("  [2] 继续汉化temp文件夹中的未完成翻译")
    print("  [3] 翻译 FTB Quests 任务文本")
    print("  [4] 初始化配置文件")
    print("  [5] 退出")
    print()

    choice = input("请输入选项编号: ").strip()

    if choice == '1':
        pass  # 继续执行新汉化流程
    elif choice == '2' and temp_exists:
        continue_translate_temp(config)
        return
    elif choice == '3':
        run_ftbquests_translation(config)
        return
    elif choice == '4':
        init_config()
        return
    elif choice == '5':
        print("已退出")
        return
    else:
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


def continue_translate_temp(config: dict):
    """继续汉化temp文件夹中未完成的翻译"""
    print_banner()
    print("[继续汉化模式] 处理 temp 文件夹中的翻译文件\n")

    # 选择翻译引擎
    translator_type = config.get('translator', 'ai')
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
        pass
    else:
        print("[提示] 无效选项，使用当前配置")

    config['translator'] = translator_type

    # 创建翻译器和缓存
    translator = create_translator(config)
    cache = TranslationCache(CACHE_DIR)

    # 扫描temp文件夹，收集所有有en_us.json或zh_cn.json的mod目录
    mod_dirs = []
    for d in os.listdir(TEMP_DIR):
        mod_path = os.path.join(TEMP_DIR, d)
        if not os.path.isdir(mod_path):
            continue
        zh_cn_path = os.path.join(mod_path, 'zh_cn.json')
        en_us_path = os.path.join(mod_path, 'en_us.json')
        if os.path.isfile(zh_cn_path) or os.path.isfile(en_us_path):
            mod_dirs.append((d, mod_path))

    if not mod_dirs:
        print("[信息] temp文件夹中没有找到翻译文件")
        return

    print(f"\n[信息] 找到 {len(mod_dirs)} 个mod的翻译文件\n")

    # 先从en_us.json创建缺失的zh_cn.json（用英文原文填充，后续翻译覆盖）
    for modid, mod_path in mod_dirs:
        en_us_path = os.path.join(mod_path, 'en_us.json')
        zh_cn_path = os.path.join(mod_path, 'zh_cn.json')
        if os.path.isfile(en_us_path) and not os.path.isfile(zh_cn_path):
            try:
                with open(en_us_path, 'r', encoding='utf-8') as f:
                    en_us_data = json.load(f)
                # 创建zh_cn.json，值为空字符串，标记为待翻译
                zh_cn_data = {}
                for key, value in en_us_data.items():
                    if isinstance(value, str):
                        zh_cn_data[key] = value  # 先填入英文，后续翻译会覆盖
                    else:
                        zh_cn_data[key] = value
                with open(zh_cn_path, 'w', encoding='utf-8') as f:
                    json.dump(zh_cn_data, f, ensure_ascii=False, indent=2)
                print(f"  [新建] {modid}/zh_cn.json ← 从 en_us.json 创建 ({len(zh_cn_data)} 条)")
            except Exception as e:
                print(f"  [错误] {modid} - 创建zh_cn.json失败: {e}")

    total_translated = 0
    final_translations = {}

    for modid, mod_path in mod_dirs:
        zh_cn_path = os.path.join(mod_path, 'zh_cn.json')
        print(f"--- 处理 mod: {modid} ---")

        # 跳过没有zh_cn.json的mod（可能只有en_us.json且创建失败）
        if not os.path.isfile(zh_cn_path):
            print(f"  [跳过] zh_cn.json 不存在")
            continue

        # 加载当前的zh_cn.json
        try:
            with open(zh_cn_path, 'r', encoding='utf-8') as f:
                zh_cn_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"  [错误] 加载失败: {e}")
            continue

        # 加载en_us.json（如果存在）用于对比
        en_us_path = os.path.join(os.path.dirname(zh_cn_path), 'en_us.json')
        en_us_data = {}
        if os.path.isfile(en_us_path):
            try:
                with open(en_us_path, 'r', encoding='utf-8') as f:
                    en_us_data = json.load(f)
            except Exception:
                pass

        # 找出未翻译的条目
        # 条件：值为空/None/list/空字符串，或者值与en_us.json中的英文相同（未真正翻译）
        untranslated = {}
        for key, value in zh_cn_data.items():
            if isinstance(value, list):
                continue
            if not isinstance(value, str) or not value or value.strip() == '':
                untranslated[key] = key
            elif en_us_data and key in en_us_data:
                # 如果zh_cn的值与en_us的值完全相同，说明未翻译
                en_value = en_us_data[key]
                if isinstance(en_value, str) and value.strip() == en_value.strip():
                    untranslated[key] = value

        if not untranslated:
            print(f"  [完成] 所有 {len(zh_cn_data)} 条已翻译，跳过")
            final_translations[modid] = zh_cn_data
            continue

        print(f"  总条目: {len(zh_cn_data)}, 未翻译: {len(untranslated)}")

        # 先查缓存
        cached, uncached = cache.get_multiple(untranslated)
        zh_cn_data.update(cached)
        print(f"  从缓存匹配: {len(cached)} 条")
        print(f"  需要API翻译: {len(uncached)} 条")

        # 调用翻译API
        if uncached:
            print(f"  开始翻译 {len(uncached)} 条文本...")
            # 对于key即value的情况，翻译value
            to_translate = {k: v for k, v in uncached.items()}
            translated = translator.translate(to_translate)
            zh_cn_data.update(translated)
            total_translated += len(translated)
            cache.update_from_result(to_translate, translated)
            print(f"  翻译完成: {len(translated)}/{len(uncached)} 条")

        # 保存更新后的zh_cn.json
        with open(zh_cn_path, 'w', encoding='utf-8') as f:
            json.dump(zh_cn_data, f, ensure_ascii=False, indent=2)
        print(f"  [保存] {zh_cn_path}")

        final_translations[modid] = zh_cn_data

    # 保存缓存
    cache.save_cache()
    print(f"\n[信息] 翻译缓存已保存 ({cache.size} 条)")

    # 打包资源包
    pack_name = config.get('resource_pack_name', 'Mod中文翻译资源包')
    output_filename = f"{pack_name}.zip"
    output_path = os.path.join(BASE_DIR, output_filename)
    pack_description = config.get('resource_pack_description', '自动翻译的Mod中文语言包')
    game_version = config.get('game_version', '1.20.1')

    print(f"\n[Step 4/4] 打包资源包...")

    success = create_resource_pack(
        translations=final_translations,
        output_path=output_path,
        pack_description=pack_description,
        game_version=game_version
    )

    if success:
        print("\n" + "=" * 60)
        print("  ✅ 继续汉化完成！")
        print("=" * 60)
        print(f"\n  新翻译条目: {total_translated}")
        print(f"  输出文件: {output_path}")
    else:
        print("\n[错误] 资源包创建失败")
        sys.exit(1)

    print()
    input("按回车键退出...")


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

        # 获取temp中已有的modid列表（来自jar提取）
        existing_temp_modids = set()
        if os.path.isdir(TEMP_DIR):
            for d in os.listdir(TEMP_DIR):
                if os.path.isdir(os.path.join(TEMP_DIR, d)):
                    existing_temp_modids.add(d)

        # 判断导入的是文件夹还是zip
        if os.path.isdir(import_pack):
            # 判断是标准资源包文件夹(有assets目录)还是直接modid文件夹
            assets_dir = os.path.join(import_pack, 'assets')
            if os.path.isdir(assets_dir):
                # 标准资源包结构: assets/<modid>/lang/zh_cn.json
                for modid in os.listdir(assets_dir):
                    # 只复制temp中已有的modid
                    if modid not in existing_temp_modids:
                        continue
                    lang_dir = os.path.join(assets_dir, modid, 'lang')
                    if not os.path.isdir(lang_dir):
                        continue
                    zh_cn_src = os.path.join(lang_dir, 'zh_cn.json')
                    if os.path.isfile(zh_cn_src):
                        zh_cn_dst = os.path.join(TEMP_DIR, modid, 'zh_cn.json')
                        if os.path.isfile(zh_cn_dst):
                            print(f"  [跳过] {modid} - temp中已存在zh_cn.json")
                            continue
                        shutil.copy2(zh_cn_src, zh_cn_dst)
                        print(f"  [复制] {modid}/zh_cn.json → {zh_cn_dst}")
                        try:
                            with open(zh_cn_src, 'r', encoding='utf-8') as f:
                                existing_translations[modid] = json.load(f)
                        except Exception:
                            pass
            else:
                # 直接modid文件夹结构: <modid>/zh_cn.json
                for modid in os.listdir(import_pack):
                    # 只复制temp中已有的modid
                    if modid not in existing_temp_modids:
                        continue
                    mod_src_path = os.path.join(import_pack, modid)
                    if not os.path.isdir(mod_src_path):
                        continue
                    zh_cn_src = os.path.join(mod_src_path, 'zh_cn.json')
                    zh_cn_src_alt = os.path.join(mod_src_path, 'lang', 'zh_cn.json')
                    if not os.path.isfile(zh_cn_src) and os.path.isfile(zh_cn_src_alt):
                        zh_cn_src = zh_cn_src_alt
                    if os.path.isfile(zh_cn_src):
                        zh_cn_dst = os.path.join(TEMP_DIR, modid, 'zh_cn.json')
                        if os.path.isfile(zh_cn_dst):
                            print(f"  [跳过] {modid} - temp中已存在zh_cn.json")
                            continue
                        shutil.copy2(zh_cn_src, zh_cn_dst)
                        print(f"  [复制] {modid}/zh_cn.json → {zh_cn_dst}")
                        try:
                            with open(zh_cn_src, 'r', encoding='utf-8') as f:
                                existing_translations[modid] = json.load(f)
                        except Exception:
                            pass
        else:
            # zip形式：解析并只复制temp中已有的modid
            imported = import_from_path(import_pack)
            for modid, zh_cn_data in imported.items():
                if modid not in existing_temp_modids:
                    continue
                zh_cn_dst = os.path.join(TEMP_DIR, modid, 'zh_cn.json')
                if os.path.isfile(zh_cn_dst):
                    print(f"  [跳过] {modid} - temp中已存在zh_cn.json")
                    continue
                with open(zh_cn_dst, 'w', encoding='utf-8') as f:
                    json.dump(zh_cn_data, f, ensure_ascii=False, indent=2)
                print(f"  [复制] {modid}/zh_cn.json → {zh_cn_dst}")
                existing_translations[modid] = zh_cn_data
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

        # 检查temp中是否已有zh_cn.json（来自导入的汉化）
        zh_cn_existing_path = os.path.join(TEMP_DIR, modid, 'zh_cn.json')
        if os.path.isfile(zh_cn_existing_path):
            try:
                with open(zh_cn_existing_path, 'r', encoding='utf-8') as f:
                    existing_zh_cn = json.load(f)
                if existing_zh_cn:
                    print(f"  [跳过] temp中已有zh_cn.json ({len(existing_zh_cn)} 条)")
                    final_translations[modid] = existing_zh_cn
                    continue
            except Exception:
                pass

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

        # 保存 zh_cn.json 到临时文件夹
        zh_cn_temp_path = os.path.join(TEMP_DIR, modid, 'zh_cn.json')
        os.makedirs(os.path.dirname(zh_cn_temp_path), exist_ok=True)
        with open(zh_cn_temp_path, 'w', encoding='utf-8') as f:
            json.dump(zh_cn_result, f, ensure_ascii=False, indent=2)
        print(f"  [保存] zh_cn.json → {zh_cn_temp_path}")

    # 保存缓存
    cache.save_cache()
    print(f"\n[信息] 翻译缓存已保存 ({cache.size} 条)")

    print("\n[信息] 临时文件已保留在 temp 文件夹中（含 en_us.json 和 zh_cn.json）")

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
        print(f"  临时文件: {os.path.join(TEMP_DIR, '<modid>', 'zh_cn.json')}")
        print(f"\n  使用方法: 将资源包放入 .minecraft/resourcepacks 文件夹中")
    else:
        print("\n[错误] 资源包创建失败")
        sys.exit(1)

    # 等待用户确认后退出
    print()
    input("按回车键退出...")


def run_ftbquests_translation(config: dict):
    """FTB Quests 翻译流程"""
    print_banner()
    print("[FTB Quests 翻译模式] 翻译 snbt 任务文件\n")

    # 选择翻译引擎
    translator_type = config.get('translator', 'ai')
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
        pass
    else:
        print("[提示] 无效选项，使用当前配置")

    config['translator'] = translator_type

    # 输入 ftbquests 源目录路径
    print()
    print("请输入 FTB Quests 文件夹路径（包含 snbt 文件的目录）:")
    print("  示例: C:\\Users\\xxx\\.minecraft\\config\\ftbquests")
    quests_path = input("路径: ").strip().strip('"').strip("'")

    if not quests_path:
        print("[错误] 未输入路径，已退出")
        return

    if not os.path.isdir(quests_path):
        print(f"[错误] 路径不存在: {quests_path}")
        return

    # 输出目录
    output_dir = os.path.join(BASE_DIR, 'config', 'ftbquests')
    os.makedirs(output_dir, exist_ok=True)

    print()
    print("=" * 50)
    print(f"  源目录: {quests_path}")
    print(f"  输出目录: {output_dir}")
    print(f"  翻译引擎: {translator_type}")
    print("=" * 50)
    print()

    confirm = input("确认开始翻译？(Y/n): ").strip().lower()
    if confirm == 'n':
        print("已取消")
        return

    # 创建翻译器和缓存
    translator = create_translator(config)
    cache = TranslationCache(CACHE_DIR)

    print(f"\n[信息] 开始翻译 FTB Quests 文件...\n")

    total_files, total_translated, total_cached = process_ftbquests(
        quests_path, translator, cache, output_dir
    )

    # 保存缓存
    cache.save_cache()

    print("\n" + "=" * 60)
    print("  ✅ FTB Quests 翻译完成！")
    print("=" * 60)
    print(f"\n  统计信息:")
    print(f"    - 翻译文件数: {total_files}")
    print(f"    - API翻译条目: {total_translated}")
    print(f"    - 缓存命中条目: {total_cached}")
    print(f"\n  输出目录: {output_dir}")
    print(f"\n  使用方法: 将输出的 config/ftbquests 文件夹复制到")
    print(f"  Minecraft 实例目录中覆盖原文件")

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

        # 保存 zh_cn.json 到临时文件夹
        zh_cn_temp_path = os.path.join(TEMP_DIR, modid, 'zh_cn.json')
        os.makedirs(os.path.dirname(zh_cn_temp_path), exist_ok=True)
        with open(zh_cn_temp_path, 'w', encoding='utf-8') as f:
            json.dump(zh_cn_result, f, ensure_ascii=False, indent=2)
        print(f"  [保存] zh_cn.json → {zh_cn_temp_path}")

    # 保存缓存
    cache.save_cache()
    print(f"\n[信息] 翻译缓存已保存 ({cache.size} 条)")

    # 清理临时文件夹中的en_us.json（保留zh_cn.json）
    print("\n[信息] 清理临时文件中的en_us.json...")
    for modid_dir in os.listdir(TEMP_DIR):
        modid_path = os.path.join(TEMP_DIR, modid_dir)
        if os.path.isdir(modid_path):
            en_us_file = os.path.join(modid_path, 'en_us.json')
            if os.path.isfile(en_us_file):
                os.remove(en_us_file)
    print("  en_us.json 已清理，zh_cn.json 已保留在 temp 文件夹中")

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
        print(f"  临时文件: {os.path.join(TEMP_DIR, '<modid>', 'zh_cn.json')}")
        print(f"\n  使用方法: 将资源包放入 .minecraft/resourcepacks 文件夹中")
    else:
        print("\n[错误] 资源包创建失败")
        sys.exit(1)


if __name__ == '__main__':
    main()
