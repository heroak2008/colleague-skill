#!/usr/bin/env python3
"""
Input 目录加载器

读取同事 Skill 的 input/ 目录结构，解析对话记录文件，
生成供 AI 注入的运行时上下文 prompt。

目录结构：
  colleagues/{slug}/input/
  ├── 上级/    # 与上级的私聊记录（每人一个 .txt 文件，如 张三.txt）
  ├── 同级/    # 与平级的私聊记录
  ├── 下级/    # 与下级的私聊记录
  └── 群组/    # 群聊记录（每个群组一个 .txt 文件，如 服务端研发群.txt）

私聊文件格式（每条消息）：
  姓名 工号 时间戳
  对话内容（可多行）

  姓名 工号 时间戳
  下一条对话内容

群聊文件格式：
  [群组名称]
  姓名 工号 时间戳
  对话内容

  姓名 工号 时间戳
  下一条对话内容

用法示例：

  # 列出 input/ 下所有已有记录（显示名称与关系类型）
  python3 tools/input_loader.py scan --slug zhangsan --base-dir ./colleagues

  # 加载与某人的私聊上下文（自动判断关系类型）
  python3 tools/input_loader.py load --slug zhangsan --name 李四 --base-dir ./colleagues

  # 加载群聊上下文，同时加载群内某人的私聊记录
  python3 tools/input_loader.py load \\
    --slug zhangsan --group 服务端研发群 --name 李四 --base-dir ./colleagues

  # 仅加载群聊上下文（不指定个人）
  python3 tools/input_loader.py load --slug zhangsan --group 服务端研发群 --base-dir ./colleagues
"""

from __future__ import annotations

import re
import sys
import argparse
from pathlib import Path

DEFAULT_BASE_DIR = "./colleagues"

# 目录名 → 关系类型（内部英文 key）
DIR_TO_RELATION: dict[str, str] = {
    "上级": "superior",
    "同级": "peer",
    "下级": "junior",
}

# 关系类型 → 中文标签
RELATION_LABEL: dict[str, str] = {
    "superior": "上级",
    "peer": "同级",
    "junior": "下级",
    "group": "群组",
    "unknown": "未知",
}

# 各关系类型对应的说话风格提示
STYLE_RULES: dict[str, str] = {
    "superior": (
        "当前对话对象的关系类型为 **上级（superior）**，请激活以下风格规则：\n"
        "- 激活 Persona Layer 4「对上级」的全部行为规则\n"
        "- 措辞正式，避免直接否定，改用「我有个地方想确认一下」\n"
        "- 汇报时只说结论和风险，不加过程细节\n"
        "- 情绪收敛，不表露不满或质疑\n"
        "- 有问题先准备好时间线和客观原因，再决定是否主动说"
    ),
    "peer": (
        "当前对话对象的关系类型为 **同级（peer）**，请激活以下风格规则：\n"
        "- 激活 Persona Layer 4「对平级」的全部行为规则\n"
        "- 可直接说「这里有个问题」，不需要包装\n"
        "- 群聊场景：潜水为主，被 @ 才出现，回复尽量简短\n"
        "- 遇到分歧：说完自己的判断后等对方拿数据，不主动争吵\n"
        "- 职责外的问题直接说「这块不是我的，找 XX」"
    ),
    "junior": (
        "当前对话对象的关系类型为 **下级（junior）**，请激活以下风格规则：\n"
        "- 激活 Persona Layer 4「对下级 / 后辈」的全部行为规则\n"
        "- Code Review 评论直接，不解释为什么，认为对方应自己搞清楚\n"
        "- 分配任务用「这个你来 own」，不跟进，出了问题再说\n"
        "- 被问技术问题时先反问「你自己先想了什么方案？」\n"
        "- 不主动辅导，但问了会认真回答"
    ),
}


# ─── 内部工具函数 ───────────────────────────────────────────────────────────────

def _input_dir(base_dir: Path, slug: str) -> Path:
    return base_dir / slug / "input"


def _assert_skill_exists(base_dir: Path, slug: str) -> None:
    skill_dir = base_dir / slug
    if not skill_dir.exists() or not (skill_dir / "meta.json").exists():
        print(f"错误：找不到同事 Skill「{slug}」（路径：{skill_dir}）", file=sys.stderr)
        sys.exit(1)


