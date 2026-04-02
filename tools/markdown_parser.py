#!/usr/bin/env python3
"""
Markdown 文档解析器

解析本地 .md 文件，提取文档结构特征和写作模式，供影分身文档风格分析使用。

用法示例：
  # 解析单个文件，输出 JSON 分析结果
  python3 tools/markdown_parser.py --input article.md --output analysis.json

  # 解析目录（递归扫描所有 .md）
  python3 tools/markdown_parser.py --input ./docs/ --output analysis.json

  # 仅打印可供 LLM 直接读取的文字摘要
  python3 tools/markdown_parser.py --input ./docs/ --summary

  # 多路径输入
  python3 tools/markdown_parser.py --input a.md b.md ./notes/ --summary
"""

from __future__ import annotations

import re
import sys
import json
import argparse
import collections
from pathlib import Path
from typing import Any

# ─── 常量 ─────────────────────────────────────────────────────────────────────

# 结论先行的开篇关键词
_CONCLUSION_FIRST_PATTERNS = re.compile(
    r"(本文|这篇|总结|结论|核心观点|核心结论|简单来说|一句话|TL;DR|tldr|"
    r"答案是|我的判断|我认为|我的结论|直接说结论)",
    re.IGNORECASE,
)

# 常见开篇类型判断
_INTRO_QUESTION = re.compile(r"[？?]")
_INTRO_BG = re.compile(r"(在.{2,20}(场景|背景|情况|环境)|随着|当前|目前|现在|最近|近年)")
_INTRO_STATEMENT = re.compile(r"(本文|这篇文章|今天|我们|接下来)")

# 结尾模式
_OUTRO_SUMMARY = re.compile(r"(综上|总结|小结|回顾|总的来说|总而言之|最后)")
_OUTRO_CTA = re.compile(r"(欢迎|如果你|不妨|可以试试|建议|推荐|希望|期待)")
_OUTRO_OPEN = re.compile(r"(思考|探索|持续|未完待续|下一篇|后续|更多可能)")

# 噪声行（YAML frontmatter 分隔符、纯空行等）
_FRONTMATTER_SEP = re.compile(r"^---\s*$")

# 中英文字符计数（排除空格和标点，近似字数）
_WORD_COUNT = re.compile(r"[\u4e00-\u9fff]|[a-zA-Z0-9]+")


# ─── 单文件解析 ────────────────────────────────────────────────────────────────

def _strip_frontmatter(lines: list[str]) -> list[str]:
    """去除 YAML frontmatter（--- 之间的内容）。"""
    if not lines:
        return lines
    if _FRONTMATTER_SEP.match(lines[0]):
        for i in range(1, len(lines)):
            if _FRONTMATTER_SEP.match(lines[i]):
                return lines[i + 1 :]
    return lines


