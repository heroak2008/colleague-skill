#!/usr/bin/env python3
"""
TXT 聊天记录解析器

支持的格式：
  格式 1 — 带时间戳（完整日期时间 + 说话人：内容）
      2024-01-01 10:00:00 张三：消息内容
      2024-01-01 10:00 张三：消息内容
      2024/01/01 10:00 张三：消息内容
  格式 2 — 仅日期 + 说话人
      2024-01-01 张三：消息内容
  格式 3 — 微信导出式（时间单独一行，发送人单独一行，内容另起一行）
      2024-01-01 10:00:00
      张三
      消息内容
  格式 4 — 说话人在行首（无时间）
      张三：消息内容
      张三: 消息内容
  格式 5 — Markdown 引用式
      **张三**: 消息内容
  格式 6 — 企业工号格式（名字+工号 制表符 时间，内容另起一行）
      张三(z00611745)\t2026-01-04 15:58:23
      消息内容

每条消息解析为 {"timestamp": str, "sender": str, "content": str}。

用法示例：
  # 解析单个文件，过滤目标人
  python3 tools/txt_parser.py --input chat.txt --target "张三" --output out.txt

  # 解析整个目录（递归），交互式选择目标人
  python3 tools/txt_parser.py --input ./chats/ --output out.txt

  # 解析多个路径
  python3 tools/txt_parser.py --input chat1.txt chat2.txt --target "张三"

  # 仅列出识别到的说话人（用于确认 --target 参数）
  python3 tools/txt_parser.py --input ./chats/ --list-speakers
"""

from __future__ import annotations

import re
import sys
import argparse
from pathlib import Path
from typing import Iterator

# ─── 正则模式 ──────────────────────────────────────────────────────────────────

# 格式 1/2：时间 + 说话人：内容（时间含日期，可选 HH:MM[:SS]）
_RE_TIMESTAMP_SENDER = re.compile(
    r"^(?P<time>\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:[T \t]\d{1,2}:\d{2}(?::\d{2})?)?)"
    r"[ \t]+(?P<sender>[^\n:：]{1,40}?)[ \t]*[：:]\s*(?P<content>.+)$"
)

# 格式 4：说话人：内容（无时间）
_RE_SENDER_ONLY = re.compile(
    r"^(?P<sender>[^\n:：]{1,40}?)[ \t]*[：:]\s*(?P<content>.+)$"
)

# 格式 5：Markdown 加粗 **说话人**: 内容
_RE_MD_SENDER = re.compile(
    r"^\*\*(?P<sender>[^\*\n]{1,40}?)\*\*[ \t]*[：:]\s*(?P<content>.+)$"
)

# 格式 3 时间行（微信导出：时间单独一行）
_RE_TIMESTAMP_LINE = re.compile(
    r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:[T \t]\d{1,2}:\d{2}(?::\d{2})?)?$"
)

# 格式 6：企业工号格式 — "姓名(工号)\t时间戳"，内容另起一行
# 例：张三(z00611745)\t2026-01-04 15:58:23
_RE_CORP_HEADER = re.compile(
    r"^(?P<sender>[^\(\n]+)\([^\)]+\)\t(?P<time>\d{4}[-/]\d{1,2}[-/]\d{1,2}"
    r"(?:[T \t]\d{1,2}:\d{2}(?::\d{2})?)?)$"
)

# 噪声消息（系统提示、撤回、表情包等）
_NOISE_PATTERNS = re.compile(
    r"^(?:\[图片\]|\[语音\]|\[视频\]|\[文件\]|\[表情\]|\[位置\]"
    r"|\[撤回了一条消息\]|撤回了一条消息"
    r"|对方撤回了一条消息|以下为系统消息|以下消息已被撤回"
    r"|\[sticker\]|\[emoji\])$",
    re.IGNORECASE,
)

# 最小内容长度（去除单纯符号/表情的行）
_MIN_CONTENT_LEN = 1

# 流式读取的行批次大小
_CHUNK_LINES = 5000


# ─── 解析核心 ──────────────────────────────────────────────────────────────────

def _is_noise(content: str) -> bool:
    s = content.strip()
    return bool(_NOISE_PATTERNS.match(s)) or len(s) < _MIN_CONTENT_LEN


