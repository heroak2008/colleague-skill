#!/usr/bin/env python3
"""
对话群组上下文管理器

为每个同事 Skill 管理多个命名对话群组，每个群组绑定一种关系类型
（superior / peer / junior）和可选的背景注记，并保存该群组的完整
导入聊天记录。使用时调用 load 命令生成运行时 prompt 注入文本，
AI 据此切换对应的说话风格。

目录结构：
  colleagues/{slug}/conversations/
  ├── contexts.json               # 群组注册表
  └── {group_id}/
      ├── context.md              # 背景注记（可选）
      └── history.txt             # 导入的聊天记录（txt_parser 输出全文）

用法示例：

  # 新建群组
  python3 tools/context_manager.py create \\
    --slug zhangsan --group-id boss_1on1 \\
    --display-name "和老板的 1on1" --relation superior \\
    --note "老板是技术总监，关注 KR 进度" \\
    --base-dir ./colleagues

  # 列出群组
  python3 tools/context_manager.py list --slug zhangsan --base-dir ./colleagues

  # 导入聊天记录到群组
  python3 tools/context_manager.py import \\
    --slug zhangsan --group-id boss_1on1 \\
    --file /tmp/txt_parsed_superior.txt \\
    --base-dir ./colleagues

  # 生成运行时上下文 prompt（在 /use 命令中调用）
  python3 tools/context_manager.py load \\
    --slug zhangsan --group-id boss_1on1 \\
    --base-dir ./colleagues

  # 删除群组
  python3 tools/context_manager.py delete \\
    --slug zhangsan --group-id boss_1on1 \\
    --base-dir ./colleagues

  # 显示群组详情
  python3 tools/context_manager.py show \\
    --slug zhangsan --group-id boss_1on1 \\
    --base-dir ./colleagues
"""

from __future__ import annotations

import json
import shutil
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone

DEFAULT_BASE_DIR = "./colleagues"

RELATION_LABELS = {
    "superior": "上级",
    "peer": "平级",
    "junior": "后辈",
}

RELATION_STYLE_RULES = {
    "superior": (
        "当前关系类型为 **superior（上级）**，请激活以下规则：\n"
        "- 激活 Layer 4「对上级」的所有行为规则\n"
        "- 措辞正式，避免直接否定，改用「我有个地方想确认一下」\n"
        "- 汇报时只说结论和风险，不加过程细节\n"
        "- 情绪收敛，不表露不满或质疑\n"
        "- 有问题先准备好时间线和客观原因，再决定是否主动说"
    ),
    "peer": (
        "当前关系类型为 **peer（平级）**，请激活以下规则：\n"
        "- 激活 Layer 4「对平级」的所有行为规则\n"
        "- 可直接说「这里有个问题」，不需要包装\n"
        "- 群聊场景：潜水为主，被 @ 才出现，回复尽量简短\n"
        "- 遇到分歧：说完自己的判断后等对方拿数据，不主动争吵\n"
        "- 职责外的问题直接说「这块不是我的，找 XX」"
    ),
    "junior": (
        "当前关系类型为 **junior（后辈）**，请激活以下规则：\n"
        "- 激活 Layer 4「对下级 / 后辈」的所有行为规则\n"
        "- Code Review 评论直接，不解释为什么，认为对方应自己搞清楚\n"
        "- 分配任务用「这个你来 own」，不跟进，出了问题再说\n"
        "- 被问技术问题时先反问「你自己先想了什么方案？」\n"
        "- 不主动辅导，但问了会认真回答"
    ),
}


# ─── 工具函数 ───────────────────────────────────────────────────────────────────

def _conversations_dir(base_dir: Path, slug: str) -> Path:
    return base_dir / slug / "conversations"


def _contexts_path(base_dir: Path, slug: str) -> Path:
    return _conversations_dir(base_dir, slug) / "contexts.json"