def _parse_document(text: str) -> dict[str, Any]:
    """解析单个 Markdown 文件，返回结构化特征字典。"""
    lines = text.splitlines()
    lines = _strip_frontmatter(lines)

    # ── 标题统计 ──
    heading_counts: dict[int, int] = collections.Counter()
    headings: list[tuple[int, str]] = []
    for line in lines:
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            level = len(m.group(1))
            heading_counts[level] += 1
            headings.append((level, m.group(2).strip()))

    total_headings = sum(heading_counts.values())
    heading_avg_len = (
        sum(len(h[1]) for h in headings) / len(headings) if headings else 0
    )

    # ── 段落统计 ──
    # 段落 = 被空行分隔的非标题、非代码块、非列表的连续文字块
    paragraphs: list[str] = []
    in_fence = False
    current: list[str] = []
    for line in lines:
        if re.match(r"^```", line):
            in_fence = not in_fence
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        if in_fence:
            continue
        stripped = line.strip()
        if not stripped:
            if current:
                paragraphs.append(" ".join(current))
                current = []
        elif re.match(r"^#{1,6}\s", line):
            if current:
                paragraphs.append(" ".join(current))
                current = []
        elif re.match(r"^[-*+]\s|^\d+\.\s|^>\s|^\|", line):
            if current:
                paragraphs.append(" ".join(current))
                current = []
        else:
            current.append(stripped)
    if current:
        paragraphs.append(" ".join(current))

    para_count = len(paragraphs)
    para_avg_len = sum(len(p) for p in paragraphs) / para_count if para_count else 0

    # ── 格式元素统计 ──
    unordered_list_lines = sum(
        1 for l in lines if re.match(r"^(\s*)[-*+]\s", l)
    )
    ordered_list_lines = sum(
        1 for l in lines if re.match(r"^(\s*)\d+\.\s", l)
    )
    # 嵌套列表深度
    max_list_depth = 0
    for line in lines:
        m = re.match(r"^(\s+)[-*+\d]", line)
        if m:
            depth = len(m.group(1)) // 2 + 1
            if depth > max_list_depth:
                max_list_depth = depth

    # 代码块
    fenced_blocks: list[str] = []
    in_fence2 = False
    fence_lang = ""
    for line in lines:
        m = re.match(r"^```(\w*)", line)
        if m and not in_fence2:
            in_fence2 = True
            fence_lang = m.group(1).strip()
        elif re.match(r"^```", line) and in_fence2:
            fenced_blocks.append(fence_lang)
            in_fence2 = False
            fence_lang = ""

    inline_code_count = sum(
        len(re.findall(r"`[^`\n]+`", l)) for l in lines
    )
    fenced_block_count = len(fenced_blocks)
    fenced_with_lang = sum(1 for lang in fenced_blocks if lang)

    # 表格
    table_lines = [l for l in lines if re.match(r"^\|", l.strip())]
    table_count = 0
    in_table = False
    table_cols_list: list[int] = []
    for line in lines:
        stripped = line.strip()
        if re.match(r"^\|", stripped):
            if not in_table:
                in_table = True
                table_count += 1
                cols = len([c for c in stripped.split("|") if c.strip()])
                table_cols_list.append(cols)
        else:
            in_table = False
    avg_table_cols = (
        sum(table_cols_list) / len(table_cols_list) if table_cols_list else 0
    )

    # 引用块
    blockquote_lines = sum(1 for l in lines if re.match(r"^>\s", l))

    # 分割线
    divider_count = sum(
        1 for l in lines if re.match(r"^(-{3,}|\*{3,}|_{3,})\s*$", l)
    )

    # 加粗 / 斜体 / 高亮
    bold_count = sum(len(re.findall(r"\*\*[^*\n]+\*\*|__[^_\n]+__", l)) for l in lines)
    # 匹配单星号斜体（*text*）和单下划线斜体（_text_），分别用两个简单模式
    _RE_ITALIC_STAR = re.compile(r"(?<!\*)\*(?!\*)[^*\n]+(?<!\*)\*(?!\*)")
    _RE_ITALIC_UNDER = re.compile(r"(?<!_)_(?!_)[^_\n]+(?<!_)_(?!_)")
    italic_count = sum(
        len(_RE_ITALIC_STAR.findall(l)) + len(_RE_ITALIC_UNDER.findall(l))
        for l in lines
    )
    highlight_count = sum(len(re.findall(r"==[^=\n]+==", l)) for l in lines)

    # ── 链接 / 图片引用 ──
    link_count = sum(len(re.findall(r"\[([^\]]+)\]\([^)]+\)", l)) for l in lines)
    image_count = sum(len(re.findall(r"!\[([^\]]*)\]\([^)]+\)", l)) for l in lines)

    # ── 字数统计 ──
    all_text = "\n".join(lines)
    word_matches = _WORD_COUNT.findall(all_text)
    word_count = len(word_matches)

    # ── 高频词 Top-20（中文字符 + 英文单词，过滤停用词）──
    _STOPWORDS = {
        "的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一",
        "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
        "没有", "看", "好", "自己", "这", "那", "它", "他", "她", "们",
        "但", "而", "所", "以", "被", "于", "其", "为", "如", "可", "与",
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "must", "can", "of", "in", "to",
        "for", "on", "with", "at", "by", "from", "as", "or", "and", "but",
        "not", "that", "this", "it", "i", "we", "you", "he", "she", "they",
    }
    # 中文单字统计意义低（多为虚词/助词），提取2-4字词组以捕获有意义的词汇；
    # 2字下限过滤单字噪声，4字上限避免跨句短语误匹配。
    cn_words = re.findall(r"[\u4e00-\u9fff]{2,4}", all_text)
    en_words = [w.lower() for w in re.findall(r"[a-zA-Z]{3,}", all_text)]
    all_words = cn_words + en_words
    freq_words = [
        (w, c)
        for w, c in collections.Counter(all_words).most_common(40)
        if w not in _STOPWORDS
    ][:20]

    # ── 开篇 / 结尾分析 ──
    # 取前 5 个非空非标题行作为"开篇"
    body_lines = [
        l.strip()
        for l in lines
        if l.strip()
        and not re.match(r"^#{1,6}\s", l)
        and not re.match(r"^[-*+]\s|^\d+\.\s|^>\s|^\|", l)
    ]
    intro_lines = body_lines[:5]
    outro_lines = body_lines[-5:] if len(body_lines) >= 5 else body_lines

    intro_text = " ".join(intro_lines)
    outro_text = " ".join(outro_lines)

    conclusion_first = bool(_CONCLUSION_FIRST_PATTERNS.search(intro_text))

    intro_type = "unknown"
    if _INTRO_QUESTION.search(intro_text):
        intro_type = "question"
    elif _INTRO_BG.search(intro_text):
        intro_type = "background"
    elif _INTRO_STATEMENT.search(intro_text):
        intro_type = "statement"

    outro_type = "unknown"
    if _OUTRO_SUMMARY.search(outro_text):
        outro_type = "summary"
    elif _OUTRO_CTA.search(outro_text):
        outro_type = "cta"
    elif _OUTRO_OPEN.search(outro_text):
        outro_type = "open"

    # ── 标题命名规律 ──
    heading_styles: dict[str, int] = collections.Counter()
    for _, htitle in headings:
        if re.search(r"[？?]$", htitle):
            heading_styles["question"] += 1
        elif re.match(r"^\d+[\.、]?\s", htitle) or re.search(r"\d+\s*(个|种|步|点|条|件|类)", htitle):
            heading_styles["numbered_list"] += 1
        elif re.match(r"^(如何|怎么|为什么|什么是|How|Why|What|When)", htitle, re.IGNORECASE):
            heading_styles["how_why"] += 1
        else:
            heading_styles["statement"] += 1

    # ── 第一人称使用 ──
    first_person_count = len(
        re.findall(r"(?<![^\s])(?:我|我们|本文|笔者|I\b|we\b)", all_text, re.IGNORECASE)
    )

    return {
        "headings": {
            "total": total_headings,
            "by_level": dict(heading_counts),
            "avg_title_len": round(heading_avg_len, 1),
            "naming_styles": dict(heading_styles),
        },
        "paragraphs": {
            "count": para_count,
            "avg_len": round(para_avg_len, 1),
        },
        "lists": {
            "unordered_lines": unordered_list_lines,
            "ordered_lines": ordered_list_lines,
            "max_nesting_depth": max_list_depth,
        },
        "code": {
            "fenced_blocks": fenced_block_count,
            "fenced_with_lang": fenced_with_lang,
            "inline_code": inline_code_count,
        },
        "tables": {
            "count": table_count,
            "avg_cols": round(avg_table_cols, 1),
        },
        "emphasis": {
            "bold": bold_count,
            "italic": italic_count,
            "highlight": highlight_count,
            "blockquotes": blockquote_lines,
        },
        "dividers": divider_count,
        "links": link_count,
        "images": image_count,
        "word_count": word_count,
        "top_words": freq_words,
        "structure": {
            "conclusion_first": conclusion_first,
            "intro_type": intro_type,
            "outro_type": outro_type,
        },
        "first_person_count": first_person_count,
        "intro_sample": intro_text[:200],
        "outro_sample": outro_text[:200],
    }