def _iter_lines(path: Path) -> Iterator[str]:
    """逐行读取文件，自动探测编码，支持大文件流式处理。"""
    # utf-8-sig 优先：可同时处理带 BOM 和不带 BOM 的 UTF-8 文件
    encodings = ["utf-8-sig", "utf-8", "gbk", "gb18030", "big5", "latin-1"]
    for enc in encodings:
        try:
            with path.open("r", encoding=enc, errors="strict") as fh:
                for line in fh:
                    yield line.rstrip("\n").rstrip("\r")
            return
        except (UnicodeDecodeError, LookupError):
            continue
    # 最终兜底：忽略解码错误
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            yield line.rstrip("\n").rstrip("\r")


def _parse_lines(lines: Iterator[str]) -> list[dict]:
    """
    对一个文件的行序列进行解析，返回消息列表。
    每条消息：{"timestamp": str, "sender": str, "content": str}
    """
    messages: list[dict] = []
    pending_time: str = ""
    pending_sender: str = ""
    pending_lines: list[str] = []

    def _flush():
        if pending_sender and pending_lines:
            content = " ".join(pending_lines).strip()
            if not _is_noise(content):
                messages.append({
                    "timestamp": pending_time,
                    "sender": pending_sender,
                    "content": content,
                })

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        # ── 格式 6：企业工号格式 — "姓名(工号)\t时间"，内容另起一行
        # 例：张三(z00611745)\t2026-01-04 15:58:23
        # 注意：原始行保留制表符，strip() 会去掉行首尾空白但不会去掉中间的 \t
        m = _RE_CORP_HEADER.match(raw.rstrip("\r\n"))
        if m:
            _flush()
            pending_time = m.group("time").strip()
            pending_sender = m.group("sender").strip()
            pending_lines = []
            continue

        # ── 格式 5：**说话人**: 内容
        m = _RE_MD_SENDER.match(line)
        if m:
            _flush()
            pending_time = ""
            pending_sender = m.group("sender").strip()
            pending_lines = [m.group("content").strip()]
            continue

        # ── 格式 3：时间单独一行（微信导出）
        # 必须在格式 1/2 之前检查，避免把纯时间行（如 "2024-01-01 10:00:00"）
        # 误当成 "时间 + 说话人：内容" 解析（时间末尾的 HH:MM 被误认为 sender:content）
        if _RE_TIMESTAMP_LINE.match(line):
            _flush()
            pending_time = line
            pending_sender = ""
            pending_lines = []
            continue

        # ── 格式 1/2：时间 + 说话人：内容（同行）
        m = _RE_TIMESTAMP_SENDER.match(line)
        if m:
            _flush()
            pending_time = m.group("time").strip()
            pending_sender = m.group("sender").strip()
            pending_lines = [m.group("content").strip()]
            continue

        # ── 格式 4：说话人：内容（无时间）
        # 仅在还没有 pending_sender 或时间行后的说话人行时触发
        m = _RE_SENDER_ONLY.match(line)
        if m:
            candidate_sender = m.group("sender").strip()
            candidate_content = m.group("content").strip()
            # 避免误把 URL 或句子中的冒号当做分隔符：
            # 说话人字段不应含空格超过 2 个单词，且不应以标点结尾
            if (
                len(candidate_sender) <= 20
                and not candidate_sender.endswith((".", "。", "，", ",", "、"))
                and "http" not in candidate_sender
            ):
                # 格式 3/6 的后续内容行：已有时间但尚无 sender，且本行含冒号
                if pending_time and not pending_sender and not pending_lines:
                    pending_sender = candidate_sender
                    pending_lines = [candidate_content]
                else:
                    _flush()
                    pending_time = ""
                    pending_sender = candidate_sender
                    pending_lines = [candidate_content]
                continue

        # ── 格式 3 的第二行（纯发送人，尚无冒号）
        if pending_time and not pending_sender:
            pending_sender = line
            pending_lines = []
            continue

        # ── 续行（上条消息的后续内容）
        if pending_sender:
            pending_lines.append(line)

    _flush()
    return messages


def parse_file(path: Path) -> list[dict]:
    """解析单个 TXT 文件，返回消息列表。"""
    if path.stat().st_size == 0:
        return []
    return _parse_lines(_iter_lines(path))