def _group_dir(base_dir: Path, slug: str, group_id: str) -> Path:
    return _conversations_dir(base_dir, slug) / group_id


def _load_contexts(base_dir: Path, slug: str) -> dict:
    path = _contexts_path(base_dir, slug)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"groups": []}


def _save_contexts(base_dir: Path, slug: str, data: dict) -> None:
    path = _contexts_path(base_dir, slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _find_group(data: dict, group_id: str) -> dict | None:
    for g in data.get("groups", []):
        if g["id"] == group_id:
            return g
    return None


def _assert_skill_exists(base_dir: Path, slug: str) -> None:
    skill_dir = base_dir / slug
    if not skill_dir.exists() or not (skill_dir / "meta.json").exists():
        print(f"错误：找不到同事 Skill「{slug}」（路径：{skill_dir}）", file=sys.stderr)
        sys.exit(1)


# ─── 子命令处理函数 ──────────────────────────────────────────────────────────────

def cmd_create(args: argparse.Namespace, base_dir: Path) -> None:
    """新建对话群组"""
    _assert_skill_exists(base_dir, args.slug)

    group_id = args.group_id
    relation = args.relation

    if relation not in RELATION_LABELS:
        print(f"错误：--relation 必须为 superior / peer / junior，收到：{relation}", file=sys.stderr)
        sys.exit(1)

    data = _load_contexts(base_dir, args.slug)

    if _find_group(data, group_id):
        print(f"错误：群组「{group_id}」已存在，如需更新请先删除再重建", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc).isoformat()
    display_name = args.display_name or group_id
    note = args.note or ""

    group_entry = {
        "id": group_id,
        "display_name": display_name,
        "relation": relation,
        "created_at": now,
        "note": note,
        "has_history": False,
    }
    data["groups"].append(group_entry)
    _save_contexts(base_dir, args.slug, data)

    # 创建群组目录
    gdir = _group_dir(base_dir, args.slug, group_id)
    gdir.mkdir(parents=True, exist_ok=True)

    # 写入 context.md（若有备注）
    if note:
        (gdir / "context.md").write_text(
            f"# 群组背景：{display_name}\n\n{note}\n",
            encoding="utf-8",
        )

    print(f"✅ 群组已创建：[{group_id}]「{display_name}」（{RELATION_LABELS[relation]}）")
    print(f"   路径：{gdir}")
    print()
    print("下一步：导入该群组的聊天记录（可选）：")
    print(
        f"  python3 tools/context_manager.py import "
        f"--slug {args.slug} --group-id {group_id} "
        f"--file /tmp/txt_parsed_{relation}.txt"
    )


def cmd_list(args: argparse.Namespace, base_dir: Path) -> None:
    """列出同事的所有群组"""
    _assert_skill_exists(base_dir, args.slug)

    data = _load_contexts(base_dir, args.slug)
    groups = data.get("groups", [])

    if not groups:
        print(f"「{args.slug}」暂无对话群组。")
        print()
        print("创建群组：")
        print(
            f"  python3 tools/context_manager.py create "
            f"--slug {args.slug} --group-id <群组ID> "
            f"--display-name <显示名> --relation superior/peer/junior"
        )
        return

    print(f"「{args.slug}」共 {len(groups)} 个对话群组：\n")
    for g in groups:
        rel_label = RELATION_LABELS.get(g["relation"], g["relation"])
        has_hist = "✓ 有聊天记录" if g.get("has_history") else "✗ 无聊天记录"
        created = g.get("created_at", "")[:10]
        print(f"  [{g['id']}]  {g['display_name']}  —  关系：{rel_label}  {has_hist}  建于：{created}")
        if g.get("note"):
            print(f"    背景：{g['note']}")
        print()


def cmd_import(args: argparse.Namespace, base_dir: Path) -> None:
    """导入聊天记录到群组"""
    _assert_skill_exists(base_dir, args.slug)

    data = _load_contexts(base_dir, args.slug)
    group = _find_group(data, args.group_id)
    if not group:
        print(f"错误：群组「{args.group_id}」不存在，请先创建", file=sys.stderr)
        sys.exit(1)

    src = Path(args.file).expanduser()
    if not src.exists():
        print(f"错误：文件不存在：{src}", file=sys.stderr)
        sys.exit(1)

    gdir = _group_dir(base_dir, args.slug, args.group_id)
    gdir.mkdir(parents=True, exist_ok=True)

    dest = gdir / "history.txt"
    shutil.copy2(src, dest)
    group["has_history"] = True
    _save_contexts(base_dir, args.slug, data)

    line_count = len(dest.read_text(encoding="utf-8").splitlines())
    print(f"✅ 聊天记录已导入：{line_count} 行")
    print(f"   群组：[{args.group_id}]「{group['display_name']}」")
    print(f"   路径：{dest}")


def cmd_load(args: argparse.Namespace, base_dir: Path) -> None:
    """生成运行时上下文 prompt，供 AI 注入到会话开头"""
    _assert_skill_exists(base_dir, args.slug)

    data = _load_contexts(base_dir, args.slug)
    group = _find_group(data, args.group_id)
    if not group:
        print(f"错误：群组「{args.group_id}」不存在", file=sys.stderr)
        sys.exit(1)

    relation = group["relation"]
    rel_label = RELATION_LABELS.get(relation, relation)
    display_name = group["display_name"]
    note = group.get("note", "")

    lines: list[str] = []
    lines.append(f"## 当前对话群组：{display_name}（关系类型：{rel_label} / `{relation}`）")
    lines.append("")

    if note:
        lines.append(f"**群组背景**：{note}")
        lines.append("")

    # 说话风格切换规则
    style_rule = RELATION_STYLE_RULES.get(relation, "")
    if style_rule:
        lines.append("### 说话风格切换规则")
        lines.append("")
        lines.append(style_rule)
        lines.append("")

    # 历史聊天记录
    history_path = _group_dir(base_dir, args.slug, args.group_id) / "history.txt"
    if history_path.exists():
        history_text = history_path.read_text(encoding="utf-8").strip()
        if history_text:
            lines.append("### 本群组聊天记录（导入的原始记录，供风格参考）")
            lines.append("")
            lines.append(history_text)
            lines.append("")

    print("\n".join(lines))


def cmd_show(args: argparse.Namespace, base_dir: Path) -> None:
    """显示群组详情"""
    _assert_skill_exists(base_dir, args.slug)

    data = _load_contexts(base_dir, args.slug)
    group = _find_group(data, args.group_id)
    if not group:
        print(f"错误：群组「{args.group_id}」不存在", file=sys.stderr)
        sys.exit(1)

    rel_label = RELATION_LABELS.get(group["relation"], group["relation"])
    print(f"群组 ID       : {group['id']}")
    print(f"显示名        : {group['display_name']}")
    print(f"关系类型      : {group['relation']}（{rel_label}）")
    print(f"建立时间      : {group.get('created_at', '')[:19]}")
    print(f"背景注记      : {group.get('note') or '（无）'}")

    history_path = _group_dir(base_dir, args.slug, args.group_id) / "history.txt"
    if history_path.exists():
        line_count = len(history_path.read_text(encoding="utf-8").splitlines())
        print(f"聊天记录      : {line_count} 行（{history_path}）")
    else:
        print("聊天记录      : 暂无")


def cmd_delete(args: argparse.Namespace, base_dir: Path) -> None:
    """删除群组"""
    _assert_skill_exists(base_dir, args.slug)

    data = _load_contexts(base_dir, args.slug)
    group = _find_group(data, args.group_id)
    if not group:
        print(f"错误：群组「{args.group_id}」不存在", file=sys.stderr)
        sys.exit(1)

    display_name = group["display_name"]

    if not args.yes:
        confirm = input(f"确认删除群组「{display_name}」及其所有数据？(y/N) ").strip().lower()
        if confirm != "y":
            print("已取消")
            return

    # 删除群组目录
    gdir = _group_dir(base_dir, args.slug, args.group_id)
    if gdir.exists():
        shutil.rmtree(gdir)

    # 从注册表中移除
    data["groups"] = [g for g in data["groups"] if g["id"] != args.group_id]
    _save_contexts(base_dir, args.slug, data)

    print(f"✅ 群组已删除：[{args.group_id}]「{display_name}」")


# ─── CLI 入口 ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="对话群组上下文管理器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # create
    p_create = subparsers.add_parser("create", help="新建对话群组")
    p_create.add_argument("--slug", required=True, help="同事 slug")
    p_create.add_argument("--group-id", required=True, help="群组唯一 ID（如 boss_1on1）")
    p_create.add_argument("--display-name", help="群组显示名（如「和老板的 1on1」）")
    p_create.add_argument(
        "--relation",
        required=True,
        choices=["superior", "peer", "junior"],
        help="关系类型：superior=上级  peer=平级  junior=后辈",
    )
    p_create.add_argument("--note", help="群组背景说明（可选）")
    p_create.add_argument("--base-dir", default=DEFAULT_BASE_DIR, help=f"同事 Skill 根目录（默认：{DEFAULT_BASE_DIR}）")

    # list
    p_list = subparsers.add_parser("list", help="列出同事的所有群组")
    p_list.add_argument("--slug", required=True, help="同事 slug")
    p_list.add_argument("--base-dir", default=DEFAULT_BASE_DIR, help=f"同事 Skill 根目录（默认：{DEFAULT_BASE_DIR}）")

    # import
    p_import = subparsers.add_parser("import", help="导入聊天记录到群组")
    p_import.add_argument("--slug", required=True, help="同事 slug")
    p_import.add_argument("--group-id", required=True, help="群组 ID")
    p_import.add_argument(
        "--file",
        required=True,
        help="txt_parser.py 输出的聊天记录文件路径",
    )
    p_import.add_argument("--base-dir", default=DEFAULT_BASE_DIR, help=f"同事 Skill 根目录（默认：{DEFAULT_BASE_DIR}）")

    # load
    p_load = subparsers.add_parser("load", help="生成运行时上下文 prompt（供 AI 注入）")
    p_load.add_argument("--slug", required=True, help="同事 slug")
    p_load.add_argument("--group-id", required=True, help="群组 ID")
    p_load.add_argument("--base-dir", default=DEFAULT_BASE_DIR, help=f"同事 Skill 根目录（默认：{DEFAULT_BASE_DIR}）")

    # show
    p_show = subparsers.add_parser("show", help="显示群组详情")
    p_show.add_argument("--slug", required=True, help="同事 slug")
    p_show.add_argument("--group-id", required=True, help="群组 ID")
    p_show.add_argument("--base-dir", default=DEFAULT_BASE_DIR, help=f"同事 Skill 根目录（默认：{DEFAULT_BASE_DIR}）")

    # delete
    p_delete = subparsers.add_parser("delete", help="删除群组")
    p_delete.add_argument("--slug", required=True, help="同事 slug")
    p_delete.add_argument("--group-id", required=True, help="群组 ID")
    p_delete.add_argument("--yes", "-y", action="store_true", help="跳过确认提示")
    p_delete.add_argument("--base-dir", default=DEFAULT_BASE_DIR, help=f"同事 Skill 根目录（默认：{DEFAULT_BASE_DIR}）")

    args = parser.parse_args()
    base_dir = Path(args.base_dir).expanduser()

    dispatch = {
        "create": cmd_create,
        "list": cmd_list,
        "import": cmd_import,
        "load": cmd_load,
        "show": cmd_show,
        "delete": cmd_delete,
    }
    dispatch[args.command](args, base_dir)


if __name__ == "__main__":
    main()