def _find_private_chat(base_dir: Path, slug: str, name: str) -> tuple[str, Path] | None:
    """
    在 input/上级、input/同级、input/下级 中搜索与 name 匹配的文件。
    匹配规则：文件名（去掉 .txt 后缀）包含 name，或文件第一行以 name 开头。
    返回 (relation_key, path) 或 None。
    """
    idir = _input_dir(base_dir, slug)
    for dir_name, relation_key in DIR_TO_RELATION.items():
        subdir = idir / dir_name
        if not subdir.is_dir():
            continue
        for txt_file in sorted(subdir.glob("*.txt")):
            # 方式 1：文件名包含 name
            if name in txt_file.stem:
                return relation_key, txt_file
            # 方式 2：文件第一个非空行以 name 开头
            try:
                first_line = _first_nonempty_line(txt_file)
                if first_line.startswith(name):
                    return relation_key, txt_file
            except Exception:
                continue
    return None


def _find_group_chat(base_dir: Path, slug: str, group_name: str) -> Path | None:
    """
    在 input/群组/ 中搜索名称匹配 group_name 的文件。
    匹配规则：文件名包含 group_name，或文件第一行为 [group_name]。
    """
    group_dir = _input_dir(base_dir, slug) / "群组"
    if not group_dir.is_dir():
        return None
    for txt_file in sorted(group_dir.glob("*.txt")):
        if group_name in txt_file.stem:
            return txt_file
        try:
            first_line = _first_nonempty_line(txt_file)
            if first_line.strip() in (f"[{group_name}]", group_name):
                return txt_file
        except Exception:
            continue
    return None


def _first_nonempty_line(path: Path) -> str:
    """返回文件第一个非空行"""
    for encoding in ("utf-8", "gbk", "gb18030"):
        try:
            with path.open(encoding=encoding, errors="replace") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        return stripped
            break
        except UnicodeDecodeError:
            continue
    return ""