def parse_paths(
    inputs: list[str],
    recursive: bool = True,
    relation: str | None = None,
) -> list[dict]:
    """
    解析一组路径（文件或目录），返回所有消息（按文件顺序）。
    directories：若 recursive=True 则递归查找 *.txt。

    relation：可选，为所有解析出的消息附加关系标注。
      接受 "superior"（上级）、"peer"（同级）、"junior"（后辈）或 None（未标注）。
    """
    all_messages: list[dict] = []
    visited: set[Path] = set()

    def _add_file(p: Path):
        real = p.resolve()
        if real in visited:
            return
        visited.add(real)
        msgs = parse_file(p)
        if relation is not None:
            for m in msgs:
                m["relation"] = relation
        all_messages.extend(msgs)

    for raw in inputs:
        p = Path(raw).expanduser()
        if not p.exists():
            print(f"警告：路径不存在，已跳过：{p}", file=sys.stderr)
            continue
        if p.is_file():
            _add_file(p)
        elif p.is_dir():
            pattern = "**/*.txt" if recursive else "*.txt"
            found = sorted(p.glob(pattern))
            if not found:
                print(f"警告：目录中未找到 .txt 文件：{p}", file=sys.stderr)
            for f in found:
                _add_file(f)
        else:
            print(f"警告：不支持的路径类型，已跳过：{p}", file=sys.stderr)

    return all_messages


# ─── 过滤与提取 ────────────────────────────────────────────────────────────────

def get_speakers(messages: list[dict]) -> list[str]:
    """返回去重后的说话人列表（按出现次数降序）。"""
    counts: dict[str, int] = {}
    for msg in messages:
        s = msg["sender"]
        counts[s] = counts.get(s, 0) + 1
    return sorted(counts.keys(), key=lambda k: -counts[k])


def filter_by_target(messages: list[dict], target: str) -> list[dict]:
    """过滤出目标人发出的消息（支持部分匹配）。"""
    return [m for m in messages if target in m["sender"]]


_RELATION_LABELS = {
    "superior": "跟领导的对话（上级视角）",
    "peer": "跟同级的对话",
    "junior": "跟后辈的对话（下级视角）",
}

_VALID_RELATIONS = set(_RELATION_LABELS.keys())


def extract_key_content(messages: list[dict]) -> dict:
    """
    将消息分类提取：
    - long_messages：>50 字，可能含观点/方案
    - decision_messages：含决策类关键词
    - daily_messages：其他日常沟通

    同时按 relation（superior / peer / junior / None）做二级分组，
    结果存于 by_relation，每个 bucket 的结构与顶层相同。
    """
    long_messages: list[dict] = []
    decision_messages: list[dict] = []
    daily_messages: list[dict] = []

    decision_keywords = [
        "同意", "不行", "觉得", "建议", "应该", "不应该", "可以", "不可以",
        "方案", "思路", "考虑", "决定", "确认", "拒绝", "推进", "暂缓",
        "没问题", "有问题", "风险", "评估", "判断", "计划", "优先",
    ]

    # 按 relation 分桶
    by_relation: dict[str, dict] = {
        "superior": {"long_messages": [], "decision_messages": [], "daily_messages": []},
        "peer":     {"long_messages": [], "decision_messages": [], "daily_messages": []},
        "junior":   {"long_messages": [], "decision_messages": [], "daily_messages": []},
        "unknown":  {"long_messages": [], "decision_messages": [], "daily_messages": []},
    }

    for msg in messages:
        content = msg["content"]
        relation = msg.get("relation") or "unknown"
        if relation not in by_relation:
            relation = "unknown"

        if len(content) > 50:
            bucket = "long_messages"
        elif any(kw in content for kw in decision_keywords):
            bucket = "decision_messages"
        else:
            bucket = "daily_messages"

        # 顶层列表（全量）
        if bucket == "long_messages":
            long_messages.append(msg)
        elif bucket == "decision_messages":
            decision_messages.append(msg)
        else:
            daily_messages.append(msg)

        # 按关系分桶
        by_relation[relation][bucket].append(msg)

    return {
        "long_messages": long_messages,
        "decision_messages": decision_messages,
        "daily_messages": daily_messages,
        "total_count": len(messages),
        "by_relation": by_relation,
    }


# ─── 输出格式化 ────────────────────────────────────────────────────────────────