# ─── 多文件汇总 ────────────────────────────────────────────────────────────────

def _aggregate(docs: list[dict[str, Any]]) -> dict[str, Any]:
    """将多篇文档的解析结果汇总为整体写作风格统计。"""
    n = len(docs)
    if n == 0:
        return {}

    def avg(vals: list[float]) -> float:
        return round(sum(vals) / len(vals), 2) if vals else 0.0

    def sum_counter(field_path: list[str]) -> dict[str, int]:
        result: dict[str, int] = collections.Counter()
        for doc in docs:
            obj = doc
            for key in field_path:
                obj = obj.get(key, {})
            if isinstance(obj, dict):
                result.update(obj)
        return dict(result)

    word_counts = [d["word_count"] for d in docs]

    # 字数区间
    def _wc_range(wc: int) -> str:
        if wc < 500:
            return "<500"
        elif wc < 1000:
            return "500-1000"
        elif wc < 2000:
            return "1000-2000"
        elif wc < 5000:
            return "2000-5000"
        else:
            return "5000+"

    wc_dist: dict[str, int] = collections.Counter(_wc_range(w) for w in word_counts)

    # 汇总高频词
    combined_words: dict[str, int] = collections.Counter()
    for doc in docs:
        for word, cnt in doc.get("top_words", []):
            combined_words[word] += cnt
    top_words_agg = combined_words.most_common(20)

    # 结论先行比例
    conclusion_first_ratio = sum(
        1 for d in docs if d["structure"]["conclusion_first"]
    ) / n

    # 开篇 / 结尾类型分布
    intro_types: dict[str, int] = collections.Counter(
        d["structure"]["intro_type"] for d in docs
    )
    outro_types: dict[str, int] = collections.Counter(
        d["structure"]["outro_type"] for d in docs
    )

    # 标题命名风格汇总
    heading_styles_agg = sum_counter(["headings", "naming_styles"])

    # 代码块语言标注率
    total_fenced = sum(d["code"]["fenced_blocks"] for d in docs)
    total_fenced_lang = sum(d["code"]["fenced_with_lang"] for d in docs)
    lang_annotation_ratio = (
        round(total_fenced_lang / total_fenced, 2) if total_fenced > 0 else 0.0
    )

    # 列表密度（列表行 / 总字数）
    total_list_lines = sum(
        d["lists"]["unordered_lines"] + d["lists"]["ordered_lines"] for d in docs
    )
    total_words = sum(word_counts)
    list_density = round(total_list_lines / total_words * 100, 2) if total_words else 0

    # 格式元素每千字密度
    def _per_kw(total_val: int) -> float:
        return round(total_val / total_words * 1000, 1) if total_words else 0.0

    total_bold = sum(d["emphasis"]["bold"] for d in docs)
    total_tables = sum(d["tables"]["count"] for d in docs)
    total_links = sum(d["links"] for d in docs)
    total_images = sum(d["images"] for d in docs)
    total_blockquotes = sum(d["emphasis"]["blockquotes"] for d in docs)
    total_first_person = sum(d["first_person_count"] for d in docs)

    return {
        "doc_count": n,
        "word_count": {
            "total": total_words,
            "avg_per_doc": round(avg(word_counts), 0),
            "distribution": dict(wc_dist),
        },
        "headings": {
            "avg_per_doc": avg([d["headings"]["total"] for d in docs]),
            "level_distribution": sum_counter(["headings", "by_level"]),
            "avg_title_len": avg([d["headings"]["avg_title_len"] for d in docs]),
            "naming_styles": heading_styles_agg,
        },
        "paragraphs": {
            "avg_count_per_doc": avg([d["paragraphs"]["count"] for d in docs]),
            "avg_len": avg([d["paragraphs"]["avg_len"] for d in docs]),
        },
        "lists": {
            "density_per_100_words": list_density,
            "unordered_vs_ordered_ratio": (
                round(
                    sum(d["lists"]["unordered_lines"] for d in docs)
                    / max(1, sum(d["lists"]["ordered_lines"] for d in docs)),
                    1,
                )
            ),
            "max_nesting_depth": max(
                (d["lists"]["max_nesting_depth"] for d in docs), default=0
            ),
        },
        "code": {
            "fenced_blocks_total": total_fenced,
            "fenced_per_doc": round(total_fenced / n, 1),
            "lang_annotation_ratio": lang_annotation_ratio,
            "inline_code_per_kw": _per_kw(
                sum(d["code"]["inline_code"] for d in docs)
            ),
        },
        "tables": {
            "total": total_tables,
            "per_doc": round(total_tables / n, 2),
            "avg_cols": avg(
                [d["tables"]["avg_cols"] for d in docs if d["tables"]["count"] > 0]
            ),
        },
        "emphasis": {
            "bold_per_kw": _per_kw(total_bold),
            "blockquotes_total": total_blockquotes,
            "highlight_total": sum(d["emphasis"]["highlight"] for d in docs),
        },
        "links_per_kw": _per_kw(total_links),
        "images_per_kw": _per_kw(total_images),
        "first_person_per_kw": _per_kw(total_first_person),
        "structure": {
            "conclusion_first_ratio": round(conclusion_first_ratio, 2),
            "intro_type_distribution": dict(intro_types),
            "outro_type_distribution": dict(outro_types),
        },
        "top_words": top_words_agg,
    }


