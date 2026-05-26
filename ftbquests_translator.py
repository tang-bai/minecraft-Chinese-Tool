#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTB Quests snbt 文件翻译模块
解析 config/ftbquests 中的 snbt 文件，翻译任务标题、描述、章节名称
"""

import os
import re
import json
from typing import Dict, List, Tuple, Optional


def scan_snbt_files(quests_path: str) -> List[str]:
    """
    扫描 ftbquests 目录中的所有 snbt 文件
    :param quests_path: ftbquests 目录路径
    :return: snbt 文件路径列表
    """
    snbt_files = []
    for root, dirs, files in os.walk(quests_path):
        for filename in files:
            if filename.endswith('.snbt'):
                snbt_files.append(os.path.join(root, filename))
    return snbt_files


def extract_translatable_texts(content: str) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    """
    从 snbt 文件内容中提取需要翻译的文本
    :param content: snbt 文件内容
    :return: (string_fields, list_fields)
        - string_fields: {field_key: text} 需要翻译的字符串字段
        - list_fields: {field_key: [line1, line2, ...]} 需要翻译的列表字段
    """
    string_fields = {}
    list_fields = {}

    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 匹配 quest_title: "text"
        title_match = re.match(r'^(\s*)(quest_title|title)\s*=\s*"(.+)"\s*$', line)
        if title_match:
            key = title_match.group(2)
            value = title_match.group(3)
            # 排除已经翻译的中文文本
            if not _is_chinese(value):
                string_fields[f"line_{i}_{key}"] = value
            i += 1
            continue

        # 匹配 chapter_title 等字段
        chapter_match = re.match(r'^(\s*)(chapter_title|subtitle)\s*=\s*"(.+)"\s*$', line)
        if chapter_match:
            key = chapter_match.group(2)
            value = chapter_match.group(3)
            if not _is_chinese(value):
                string_fields[f"line_{i}_{key}"] = value
            i += 1
            continue

        # 匹配 quest_desc: [ 列表开始
        desc_match = re.match(r'^(\s*)(quest_desc)\s*:\s*\[', line)
        if desc_match:
            key = "quest_desc"
            indent = desc_match.group(1)
            desc_lines = []
            i += 1
            while i < len(lines):
                desc_line = lines[i]
                desc_stripped = desc_line.strip()
                if desc_stripped == ']':
                    break
                # 提取引号内的文本
                text_match = re.match(r'^\s*"(.*)"\s*,?\s*$', desc_line)
                if text_match:
                    text = text_match.group(1)
                    desc_lines.append(text)
                else:
                    desc_lines.append(None)  # 非文本行（如空行）
                i += 1

            # 检查是否有需要翻译的非空行
            has_translatable = any(line and line.strip() and not _is_chinese(line) for line in desc_lines if line is not None)
            if has_translatable:
                list_fields[f"line_{desc_match.start()}_{key}"] = desc_lines
            i += 1
            continue

        # 匹配 description: [ 列表（另一种格式）
        desc_match2 = re.match(r'^(\s*)(description)\s*:\s*\[', line)
        if desc_match2:
            key = "description"
            desc_lines = []
            i += 1
            while i < len(lines):
                desc_line = lines[i]
                desc_stripped = desc_line.strip()
                if desc_stripped == ']':
                    break
                text_match = re.match(r'^\s*"(.*)"\s*,?\s*$', desc_line)
                if text_match:
                    text = text_match.group(1)
                    desc_lines.append(text)
                else:
                    desc_lines.append(None)
                i += 1

            has_translatable = any(line and line.strip() and not _is_chinese(line) for line in desc_lines if line is not None)
            if has_translatable:
                list_fields[f"line_{desc_match2.start()}_{key}"] = desc_lines
            i += 1
            continue

        i += 1

    return string_fields, list_fields


def _is_chinese(text: str) -> bool:
    """判断文本是否已经是中文"""
    if not text:
        return False
    chinese_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    # 如果中文字符占比超过30%，认为已经是中文
    return chinese_count > len(text) * 0.3


def translate_snbt_file(
    file_path: str,
    translator,
    cache,
    output_dir: str
) -> Tuple[int, int]:
    """
    翻译单个 snbt 文件
    :param file_path: snbt 文件路径
    :param translator: 翻译器实例
    :param cache: 缓存实例
    :param output_dir: 输出目录
    :return: (翻译条目数, 缓存命中数)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    string_fields, list_fields = extract_translatable_texts(content)

    if not string_fields and not list_fields:
        return 0, 0

    # 准备翻译文本
    texts_to_translate = {}
    field_map = {}  # {translated_key: (field_type, original_key, index)}

    # 字符串字段
    for field_key, text in string_fields.items():
        texts_to_translate[field_key] = text
        field_map[field_key] = ('string', field_key, 0)

    # 列表字段
    for field_key, lines in list_fields.items():
        for idx, line in enumerate(lines):
            if line is not None and line.strip() and not _is_chinese(line):
                translate_key = f"{field_key}_{idx}"
                texts_to_translate[translate_key] = line
                field_map[translate_key] = ('list', field_key, idx)

    if not texts_to_translate:
        return 0, 0

    # 查缓存
    cached, uncached = cache.get_multiple(texts_to_translate)

    # 翻译未缓存的文本
    translated = {}
    if uncached:
        translated = translator.translate(uncached)
        cache.update_from_result(uncached, translated)

    # 合并翻译结果
    all_translated = {**cached, **translated}

    # 将翻译结果写回文件内容
    lines = content.split('\n')
    modified_lines = list(lines)  # 复制一份

    for translate_key, (field_type, original_key, idx) in field_map.items():
        zh_text = all_translated.get(translate_key)
        if not zh_text:
            continue

        if field_type == 'string':
            # 找到原始行号
            line_num = int(original_key.split('_')[1])
            if line_num < len(modified_lines):
                # 替换引号内的文本
                old_line = modified_lines[line_num]
                new_line = re.sub(
                    r'(=\s*")(.+)(")',
                    lambda m: m.group(1) + zh_text + m.group(3),
                    old_line,
                    count=1
                )
                modified_lines[line_num] = new_line

        elif field_type == 'list':
            # 找到列表字段的起始行
            list_start_line = int(original_key.split('_')[1])
            # 找到列表中第 idx 个文本行
            text_count = 0
            for j in range(list_start_line + 1, len(modified_lines)):
                line_stripped = modified_lines[j].strip()
                if line_stripped == ']':
                    break
                text_match = re.match(r'^(\s*)"(.*)"(\s*,?\s*)$', modified_lines[j])
                if text_match:
                    if text_count == idx:
                        indent = text_match.group(1)
                        suffix = text_match.group(3)
                        modified_lines[j] = f'{indent}"{zh_text}"{suffix}'
                        break
                    text_count += 1

    # 写入输出文件
    # 需要从 ftbquests 根目录算起的相对路径
    # 找到 file_path 中 ftbquests 之后的部分
    parts = file_path.replace('\\', '/').split('/')
    ftbquests_idx = -1
    for pi, part in enumerate(parts):
        if part == 'ftbquests':
            ftbquests_idx = pi
            break
    if ftbquests_idx >= 0:
        rel_path = os.path.join(*parts[ftbquests_idx:])
    else:
        rel_path = os.path.basename(file_path)
    output_path = os.path.join(output_dir, rel_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(modified_lines))

    total_translated = len(translated)
    total_cached = len(cached)

    return total_translated, total_cached