def _format_relation_section(relation_key: str, bucket: dict) -> list[str]:
    """为单个关系类型（superior/peer/junior/unknown）生成输出段落。"""
    label = _RELATION_LABELS.get(relation_key, "未分类对话")
    total = (
        len(bucket["long_messages"])
        + len(bucket["decision_messages"])
        + len(bucket["daily_messages"])
    )
    if total == 0:
        return []

    lines = [
        f"## {label}",
        f"消息数：{total}",
        "",
        "### 长消息（观点/方案类，权重最高）",
        "",
    ]
    for msg in bucket["long_messages"]:
        ts = f"[{msg['timestamp']}] " if msg["timestamp"] else ""
        lines.append(f"{ts}{msg['content']}")
        lines.append("")

    lines += ["### 决策类回复", ""]
    for msg in bucket["decision_messages"]:
        ts = f"[{msg['timestamp']}] " if msg["timestamp"] else ""
        lines.append(f"{ts}{msg['content']}")
        lines.append("")

    lines += ["### 日常沟通（风格参考）", ""]
    for msg in bucket["daily_messages"][:100]:
        ts = f"[{msg['timestamp']}] " if msg["timestamp"] else ""
        lines.append(f"{ts}{msg['content']}")

    return lines


def format_output(target_name: str, extracted: dict) -> str:
    """格式化提取结果，供 AI 分析使用。

    当 extracted 中存在 by_relation 且有多于 unknown 的关系分桶时，
    按关系类型分段输出；否则沿用原有的统一输出格式。
    """
    by_relation: dict = extracted.get("by_relation", {})
    has_relation_data = any(
        (
            len(by_relation.get(r, {}).get("long_messages", []))
            + len(by_relation.get(r, {}).get("decision_messages", []))
            + len(by_relation.get(r, {}).get("daily_messages", []))
        ) > 0
        for r in ("superior", "peer", "junior")
    )

    lines = [
        "# TXT 聊天记录提取结果",
        f"目标人物：{target_name}",
        f"总消息数：{extracted['total_count']}",
        "",
        "---",
        "",
    ]

    if has_relation_data:
        # 按关系类型分段输出
        for rel_key in ("superior", "peer", "junior", "unknown"):
            bucket = by_relation.get(rel_key, {})
            section = _format_relation_section(rel_key, bucket)
            if section:
                lines.extend(section)
                lines += ["", "---", ""]
    else:
        # 无关系标注：沿用原有统一输出格式
        lines += [
            "## 长消息（观点/方案类，权重最高）",
            "",
        ]
        for msg in extracted["long_messages"]:
            ts = f"[{msg['timestamp']}] " if msg["timestamp"] else ""
            lines.append(f"{ts}{msg['content']}")
            lines.append("")

        lines += ["---", "", "## 决策类回复", ""]
        for msg in extracted["decision_messages"]:
            ts = f"[{msg['timestamp']}] " if msg["timestamp"] else ""
            lines.append(f"{ts}{msg['content']}")
            lines.append("")

        lines += ["---", "", "## 日常沟通（风格参考）", ""]
        for msg in extracted["daily_messages"][:100]:
            ts = f"[{msg['timestamp']}] " if msg["timestamp"] else ""
            lines.append(f"{ts}{msg['content']}")

    return "\n".join(lines)


# ─── CLI 入口 ─────────────────────────────────────────────────────────────────

def _interactive_select_target(speakers: list[str]) -> str:
    """交互式选择目标说话人。"""
    print("\n检测到以下说话人（按消息数量排序）：\n")
    for i, sp in enumerate(speakers, 1):
        print(f"  [{i}] {sp}")
    print()
    while True:
        raw = input("请输入目标同事的姓名（或序号）：").strip()
        if not raw:
            continue
        # 序号选择
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(speakers):
                return speakers[idx]
            print(f"序号超出范围，请输入 1–{len(speakers)}")
            continue
        # 直接输入名字（支持部分匹配）
        matched = [s for s in speakers if raw in s]
        if len(matched) == 1:
            return matched[0]
        if len(matched) > 1:
            print(f"匹配到多个说话人：{matched}，请输入更精确的名字")
            continue
        # 允许直接使用用户输入（即便当前消息里没有完全匹配）
        confirm = input(f"未找到精确匹配 '{raw}'，仍然使用此名称过滤？[y/N] ").strip().lower()
        if confirm in ("y", "yes"):
            return raw


