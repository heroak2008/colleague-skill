#!/usr/bin/env python3
"""
习惯管理器

管理同事 Skill 的说话习惯（口头禅、高频词、行话、说话风格规则），追踪每个习惯
在 input/ 聊天记录中最近一次出现的时间。超过 90 天未在记录中出现的习惯，
将在运行时上下文中被标记为"权重降低"，AI 应减少使用。

**仅追踪 Layer 2（表达风格）的习惯。Layer 0（核心性格）不受此规则影响。**

用法：
    # 从 persona.md Layer 2 初始化 habits.json
    python3 tools/habit_manager.py init --slug zhangsan --base-dir ./colleagues

    # 扫描 input/ 目录，更新习惯的最后出现时间
    python3 tools/habit_manager.py scan --slug zhangsan --base-dir ./colleagues

    # 列出已过期的习惯（active=false）
    python3 tools/habit_manager.py check --slug zhangsan --base-dir ./colleagues
"""

from __future__ import annotations

import json
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional

DEFAULT_BASE_DIR = "./colleagues"
DEFAULT_EXPIRY_DAYS = 90

# 将 tools/ 目录加入 sys.path，以便在以脚本方式运行时能导入同级模块（如 txt_parser）
_TOOLS_DIR = Path(__file__).parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

try:
    from txt_parser import parse_file as _parse_file  # type: ignore[import]
    _TXT_PARSER_AVAILABLE = True
except ImportError:
    _TXT_PARSER_AVAILABLE = False

# ─── 时间戳解析 ─────────────────────────────────────────────────────────────────

_TS_PATTERNS = [
    # 2024-01-01 10:00:00  /  2024/01/01 10:00:00  /  2024-01-01T10:00:00
    re.compile(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})[T ](\d{1,2}:\d{2}(?::\d{2})?)"),
    # 2024-01-01  /  2024/01/01
    re.compile(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})"),
]

# persona.md 行内注释最大长度（如 take（"这个 take 对不对"） 中括号内的说明）
_ANNOTATION_MAX_LEN = 80


def _parse_timestamp(ts_str: str) -> Optional[datetime]:
    """将聊天记录中的时间戳字符串解析为 datetime（UTC）。返回 None 表示无法解析。"""
    if not ts_str:
        return None
    s = ts_str.strip()
    for pat in _TS_PATTERNS:
        m = pat.search(s)
        if m:
            raw = m.group(0).replace("/", "-").replace("T", " ")
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(raw[: len(fmt)], fmt)
                    return dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
    return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─── persona.md 解析：提取 Layer 2 习惯 ────────────────────────────────────────

_CATCHPHRASE_RE = re.compile(r"你的口头禅[：:](.+)")
_HIGHFREQ_RE = re.compile(r"你的高频词[：:](.+)")
_JARGON_RE = re.compile(r"你的行话[：:](.+)")


def _extract_list_items(text: str) -> list[str]:
    """
    从如 '「先对齐一下」「impact 是什么」' 或 '对齐、落地、推进' 这样的文本中
    提取单个词条。支持「」引号、顿号、逗号分隔，并去除行内注释（如 take（"示例"））。
    """
    # 先去除括号内的注释说明，如 take（"这个 take 对不对"）→ take
    cleaned = re.sub(r"[（(][^）)]{0,%d}[）)]" % _ANNOTATION_MAX_LEN, "", text)

    # 尝试用「」括号提取
    bracketed = re.findall(r"[「『]([^「『」』]{1,50})[」』]", cleaned)
    if bracketed:
        return [b.strip() for b in bracketed if b.strip()]

    # 回退：按顿号/逗号分割（不按空格，以保留 "follow up" 这类多词词组）
    parts = re.split(r"[、，,]+", cleaned.strip())
    return [p.strip() for p in parts if p.strip() and len(p.strip()) >= 2]


def _parse_layer2_habits(persona_content: str) -> list[dict]:
    """从 persona.md 内容中提取 Layer 2 的习惯条目。"""
    habits: list[dict] = []
    seen: set[str] = set()

    def _add(text: str, habit_type: str) -> None:
        if text and text not in seen:
            seen.add(text)
            habits.append({"text": text, "type": habit_type})

    for line in persona_content.splitlines():
        m = _CATCHPHRASE_RE.search(line)
        if m:
            for item in _extract_list_items(m.group(1)):
                _add(item, "catchphrase")
            continue

        m = _HIGHFREQ_RE.search(line)
        if m:
            for item in _extract_list_items(m.group(1)):
                _add(item, "highfreq")
            continue

        m = _JARGON_RE.search(line)
        if m:
            for item in _extract_list_items(m.group(1)):
                _add(item, "jargon")
            continue

    return habits