def process_ftbquests(
    quests_path: str,
    translator,
    cache,
    output_dir: str
) -> Tuple[int, int, int]:
    """
    处理整个 ftbquests 目录
    :param quests_path: ftbquests 源目录路径
    :param translator: 翻译器实例
    :param cache: 缓存实例
    :param output_dir: 输出目录
    :return: (文件数, 翻译条目数, 缓存命中数)
    """
    snbt_files = scan_snbt_files(quests_path)

    if not snbt_files:
        print("[信息] 未找到 snbt 文件")
        return 0, 0, 0

    print(f"[信息] 找到 {len(snbt_files)} 个 snbt 文件\n")

    total_files = 0
    total_translated = 0
    total_cached = 0

    for file_path in snbt_files:
        rel_path = os.path.relpath(file_path, quests_path)
        print(f"  处理: {rel_path}")

        translated, cached = translate_snbt_file(
            file_path, translator, cache, output_dir
        )

        if translated is not None and cached is not None and (translated + cached) > 0:
            total_files += 1
            total_translated += translated
            total_cached += cached
            print(f"    翻译: {translated} 条, 缓存: {cached} 条")
        else:
            # 即使不需要翻译，也复制原文件到输出目录
            output_path = os.path.join(output_dir, rel_path)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(file_path, 'r', encoding='utf-8') as src:
                with open(output_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            print(f"    无需翻译，已复制原文件")

    return total_files, total_translated, total_cached