def main() -> None:
    parser = argparse.ArgumentParser(
        description="TXT 聊天记录解析器 — 解析聊天记录，提取目标同事的发言",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 解析单个文件，过滤 "张三"
  python3 tools/txt_parser.py --input chat.txt --target "张三" --output out.txt

  # 解析目录（递归），交互式选择目标人
  python3 tools/txt_parser.py --input ./chats/ --output out.txt

  # 列出识别到的全部说话人
  python3 tools/txt_parser.py --input chat.txt --list-speakers

  # 解析多个文件/目录，不递归
  python3 tools/txt_parser.py --input chat1.txt chat2.txt --target "李四" --no-recursive

支持的 TXT 格式（详见 README）：
  格式 1：  2024-01-01 10:00:00 张三：内容
  格式 2：  2024-01-01 张三：内容
  格式 3：  时间单独一行 / 发送人单独一行 / 内容另起一行（微信导出式）
  格式 4：  张三：内容（无时间）
  格式 5：  **张三**: 内容（Markdown 加粗式）
  格式 6：  张三(工号)<TAB>时间 / 内容另起一行（企业工号格式）
""",
    )
    parser.add_argument(
        "--input",
        nargs="+",
        required=True,
        metavar="PATH",
        help="输入文件或目录路径（可多个）",
    )
    parser.add_argument(
        "--target",
        default=None,
        metavar="NAME",
        help="目标同事姓名（用于过滤消息；未指定时交互式选择）",
    )
    parser.add_argument(
        "--output",
        default=None,
        metavar="FILE",
        help="输出文件路径（默认打印到 stdout）",
    )
    parser.add_argument(
        "--list-speakers",
        action="store_true",
        help="列出识别到的全部说话人后退出（不输出消息内容）",
    )
    parser.add_argument(
        "--relation",
        default=None,
        choices=["superior", "peer", "junior"],
        metavar="RELATION",
        help=(
            "聊天对象的关系类型（可选）："
            "superior（上级/领导）、peer（同级/平级）、junior（后辈/下属）。"
            "未指定则不附加关系标注（等同于混合文件）。"
        ),
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="处理目录时不递归，仅读取一级 .txt 文件",
    )
    parser.add_argument(
        "--min-messages",
        type=int,
        default=10,
        metavar="N",
        help="目标同事消息数低于 N 时给出警告（默认：10）",
    )

    args = parser.parse_args()
    recursive = not args.no_recursive

    # ── 解析所有输入
    all_messages = parse_paths(args.input, recursive=recursive, relation=args.relation)

    if not all_messages:
        print("错误：未解析到任何消息，请检查文件路径和格式。", file=sys.stderr)
        sys.exit(1)

    speakers = get_speakers(all_messages)

    # ── 仅列出说话人
    if args.list_speakers:
        print(f"共解析 {len(all_messages)} 条消息，识别到以下说话人（按消息数降序）：\n")
        counts: dict[str, int] = {}
        for m in all_messages:
            counts[m["sender"]] = counts.get(m["sender"], 0) + 1
        for sp in speakers:
            print(f"  {sp}（{counts[sp]} 条）")
        sys.exit(0)

    # ── 确定目标同事
    target = args.target
    if not target:
        if not sys.stdin.isatty():
            print(
                "错误：未指定 --target，且当前非交互模式。\n"
                "请使用 --target 指定目标同事，或 --list-speakers 查看说话人列表。",
                file=sys.stderr,
            )
            sys.exit(1)
        target = _interactive_select_target(speakers)

    # ── 过滤目标人消息
    filtered = filter_by_target(all_messages, target)

    if not filtered:
        print(
            f"警告：未找到 '{target}' 发出的任何消息。\n"
            "建议：\n"
            "  1. 使用 --list-speakers 查看文件中实际的说话人名称\n"
            "  2. 检查姓名拼写（支持部分匹配，例如 '张三' 可匹配 '张三（已离职）'）\n"
            "  3. 确认聊天记录格式是否受支持（见 README 中的格式说明）",
            file=sys.stderr,
        )
        sys.exit(1)

    if len(filtered) < args.min_messages:
        print(
            f"⚠️  注意：'{target}' 仅有 {len(filtered)} 条消息，可能不足以生成高质量 Skill。\n"
            "建议补充更多聊天记录后再生成，或结合手动描述使用。",
            file=sys.stderr,
        )

    # ── 提取关键内容并输出
    extracted = extract_key_content(filtered)
    output_text = format_output(target, extracted)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_text, encoding="utf-8")
        relation_info = f"   关系类型：{args.relation}" if args.relation else ""
        print(
            f"✅ 已输出到 {args.output}\n"
            f"   目标人物：{target}\n"
            f"   消息总数：{len(filtered)}\n"
            f"   长消息：{len(extracted['long_messages'])}  "
            f"决策类：{len(extracted['decision_messages'])}  "
            f"日常：{len(extracted['daily_messages'])}"
            + (f"\n{relation_info}" if relation_info else "")
        )
    else:
        print(output_text)


if __name__ == "__main__":
    main()
