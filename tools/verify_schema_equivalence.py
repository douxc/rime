#!/usr/bin/env python3
"""校验 Rime 方案编译产物的等价性与复用机制健康度。

用途
----
1. 等价性校验：比较两份 `build/<schema_id>.schema.yaml`，排除
   `__build_info.timestamps` 段（该段取自源文件 mtime，每次编辑都会变化，
   纳入比较会产生必然的假阳性）后要求逐字节相同。
2. `import_preset` 断言：该机制仅对 punctuator / key_binder / recognizer
   三段有效。对 engine / switches 等段落使用时 librime 不报错、不展开，
   而是保留字面值，导致配置静默丢失且构建仍然成功。本脚本检出该失效。

仅依赖 Python 标准库（本机无 pyyaml）。

用法
----
    python3 tools/verify_schema_equivalence.py --baseline-dir <目录> [方案文件...]
    python3 tools/verify_schema_equivalence.py --check-import-preset <文件...>

退出码：0 全部通过；1 存在失败；2 用法错误。
"""

import argparse
import os
import re
import sys

# import_preset 经实测仅对这三段生效，其余段落出现该键即为静默失效
PRESET_SECTIONS = {"punctuator", "key_binder", "recognizer"}

TOP_LEVEL_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")
INDENTED_KEY = re.compile(r"^(\s+)([A-Za-z_][A-Za-z0-9_]*):")


def strip_build_info(text):
    """移除 __build_info 段（含其子键），返回剩余文本。

    __build_info 是编译产物的首段，其 timestamps 子段随源文件 mtime 变化。
    """
    lines = text.splitlines()
    out = []
    skipping = False

    for line in lines:
        match = TOP_LEVEL_KEY.match(line)
        if match:
            # 遇到新的顶层键时停止跳过
            skipping = match.group(1) == "__build_info"
            if skipping:
                continue
        elif skipping:
            # __build_info 的子行（有缩进或空行）
            continue
        out.append(line)

    return "\n".join(out)


def normalize(text):
    """去除首尾空行，供逐行比较。"""
    stripped = strip_build_info(text)
    return stripped.strip("\n").splitlines()


def read_text(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def unified_diff(left, right, left_label, right_label, context=3):
    """标准库 difflib 的薄封装，返回可读差异文本。"""
    import difflib

    return "\n".join(
        difflib.unified_diff(
            left, right, fromfile=left_label, tofile=right_label, lineterm="", n=context
        )
    )


def compare_files(baseline_path, current_path):
    """比较两份编译产物，返回 (是否等价, 说明)。"""
    left = normalize(read_text(baseline_path))
    right = normalize(read_text(current_path))

    if left == right:
        return True, "等价（差异仅限 __build_info.timestamps）"

    diff = unified_diff(left, right, baseline_path, current_path)
    changed = sum(
        1 for line in diff.splitlines() if line[:1] in "+-" and line[:3] not in ("+++", "---")
    )
    return False, "不等价，差异 %d 行：\n%s" % (changed, diff)


def check_import_preset(path):
    """检出在非白名单段落中出现的 import_preset 字面值。"""
    findings = []
    lines = read_text(path).splitlines()
    section = None

    for lineno, line in enumerate(lines, start=1):
        top = TOP_LEVEL_KEY.match(line)
        if top:
            section = top.group(1)
            continue

        indented = INDENTED_KEY.match(line)
        if indented and indented.group(2) == "import_preset":
            if section not in PRESET_SECTIONS:
                findings.append((lineno, section, line.strip()))

    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="校验 Rime 编译产物的等价性与 import_preset 健康度"
    )
    parser.add_argument(
        "--baseline-dir",
        help="构建前的编译产物目录；与当前 build/ 逐方案比较",
    )
    parser.add_argument(
        "--build-dir",
        default="build",
        help="当前编译产物目录（默认 build）",
    )
    parser.add_argument(
        "--check-import-preset",
        nargs="*",
        metavar="FILE",
        help="仅检查指定文件（或 build/ 下全部产物）中的 import_preset 失效",
    )
    parser.add_argument(
        "--schemas",
        nargs="*",
        metavar="SCHEMA_ID",
        help="限定比较的方案 id（默认比较基线目录中出现的全部方案）",
    )
    args = parser.parse_args(argv)

    if not args.baseline_dir and not args.check_import_preset:
        parser.print_help()
        return 2

    failures = 0

    if args.baseline_dir:
        schema_ids = args.schemas
        if not schema_ids:
            schema_ids = sorted(
                name[: -len(".schema.yaml")]
                for name in os.listdir(args.baseline_dir)
                if name.endswith(".schema.yaml")
            )
        if not schema_ids:
            print("错误：基线目录中没有 *.schema.yaml", file=sys.stderr)
            return 2

        print("== 等价性校验 ==")
        for schema_id in schema_ids:
            filename = schema_id + ".schema.yaml"
            baseline_path = os.path.join(args.baseline_dir, filename)
            current_path = os.path.join(args.build_dir, filename)

            if not os.path.exists(baseline_path):
                print("  跳过 %s：基线缺失" % schema_id)
                continue
            if not os.path.exists(current_path):
                print("  失败 %s：当前产物缺失 %s" % (schema_id, current_path))
                failures += 1
                continue

            ok, detail = compare_files(baseline_path, current_path)
            if ok:
                print("  通过 %s：%s" % (schema_id, detail))
            else:
                print("  失败 %s：%s" % (schema_id, detail))
                failures += 1

    if args.check_import_preset is not None:
        targets = args.check_import_preset
        if not targets:
            build_dir = args.build_dir
            targets = [
                os.path.join(build_dir, name)
                for name in sorted(os.listdir(build_dir))
                if name.endswith(".schema.yaml")
            ]

        print("== import_preset 健康度 ==")
        if not targets:
            print("  跳过：没有可检查的产物")
        for path in targets:
            if not os.path.exists(path):
                print("  跳过 %s：文件不存在" % path)
                continue
            findings = check_import_preset(path)
            if findings:
                print("  失败 %s：检出静默失效" % path)
                for lineno, section, snippet in findings:
                    print("    第 %d 行，段 `%s`：%s" % (lineno, section, snippet))
                failures += 1
            else:
                print("  通过 %s：无静默失效" % path)

    print()
    if failures:
        print("结果：%d 项失败" % failures)
        return 1
    print("结果：全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
