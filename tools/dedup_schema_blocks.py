#!/usr/bin/env python3
"""把五个方案中逐字相同的映射型配置块提取到 lufs_shared.yaml，并改写为 __include。

背景
----
librime 提供的复用机制中，只有 `__include: 文件:/路径` 适用于映射型配置块，
且能正确展开（实测）。`import_preset` 仅对 punctuator / key_binder /
recognizer 生效，对 engine / switches 会静默丢弃内容，因此本脚本不处理
列表型块（switches / engine / speller），它们由 tools/gen_schemas.py 负责。

本脚本幂等：已包含 __include 的块会被跳过。

用法
----
    python3 tools/dedup_schema_blocks.py --check   # 仅报告将要改动的块
    python3 tools/dedup_schema_blocks.py --apply   # 写入改动
"""

import argparse
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SCHEMAS = ["lufs_pinyin", "lufs_dpy", "lufs_mspy", "lufs_flypy", "lufs_pyjj"]

# 逐字相同、且可安全改用 __include 的映射型配置块
SHARED_BLOCKS = [
    "traditionalize",
    "emoji_suggestion",
    "grammar",
    "punctuator",
    "key_binder",
    "recognizer",
    "custom_phrase",
]

TOP_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")


def parse_blocks(text):
    """按顶层键切分，返回 [(key, start, end)] ，end 为新块起始偏移。"""
    lines = text.splitlines(keepends=True)
    starts = []
    for i, line in enumerate(lines):
        m = TOP_KEY.match(line)
        if m:
            starts.append((m.group(1), i))

    blocks = []
    for idx, (key, start) in enumerate(starts):
        end = starts[idx + 1][1] if idx + 1 < len(starts) else len(lines)
        blocks.append((key, start, end))
    return lines, blocks


def block_text(lines, start, end):
    return "".join(lines[start:end])


def is_uniform(block):
    """该块是否已收敛为纯 __include 形式。"""
    body = [l for l in block.splitlines() if l.strip()]
    return len(body) == 2 and body[1].strip().startswith("__include:")


def collect():
    """返回 (共享块内容, 各方案待替换的块位置)。"""
    shared = {}
    for key in SHARED_BLOCKS:
        texts = set()
        for schema in SCHEMAS:
            path = os.path.join(REPO, schema + ".schema.yaml")
            lines, blocks = parse_blocks(open(path, encoding="utf-8").read())
            for k, start, end in blocks:
                if k == key:
                    texts.add(block_text(lines, start, end).rstrip("\n"))
        if len(texts) == 1:
            shared[key] = texts.pop()
    return shared


def main(argv=None):
    parser = argparse.ArgumentParser(description="提取跨方案相同的映射型配置块")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="仅报告")
    group.add_argument("--apply", action="store_true", help="写入改动")
    args = parser.parse_args(argv)

    shared = collect()
    print("可收敛的共享块：")
    for key in SHARED_BLOCKS:
        if key in shared:
            print("  %-18s %d 行" % (key, len(shared[key].splitlines())))

    missing = [k for k in SHARED_BLOCKS if k not in shared]
    if missing:
        print("跳过（跨方案不一致）：%s" % ", ".join(missing))

    if args.check:
        return 0

    # 写出共享文件
    shared_path = os.path.join(REPO, "lufs_shared.yaml")
    header = (
        "# Rime 共享配置块\n"
        "# encoding: utf-8\n"
        "#\n"
        "# 本文件由 tools/dedup_schema_blocks.py 生成，承载五个 lufs_*.schema.yaml\n"
        "# 中逐字相同的映射型配置块。各方案经 __include: lufs_shared:/<块名> 引用。\n"
        "#\n"
        "# 注意：__include 仅适用于映射型块。列表型块（switches / engine /\n"
        "# speller）无法用 __include 扩展，由 tools/gen_schemas.py 处理；\n"
        "# import_preset 对 engine / switches 会静默丢弃内容，禁止使用。\n"
        "\n"
    )
    with open(shared_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(header)
        for key in SHARED_BLOCKS:
            if key in shared:
                handle.write(shared[key].rstrip("\n") + "\n\n")
    print("\n写入 %s" % os.path.relpath(shared_path, REPO))

    changed = 0
    for schema in SCHEMAS:
        path = os.path.join(REPO, schema + ".schema.yaml")
        original = open(path, encoding="utf-8").read()
        lines, blocks = parse_blocks(original)
        # 从后往前替换，避免偏移失效
        for key, start, end in reversed(blocks):
            if key not in shared:
                continue
            current = block_text(lines, start, end)
            if is_uniform(current):
                continue
            lines[start:end] = ["%s:\n  __include: lufs_shared:/%s\n\n" % (key, key)]
            changed += 1
        updated = "".join(lines)
        if updated != original:
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(updated)
            print("  改写 %s" % os.path.basename(path))

    print("\n共改写 %d 处引用" % changed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