# ─── 文字摘要生成 ──────────────────────────────────────────────────────────────

def _format_summary(stats: dict[str, Any], file_paths: list[Path]) -> str:
    """将汇总统计转换为可供 LLM 直接阅读的文字摘要。"""
    n = stats.get("doc_count", 0)
    lines = [
        "# Markdown 文档写作风格分析摘要",
        "",
        f"**分析文档数**：{n} 篇",
        f"**来源路径**：{', '.join(str(p) for p in file_paths[:5])}"
        + (" 等" if len(file_paths) > 5 else ""),
        "",
    ]

    # 字数
    wc = stats.get("word_count", {})
    # 按区间的数值上限排序（"<500" → 500, "500-1000" → 1000, …, "5000+" → 999999）
    _RANGE_ORDER = {"<500": 500, "500-1000": 1000, "1000-2000": 2000, "2000-5000": 5000, "5000+": 999999}
    dist_items = sorted(
        wc.get("distribution", {}).items(),
        key=lambda kv: _RANGE_ORDER.get(kv[0], 0),
    )
    lines += [
        "## 一、写作量",
        f"- 总字数：{wc.get('total', 0)}",
        f"- 篇均字数：{wc.get('avg_per_doc', 0)}",
        "- 字数区间分布：" + "  ".join(f"{k}字：{v}篇" for k, v in dist_items),
        "",
    ]

    # 文档结构
    h = stats.get("headings", {})
    lvl = h.get("level_distribution", {})
    lvl_str = "  ".join(f"H{k}×{v}" for k, v in sorted(lvl.items())) if lvl else "无"
    ns = h.get("naming_styles", {})
    ns_str = "  ".join(f"{k}={v}" for k, v in sorted(ns.items(), key=lambda x: -x[1])) if ns else "无"
    lines += [
        "## 二、文档结构",
        f"- 篇均标题数：{h.get('avg_per_doc', 0)}",
        f"- 标题层级分布：{lvl_str}",
        f"- 标题平均字数：{h.get('avg_title_len', 0)}",
        f"- 标题命名风格：{ns_str}（statement=陈述, question=疑问, numbered_list=数字清单, how_why=如何/为什么）",
        "",
    ]

    # 段落
    p = stats.get("paragraphs", {})
    lines += [
        "## 三、段落风格",
        f"- 篇均段落数：{p.get('avg_count_per_doc', 0)}",
        f"- 段落平均字数：{p.get('avg_len', 0)}（<80字=短句密集，80-200=适中，>200=长段）",
        "",
    ]

    # 格式偏好
    lst = stats.get("lists", {})
    code = stats.get("code", {})
    tbl = stats.get("tables", {})
    em = stats.get("emphasis", {})
    lines += [
        "## 四、格式偏好",
        f"- 列表密度：每100字含 {lst.get('density_per_100_words', 0)} 行列表项（>3=重度列表用户，1-3=适中，<1=倾向段落）",
        f"- 有序/无序列表比：{lst.get('unordered_vs_ordered_ratio', 0)}:1（无序:有序）",
        f"- 列表最大嵌套深度：{lst.get('max_nesting_depth', 0)} 层",
        f"- 代码块数（篇均）：{code.get('fenced_per_doc', 0)}",
        f"- 代码块语言标注率：{round(code.get('lang_annotation_ratio', 0)*100)}%",
        f"- 行内代码密度：每千字 {code.get('inline_code_per_kw', 0)} 处",
        f"- 表格（篇均）：{tbl.get('per_doc', 0)} 个，均 {tbl.get('avg_cols', 0)} 列",
        f"- 加粗密度：每千字 {em.get('bold_per_kw', 0)} 处",
        f"- 引用块（blockquote）总数：{em.get('blockquotes_total', 0)}",
        f"- 高亮（==text==）总数：{em.get('highlight_total', 0)}",
        "",
    ]

    # 内容模式
    st = stats.get("structure", {})
    cfr = st.get("conclusion_first_ratio", 0)
    intro_dist = st.get("intro_type_distribution", {})
    outro_dist = st.get("outro_type_distribution", {})
    intro_str = "  ".join(f"{k}={v}篇" for k, v in sorted(intro_dist.items(), key=lambda x: -x[1])) if intro_dist else "无"
    outro_str = "  ".join(f"{k}={v}篇" for k, v in sorted(outro_dist.items(), key=lambda x: -x[1])) if outro_dist else "无"
    lines += [
        "## 五、内容模式",
        f"- 结论先行比例：{round(cfr*100)}%（≥50% 表示习惯性结论先行）",
        f"- 开篇类型分布：{intro_str}（question=疑问式, background=背景铺垫, statement=陈述式, unknown=其他）",
        f"- 结尾类型分布：{outro_str}（summary=总结型, cta=行动号召, open=开放性, unknown=其他）",
        f"- 第一人称密度：每千字 {stats.get('first_person_per_kw', 0)} 次",
        f"- 链接密度：每千字 {stats.get('links_per_kw', 0)} 个",
        f"- 图片密度：每千字 {stats.get('images_per_kw', 0)} 个",
        "",
    ]

    # 高频词
    top_words = stats.get("top_words", [])
    if top_words:
        words_str = "、".join(f"{w}({c})" for w, c in top_words[:15])
        lines += [
            "## 六、高频词（Top 15）",
            words_str,
            "",
        ]

    lines += [
        "---",
        "> 以上数据由 markdown_parser.py 自动提取，供 LLM 进行文档写作风格分析使用。",
    ]

    return "\n".join(lines)