# ─── habits.json 读写 ──────────────────────────────────────────────────────────

def _habits_path(skill_dir: Path) -> Path:
    return skill_dir / "habits.json"


def _load_habits(skill_dir: Path) -> dict:
    p = _habits_path(skill_dir)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"habits": [], "expiry_days": DEFAULT_EXPIRY_DAYS, "last_scanned": None}


def _save_habits(skill_dir: Path, data: dict) -> None:
    _habits_path(skill_dir).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _is_active(last_observed: Optional[str], expiry_days: int) -> bool:
    """判断习惯是否仍然活跃（last_observed 距今 < expiry_days）。"""
    if not last_observed:
        return False
    dt = _parse_timestamp(last_observed)
    if dt is None:
        return False
    return (_now() - dt) < timedelta(days=expiry_days)


# ─── 子命令：init ──────────────────────────────────────────────────────────────

def cmd_init(skill_dir: Path) -> None:
    """从 persona.md Layer 2 初始化 habits.json。已有 habits.json 时执行合并：新增条目，保留旧条目的 last_observed。"""
    persona_path = skill_dir / "persona.md"
    if not persona_path.exists():
        print(f"错误：找不到 persona.md（路径：{persona_path}）", file=sys.stderr)
        sys.exit(1)

    meta_path = skill_dir / "meta.json"
    default_ts: str = _now().isoformat()
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            default_ts = meta.get("updated_at", default_ts)
        except Exception:
            pass

    persona_content = persona_path.read_text(encoding="utf-8")
    new_habits = _parse_layer2_habits(persona_content)

    existing_data = _load_habits(skill_dir)
    expiry_days: int = existing_data.get("expiry_days", DEFAULT_EXPIRY_DAYS)

    # 以 text 为 key 构建已有习惯的索引（保留 last_observed）
    existing_index: dict[str, dict] = {h["text"]: h for h in existing_data.get("habits", [])}

    merged: list[dict] = []
    for h in new_habits:
        existing = existing_index.get(h["text"])
        last_observed = existing["last_observed"] if existing else default_ts
        active = _is_active(last_observed, expiry_days)
        merged.append(
            {
                "text": h["text"],
                "type": h["type"],
                "last_observed": last_observed,
                "active": active,
            }
        )

    data = {
        "habits": merged,
        "expiry_days": expiry_days,
        "last_scanned": existing_data.get("last_scanned"),
    }
    _save_habits(skill_dir, data)

    active_count = sum(1 for h in merged if h["active"])
    print(
        f"✅ habits.json 已初始化：{len(merged)} 个习惯条目"
        f"（{active_count} 个活跃，{len(merged) - active_count} 个过期）"
    )


# ─── 子命令：scan ──────────────────────────────────────────────────────────────

def cmd_scan(skill_dir: Path) -> None:
    """扫描 input/ 目录下的所有 TXT 文件，更新每个习惯的 last_observed。"""
    if not _TXT_PARSER_AVAILABLE:
        print("错误：无法导入 txt_parser，请确认工具目录结构正确。", file=sys.stderr)
        sys.exit(1)

    habits_path = _habits_path(skill_dir)
    if not habits_path.exists():
        print(
            f"错误：找不到 habits.json（路径：{habits_path}）。\n"
            "请先运行 init 子命令初始化。",
            file=sys.stderr,
        )
        sys.exit(1)

    data = _load_habits(skill_dir)
    habits: list[dict] = data.get("habits", [])
    expiry_days: int = data.get("expiry_days", DEFAULT_EXPIRY_DAYS)

    if not habits:
        print("habits.json 中暂无习惯条目，无需扫描。")
        return

    # 收集 input/ 下所有 .txt 文件
    input_dir = skill_dir / "input"
    if not input_dir.is_dir():
        print(f"警告：input/ 目录不存在（路径：{input_dir}），跳过扫描。")
        return

    txt_files = sorted(input_dir.rglob("*.txt"))
    if not txt_files:
        print("警告：input/ 目录下没有 .txt 文件，跳过扫描。")
        return

    # 为每个习惯维护"本次扫描发现的最新时间戳"
    # key: 习惯 text，value: 最新 datetime 或 None
    latest: dict[str, Optional[datetime]] = {h["text"]: None for h in habits}

    for txt_file in txt_files:
        try:
            messages = _parse_file(txt_file)
        except Exception as e:
            print(f"警告：解析 {txt_file.name} 时出错，已跳过：{e}", file=sys.stderr)
            continue

        for msg in messages:
            content: str = msg.get("content", "")
            ts_str: str = msg.get("timestamp", "")
            dt = _parse_timestamp(ts_str)

            for habit_text in latest:
                if habit_text in content:
                    if dt is not None:
                        prev = latest[habit_text]
                        if prev is None or dt > prev:
                            latest[habit_text] = dt

    # 更新习惯条目
    updated_count = 0
    for habit in habits:
        found_dt = latest.get(habit["text"])
        if found_dt is not None:
            new_ts = found_dt.isoformat()
            old_ts = habit.get("last_observed", "")
            old_dt = _parse_timestamp(old_ts)
            if old_dt is None or found_dt > old_dt:
                habit["last_observed"] = new_ts
                updated_count += 1
        # 每次扫描都重新计算 active
        habit["active"] = _is_active(habit.get("last_observed"), expiry_days)

    data["last_scanned"] = _now().isoformat()
    _save_habits(skill_dir, data)

    active_count = sum(1 for h in habits if h["active"])
    print(
        f"✅ 扫描完成：{len(txt_files)} 个文件，{len(habits)} 个习惯条目，"
        f"{updated_count} 个时间戳已更新。"
        f"（{active_count} 个活跃，{len(habits) - active_count} 个过期）"
    )