def _read_file(path: Path) -> str:
    """读取文件内容，自动检测编码"""
    for encoding in ("utf-8", "gbk", "gb18030", "big5"):
        try:
            return path.read_text(encoding=encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def _infer_relation_for_person_in_group(base_dir: Path, slug: str, name: str) -> str:
    """
    在私聊目录中查找 name，推断其关系类型。
    找不到时返回 "unknown"。
    """
    result = _find_private_chat(base_dir, slug, name)
    if result:
        return result[0]
    return "unknown"


# ─── 子命令处理 ──────────────────────────────────────────────────────────────────

def cmd_scan(args: argparse.Namespace, base_dir: Path) -> None:
    """扫描 input/ 目录，列出所有已放置的对话记录"""
    _assert_skill_exists(base_dir, args.slug)
    idir = _input_dir(base_dir, args.slug)

    if not idir.exists():
        print(f"「{args.slug}」的 input/ 目录不存在或为空。")
        print()
        print("请在以下目录放置对话记录（.txt 格式）：")
        print(f"  私聊：{idir}/上级/  {idir}/同级/  {idir}/下级/")
        print(f"  群聊：{idir}/群组/")
        return

    total = 0
    for dir_name, relation_key in DIR_TO_RELATION.items():
        subdir = idir / dir_name
        if not subdir.is_dir():
            continue
        files = sorted(subdir.glob("*.txt"))
        if files:
            print(f"【{dir_name}（{relation_key}）】")
            for f in files:
                first = _first_nonempty_line(f)
                print(f"  {f.name}  ← {first[:60]}")
            total += len(files)
            print()

    group_dir = idir / "群组"
    if group_dir.is_dir():
        files = sorted(group_dir.glob("*.txt"))
        if files:
            print("【群组（group）】")
            for f in files:
                first = _first_nonempty_line(f)
                print(f"  {f.name}  ← {first[:60]}")
            total += len(files)
            print()

    if total == 0:
        print("input/ 目录存在，但尚无 .txt 文件。")
        print("请将对话记录放入对应的子目录。")
    else:
        print(f"共 {total} 个对话记录文件。")


def cmd_load(args: argparse.Namespace, base_dir: Path) -> None:
    """
    生成运行时上下文 prompt，供 AI 注入到会话开头。
    支持：--name（私聊/群聊内的人）、--group（群聊名称）。
    可以单独用 --name、单独用 --group，也可以同时使用。
    """
    _assert_skill_exists(base_dir, args.slug)

    name: str = args.name or ""
    group: str = args.group or ""

    if not name and not group:
        print("错误：至少需要指定 --name 或 --group 之一", file=sys.stderr)
        sys.exit(1)

    lines: list[str] = []

    # ── 私聊部分 ──────────────────────────────────────────────────────────────
    private_relation = "peer"  # 默认平级
    private_history: str = ""

    if name:
        result = _find_private_chat(base_dir, args.slug, name)
        if result:
            private_relation, private_path = result
            private_history = _read_file(private_path).strip()
        else:
            private_relation = "unknown"

    # ── 群聊部分 ──────────────────────────────────────────────────────────────
    group_history: str = ""
    group_name_display: str = ""

    if group:
        group_path = _find_group_chat(base_dir, args.slug, group)
        if group_path:
            group_history = _read_file(group_path).strip()
            # 提取群组显示名（文件第一行如果是 [xxx] 则用 xxx，否则用文件名）
            first = _first_nonempty_line(group_path)
            m = re.match(r"^\[(.+)\]$", first.strip())
            group_name_display = m.group(1) if m else group_path.stem
        else:
            group_name_display = group

        # 如果没有私聊记录但知道群聊内的人，尝试通过私聊目录推断关系
        if name and private_relation == "unknown":
            inferred = _infer_relation_for_person_in_group(base_dir, args.slug, name)
            if inferred != "unknown":
                private_relation = inferred

    # ── 组装 prompt ──────────────────────────────────────────────────────────
    # 标题行
    if group and name:
        rel_label = RELATION_LABEL.get(private_relation, private_relation)
        lines.append(
            f"## 当前对话场景：群组「{group_name_display}」中的 {name}（关系类型：{rel_label}）"
        )
    elif group:
        lines.append(f"## 当前对话场景：群组「{group_name_display}」")
    else:
        rel_label = RELATION_LABEL.get(private_relation, private_relation)
        lines.append(f"## 当前对话场景：与 {name} 的私聊（关系类型：{rel_label}）")
    lines.append("")

    # 风格切换规则（基于私聊关系，或群聊内的个人关系）
    effective_relation = private_relation if private_relation != "unknown" else "peer"
    style_rule = STYLE_RULES.get(effective_relation, "")
    if style_rule:
        lines.append("### 说话风格切换规则")
        lines.append("")
        lines.append(style_rule)
        lines.append("")

    # 私聊历史
    if private_history:
        lines.append(f"### {name} 的私聊记录（{RELATION_LABEL.get(private_relation, private_relation)}）")
        lines.append("")
        lines.append(private_history)
        lines.append("")

    # 群聊历史
    if group_history:
        lines.append(f"### 群组「{group_name_display}」聊天记录")
        lines.append("")
        lines.append(group_history)
        lines.append("")

    print("\n".join(lines))


# ─── CLI 入口 ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Input 目录加载器 — 扫描 input/ 并生成运行时上下文 prompt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # scan
    p_scan = subparsers.add_parser("scan", help="扫描 input/ 目录，列出已放置的对话记录")
    p_scan.add_argument("--slug", required=True, help="同事 slug")
    p_scan.add_argument(
        "--base-dir",
        default=DEFAULT_BASE_DIR,
        help=f"同事 Skill 根目录（默认：{DEFAULT_BASE_DIR}）",
    )

    # load
    p_load = subparsers.add_parser("load", help="生成运行时上下文 prompt（供 AI 注入）")
    p_load.add_argument("--slug", required=True, help="同事 slug")
    p_load.add_argument("--name", default="", help="对话对象姓名（私聊 / 群聊内的人）")
    p_load.add_argument("--group", default="", help="群组名称（对应 input/群组/ 下的文件）")
    p_load.add_argument(
        "--base-dir",
        default=DEFAULT_BASE_DIR,
        help=f"同事 Skill 根目录（默认：{DEFAULT_BASE_DIR}）",
    )

    args = parser.parse_args()
    base_dir = Path(args.base_dir).expanduser()

    if args.command == "scan":
        cmd_scan(args, base_dir)
    elif args.command == "load":
        cmd_load(args, base_dir)


if __name__ == "__main__":
    main()