# ─── 文件收集 ─────────────────────────────────────────────────────────────────

def _collect_md_files(inputs: list[str], recursive: bool = True) -> list[Path]:
    """从输入路径列表中收集所有 .md 文件。"""
    result: list[Path] = []
    for inp in inputs:
        p = Path(inp)
        if p.is_file():
            if p.suffix.lower() in {".md", ".markdown"}:
                result.append(p)
            else:
                print(f"[警告] 跳过非 Markdown 文件：{p}", file=sys.stderr)
        elif p.is_dir():
            pattern = "**/*.md" if recursive else "*.md"
            found = sorted(p.glob(pattern))
            pattern2 = "**/*.markdown" if recursive else "*.markdown"
            found += sorted(p.glob(pattern2))
            if not found:
                print(f"[警告] 目录中未找到 .md 文件：{p}", file=sys.stderr)
            result.extend(found)
        else:
            print(f"[警告] 路径不存在：{p}", file=sys.stderr)
    return result


def _read_file(path: Path) -> str:
    """读取文件，自动尝试多种编码。"""
    for enc in ("utf-8", "utf-8-sig", "gbk", "gb18030", "big5"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return path.read_text(encoding="latin-1", errors="replace")


# ─── 主入口 ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="解析本地 Markdown 文件，提取文档写作风格特征。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input", "-i",
        nargs="+",
        required=True,
        metavar="PATH",
        help="输入路径（.md 文件或目录），支持多个",
    )
    parser.add_argument(
        "--output", "-o",
        metavar="FILE",
        help="将 JSON 结果写入该文件（默认输出到 stdout）",
    )
    parser.add_argument(
        "--summary", "-s",
        action="store_true",
        help="输出可供 LLM 阅读的文字摘要（而非 JSON）",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="目录解析不递归子目录",
    )
    args = parser.parse_args()

    recursive = not args.no_recursive
    md_files = _collect_md_files(args.input, recursive=recursive)

    if not md_files:
        print("[错误] 未找到任何 Markdown 文件，请检查路径。", file=sys.stderr)
        sys.exit(1)

    print(f"[信息] 找到 {len(md_files)} 个 Markdown 文件，开始解析…", file=sys.stderr)

    per_doc: list[dict[str, Any]] = []
    for fp in md_files:
        text = _read_file(fp)
        doc_stats = _parse_document(text)
        doc_stats["file"] = str(fp)
        per_doc.append(doc_stats)

    agg = _aggregate(per_doc)

    if args.summary:
        summary_text = _format_summary(agg, md_files)
        if args.output:
            Path(args.output).write_text(summary_text, encoding="utf-8")
            print(f"[信息] 摘要已写入：{args.output}", file=sys.stderr)
        else:
            print(summary_text)
    else:
        output_data = {
            "summary": agg,
            "per_document": per_doc,
        }
        json_str = json.dumps(output_data, ensure_ascii=False, indent=2)
        if args.output:
            Path(args.output).write_text(json_str, encoding="utf-8")
            print(f"[信息] JSON 结果已写入：{args.output}", file=sys.stderr)
        else:
            print(json_str)


if __name__ == "__main__":
    main()