# ─── 子命令：check ─────────────────────────────────────────────────────────────

def cmd_check(skill_dir: Path) -> None:
    """列出所有过期习惯（active=false）。"""
    habits_path = _habits_path(skill_dir)
    if not habits_path.exists():
        print("尚未初始化 habits.json，请先运行 init 子命令。")
        return

    data = _load_habits(skill_dir)
    habits: list[dict] = data.get("habits", [])
    expiry_days: int = data.get("expiry_days", DEFAULT_EXPIRY_DAYS)
    last_scanned = data.get("last_scanned", "（从未扫描）")

    inactive = [h for h in habits if not h.get("active", True)]
    active = [h for h in habits if h.get("active", True)]

    print(f"习惯追踪报告（过期阈值：{expiry_days} 天，最后扫描：{last_scanned}）")
    print(f"共 {len(habits)} 个习惯：{len(active)} 个活跃，{len(inactive)} 个过期\n")

    if not inactive:
        print("✅ 所有习惯均在过期阈值内，无需调整。")
        return

    print("⚠️  以下习惯超过阈值未在聊天记录中出现（权重降低）：\n")
    for h in inactive:
        last = h.get("last_observed", "未知")[:10]
        print(f"  [{h['type']}]  {h['text']!r}  （最后见于：{last}）")


# ─── 公共 API（供 skill_writer.py 调用）───────────────────────────────────────

def init_habits(skill_dir: Path) -> None:
    """初始化习惯档案（供 skill_writer.create_skill 调用）。"""
    persona_path = skill_dir / "persona.md"
    if not persona_path.exists():
        return
    cmd_init(skill_dir)


def scan_habits(skill_dir: Path) -> None:
    """扫描聊天记录更新习惯时间戳（供 skill_writer.update_skill 调用）。"""
    if not _habits_path(skill_dir).exists():
        # 首次扫描前先初始化
        persona_path = skill_dir / "persona.md"
        if persona_path.exists():
            cmd_init(skill_dir)
        else:
            return
    cmd_scan(skill_dir)


def get_inactive_habits(skill_dir: Path) -> list[dict]:
    """返回过期习惯列表（供 input_loader.py 读取）。"""
    p = _habits_path(skill_dir)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    return [h for h in data.get("habits", []) if not h.get("active", True)]


# ─── CLI 入口 ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="习惯管理器 — 追踪 Layer 2 说话习惯的活跃状态",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for cmd_name, cmd_help in [
        ("init", "从 persona.md Layer 2 初始化 habits.json"),
        ("scan", "扫描 input/ 目录，更新习惯最后出现时间"),
        ("check", "列出所有过期习惯（active=false）"),
    ]:
        p = subparsers.add_parser(cmd_name, help=cmd_help)
        p.add_argument("--slug", required=True, help="同事 slug")
        p.add_argument(
            "--base-dir",
            default=DEFAULT_BASE_DIR,
            help=f"同事 Skill 根目录（默认：{DEFAULT_BASE_DIR}）",
        )

    args = parser.parse_args()
    base_dir = Path(args.base_dir).expanduser()
    skill_dir = base_dir / args.slug

    if not skill_dir.exists():
        print(f"错误：找不到 Skill 目录 {skill_dir}", file=sys.stderr)
        sys.exit(1)

    if args.command == "init":
        cmd_init(skill_dir)
    elif args.command == "scan":
        cmd_scan(skill_dir)
    elif args.command == "check":
        cmd_check(skill_dir)


if __name__ == "__main__":
    main()
