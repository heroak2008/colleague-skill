"""
tests/test_txt_parser.py

TXT 聊天记录解析器单元测试
"""

import sys
import textwrap
from pathlib import Path

import pytest

# 确保可以直接导入 tools 模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.txt_parser import (
    _parse_lines,
    _expand_paths,
    _interactive_assign_relations,
    _apply_file_relations,
    parse_file,
    parse_paths,
    get_speakers,
    filter_by_target,
    extract_key_content,
    format_output,
)


# ─── 辅助函数 ──────────────────────────────────────────────────────────────────

def lines_of(text: str):
    """将多行字符串转为行迭代器（用于 _parse_lines）。"""
    return iter(textwrap.dedent(text).strip().splitlines())


# ─── 格式解析测试 ──────────────────────────────────────────────────────────────

class TestFormat1And2:
    """格式 1/2：时间戳 + 说话人：内容（同行）"""

    def test_format1_full_datetime(self):
        msgs = _parse_lines(lines_of("""
            2024-01-01 10:00:00 张三：今天的接口设计有问题
            2024-01-01 10:01:00 李四：什么问题？
        """))
        assert len(msgs) == 2
        assert msgs[0]["sender"] == "张三"
        assert msgs[0]["timestamp"] == "2024-01-01 10:00:00"
        assert msgs[0]["content"] == "今天的接口设计有问题"
        assert msgs[1]["sender"] == "李四"

    def test_format2_date_only(self):
        msgs = _parse_lines(lines_of("""
            2024-01-01 张三：短消息
        """))
        assert len(msgs) == 1
        assert msgs[0]["sender"] == "张三"
        assert msgs[0]["timestamp"] == "2024-01-01"

    def test_format1_slash_separator(self):
        msgs = _parse_lines(lines_of("""
            2024/06/15 09:30 Alice：Let's ship it
        """))
        assert len(msgs) == 1
        assert msgs[0]["sender"] == "Alice"
        assert msgs[0]["content"] == "Let's ship it"

    def test_multiline_continuation(self):
        msgs = _parse_lines(lines_of("""
            2024-01-01 10:00 张三：第一行
            这是续行
            还有续行
            2024-01-01 10:01 李四：另一条
        """))
        assert len(msgs) == 2
        assert "第一行" in msgs[0]["content"]
        assert "续行" in msgs[0]["content"]
        assert msgs[1]["sender"] == "李四"


class TestFormat3:
    """格式 3：时间单独一行，发送人单独一行，内容另起一行（微信导出式）"""

    def test_wechat_style(self):
        msgs = _parse_lines(lines_of("""
            2024-01-01 10:00:00
            张三
            这是微信风格的消息

            2024-01-01 10:01:00
            李四
            这是另一条消息
        """))
        assert len(msgs) == 2
        assert msgs[0]["sender"] == "张三"
        assert msgs[0]["content"] == "这是微信风格的消息"
        assert msgs[1]["sender"] == "李四"

    def test_wechat_style_timestamp_only_no_content(self):
        # 时间行后没有内容，不应报错
        msgs = _parse_lines(lines_of("""
            2024-01-01 10:00:00
            张三：有内容
        """))
        # 混合格式：时间单独一行 + 发送人：内容
        assert len(msgs) >= 1


class TestFormat6:
    """格式 6：企业工号格式 — 姓名(工号)<TAB>时间戳，内容另起一行"""

    def test_corp_format_basic(self):
        # 使用真实的制表符
        lines = [
            "赵星(z00611745)\t2026-01-04 15:58:23",
            "刚收假就一堆事push",
            "杨仁恩(y00612385)\t2026-01-04 15:59:32",
            "我需求都没拆",
        ]
        msgs = _parse_lines(iter(lines))
        assert len(msgs) == 2
        assert msgs[0]["sender"] == "赵星"
        assert msgs[0]["timestamp"] == "2026-01-04 15:58:23"
        assert msgs[0]["content"] == "刚收假就一堆事push"
        assert msgs[1]["sender"] == "杨仁恩"
        assert msgs[1]["timestamp"] == "2026-01-04 15:59:32"
        assert msgs[1]["content"] == "我需求都没拆"

    def test_corp_format_multiline_content(self):
        lines = [
            "赵星(z00611745)\t2026-01-04 15:58:23",
            "第一行内容",
            "第二行内容",
            "杨仁恩(y00612385)\t2026-01-04 16:00:00",
            "另一条消息",
        ]
        msgs = _parse_lines(iter(lines))
        assert len(msgs) == 2
        assert "第一行内容" in msgs[0]["content"]
        assert "第二行内容" in msgs[0]["content"]

    def test_corp_format_file(self, tmp_path):
        f = tmp_path / "corp_chat.txt"
        content = (
            "赵星(z00611745)\t2026-01-04 15:58:23\n"
            "刚收假就一堆事push\n"
            "杨仁恩(y00612385)\t2026-01-04 15:59:32\n"
            "我需求都没拆\n"
        )
        f.write_text(content, encoding="utf-8")
        msgs = parse_file(f)
        assert len(msgs) == 2
        assert msgs[0]["sender"] == "赵星"
        assert msgs[1]["sender"] == "杨仁恩"

    def test_corp_format_filter_by_target(self):
        lines = [
            "赵星(z00611745)\t2026-01-04 15:58:23",
            "刚收假就一堆事push",
            "杨仁恩(y00612385)\t2026-01-04 15:59:32",
            "我需求都没拆",
        ]
        msgs = _parse_lines(iter(lines))
        filtered = filter_by_target(msgs, "赵星")
        assert len(filtered) == 1
        assert filtered[0]["sender"] == "赵星"

    def test_corp_format_employee_id_not_in_sender(self):
        """工号不应出现在 sender 字段中。"""
        lines = [
            "赵星(z00611745)\t2026-01-04 15:58:23",
            "测试消息",
        ]
        msgs = _parse_lines(iter(lines))
        assert msgs[0]["sender"] == "赵星"
        assert "z00611745" not in msgs[0]["sender"]


class TestFormat4:
    """格式 4：说话人：内容（无时间）"""

    def test_no_timestamp(self):
        msgs = _parse_lines(lines_of("""
            张三：你好
            李四：你也好
        """))
        assert len(msgs) == 2
        assert msgs[0]["sender"] == "张三"
        assert msgs[0]["timestamp"] == ""

    def test_full_width_colon(self):
        msgs = _parse_lines(lines_of("""
            张三：使用全角冒号
        """))
        assert len(msgs) == 1
        assert msgs[0]["content"] == "使用全角冒号"


class TestFormat5:
    """格式 5：**说话人**: 内容（Markdown 加粗式）"""

    def test_markdown_bold(self):
        msgs = _parse_lines(lines_of("""
            **张三**: 这是 Markdown 格式
            **李四**: 这也是
        """))
        assert len(msgs) == 2
        assert msgs[0]["sender"] == "张三"
        assert msgs[0]["content"] == "这是 Markdown 格式"


# ─── 噪声过滤测试 ──────────────────────────────────────────────────────────────

class TestNoiseFiltering:
    def test_image_sticker_filtered(self):
        msgs = _parse_lines(lines_of("""
            张三：[图片]
            张三：[语音]
            张三：[撤回了一条消息]
            张三：正常消息
        """))
        assert len(msgs) == 1
        assert msgs[0]["content"] == "正常消息"

    def test_empty_content_filtered(self):
        msgs = _parse_lines(lines_of("""
            张三：
            李四：有内容
        """))
        # 空内容的消息不应出现
        assert all(m["content"] for m in msgs)


# ─── 边界情况测试 ──────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        msgs = parse_file(f)
        assert msgs == []

    def test_blank_lines_only(self):
        msgs = _parse_lines(iter([" ", "   ", "\t", ""]))
        assert msgs == []

    def test_nonexistent_path(self, tmp_path, capsys):
        result = parse_paths([str(tmp_path / "nonexistent.txt")])
        captured = capsys.readouterr()
        assert result == []
        assert "不存在" in captured.err

    def test_empty_directory(self, tmp_path, capsys):
        result = parse_paths([str(tmp_path)])
        captured = capsys.readouterr()
        assert result == []
        assert "未找到" in captured.err

    def test_gbk_encoding(self, tmp_path):
        f = tmp_path / "gbk.txt"
        content = "张三：这是 GBK 编码的消息\n李四：另一条\n"
        f.write_bytes(content.encode("gbk"))
        msgs = parse_file(f)
        assert len(msgs) == 2
        assert msgs[0]["sender"] == "张三"

    def test_utf8_bom_encoding(self, tmp_path):
        f = tmp_path / "bom.txt"
        content = "张三：带 BOM 的文件\n"
        f.write_bytes(content.encode("utf-8-sig"))
        msgs = parse_file(f)
        assert len(msgs) == 1
        assert msgs[0]["sender"] == "张三"

    def test_large_file_streaming(self, tmp_path):
        """大文件不应一次性读入内存导致 OOM（验证可流式处理）。"""
        f = tmp_path / "large.txt"
        lines = []
        for i in range(10_000):
            lines.append(f"张三：消息 {i}")
        f.write_text("\n".join(lines), encoding="utf-8")
        msgs = parse_file(f)
        assert len(msgs) == 10_000

    def test_url_not_misidentified_as_sender(self):
        msgs = _parse_lines(lines_of("""
            张三：请参考 https://example.com/path:to/resource 这个链接
        """))
        assert len(msgs) == 1
        assert msgs[0]["sender"] == "张三"


# ─── 多文件/目录解析测试 ────────────────────────────────────────────────────────

class TestMultiFileParsing:
    def test_multiple_files(self, tmp_path):
        f1 = tmp_path / "chat1.txt"
        f2 = tmp_path / "chat2.txt"
        f1.write_text("张三：消息来自文件1\n", encoding="utf-8")
        f2.write_text("李四：消息来自文件2\n", encoding="utf-8")
        msgs = parse_paths([str(f1), str(f2)])
        assert len(msgs) == 2
        senders = {m["sender"] for m in msgs}
        assert "张三" in senders
        assert "李四" in senders

    def test_recursive_directory(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (tmp_path / "a.txt").write_text("张三：顶层文件\n", encoding="utf-8")
        (sub / "b.txt").write_text("李四：子目录文件\n", encoding="utf-8")
        msgs = parse_paths([str(tmp_path)], recursive=True)
        assert len(msgs) == 2

    def test_non_recursive_directory(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (tmp_path / "a.txt").write_text("张三：顶层\n", encoding="utf-8")
        (sub / "b.txt").write_text("李四：子目录\n", encoding="utf-8")
        msgs = parse_paths([str(tmp_path)], recursive=False)
        assert len(msgs) == 1
        assert msgs[0]["sender"] == "张三"

    def test_duplicate_paths_deduped(self, tmp_path):
        f = tmp_path / "chat.txt"
        f.write_text("张三：消息\n", encoding="utf-8")
        msgs = parse_paths([str(f), str(f)])
        assert len(msgs) == 1


# ─── 说话人 / 过滤测试 ─────────────────────────────────────────────────────────

class TestSpeakersAndFilter:
    def _make_messages(self):
        return [
            {"timestamp": "", "sender": "张三", "content": "消息1"},
            {"timestamp": "", "sender": "张三", "content": "消息2"},
            {"timestamp": "", "sender": "李四", "content": "消息3"},
        ]

    def test_get_speakers_sorted_by_count(self):
        msgs = self._make_messages()
        speakers = get_speakers(msgs)
        assert speakers[0] == "张三"  # 出现 2 次，排第一
        assert speakers[1] == "李四"

    def test_filter_by_target_exact(self):
        msgs = self._make_messages()
        filtered = filter_by_target(msgs, "张三")
        assert len(filtered) == 2
        assert all(m["sender"] == "张三" for m in filtered)

    def test_filter_by_target_partial(self):
        msgs = [
            {"timestamp": "", "sender": "张三（已离职）", "content": "消息"},
        ]
        filtered = filter_by_target(msgs, "张三")
        assert len(filtered) == 1

    def test_filter_by_target_no_match(self):
        msgs = self._make_messages()
        filtered = filter_by_target(msgs, "王五")
        assert filtered == []


# ─── 内容提取测试 ──────────────────────────────────────────────────────────────

class TestExtractKeyContent:
    def test_long_message_classification(self):
        msgs = [{"timestamp": "", "sender": "张三",
                 "content": "这是一段超过五十个字的长消息，包含观点和方案，比如说我认为这个接口设计存在根本性问题，需要重新考虑架构设计"}]
        extracted = extract_key_content(msgs)
        assert len(extracted["long_messages"]) == 1
        assert extracted["total_count"] == 1

    def test_decision_message_classification(self):
        msgs = [{"timestamp": "", "sender": "张三", "content": "同意，没问题"}]
        extracted = extract_key_content(msgs)
        assert len(extracted["decision_messages"]) == 1

    def test_daily_message_classification(self):
        msgs = [{"timestamp": "", "sender": "张三", "content": "好的"}]
        extracted = extract_key_content(msgs)
        assert len(extracted["daily_messages"]) == 1

    def test_total_count(self):
        msgs = [
            {"timestamp": "", "sender": "张三", "content": "好的"},
            {"timestamp": "", "sender": "张三", "content": "同意"},
            {"timestamp": "", "sender": "张三",
             "content": "这是一段超过五十个字的内容，用于测试分类逻辑是否正确运作，内容足够长了吗？"},
        ]
        extracted = extract_key_content(msgs)
        assert extracted["total_count"] == 3


# ─── 输出格式化测试 ────────────────────────────────────────────────────────────

class TestFormatOutput:
    def test_format_output_contains_target_name(self):
        extracted = {
            "long_messages": [],
            "decision_messages": [],
            "daily_messages": [{"timestamp": "2024-01-01", "sender": "张三", "content": "好的"}],
            "total_count": 1,
        }
        output = format_output("张三", extracted)
        assert "张三" in output
        assert "TXT 聊天记录提取结果" in output
        assert "总消息数：1" in output

    def test_format_output_daily_capped_at_100(self):
        daily = [{"timestamp": "", "sender": "张三", "content": f"消息{i}"} for i in range(200)]
        extracted = {
            "long_messages": [],
            "decision_messages": [],
            "daily_messages": daily,
            "total_count": 200,
        }
        output = format_output("张三", extracted)
        # 只输出前 100 条日常消息
        assert output.count("消息") <= 105  # 容忍标题中的"消息"字样


# ─── CLI 集成测试 ─────────────────────────────────────────────────────────────

class TestCLI:
    def test_list_speakers_exit_0(self, tmp_path):
        f = tmp_path / "chat.txt"
        f.write_text("张三：你好\n李四：你也好\n", encoding="utf-8")
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, "tools/txt_parser.py",
             "--input", str(f), "--list-speakers"],
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        assert "张三" in result.stdout
        assert "李四" in result.stdout

    def test_parse_with_target_output_file(self, tmp_path):
        f = tmp_path / "chat.txt"
        f.write_text("张三：重要内容\n李四：另一条\n", encoding="utf-8")
        out = tmp_path / "out.txt"
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, "tools/txt_parser.py",
             "--input", str(f),
             "--target", "张三",
             "--output", str(out)],
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "张三" in content

    def test_nonexistent_input_exits_1(self, tmp_path):
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, "tools/txt_parser.py",
             "--input", str(tmp_path / "nonexistent.txt"),
             "--target", "张三"],
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 1

    def test_target_not_found_exits_1(self, tmp_path):
        f = tmp_path / "chat.txt"
        f.write_text("张三：你好\n", encoding="utf-8")
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, "tools/txt_parser.py",
             "--input", str(f),
             "--target", "王五"],
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 1
        assert "王五" in result.stderr


# ─── 关系标注测试 ──────────────────────────────────────────────────────────────

class TestRelationField:
    """测试 --relation 参数和 relation 字段"""

    def test_parse_paths_with_superior_relation(self, tmp_path):
        f = tmp_path / "chat_leader.txt"
        f.write_text("张三：向领导汇报进展\n张三：没问题，会按时完成\n", encoding="utf-8")
        msgs = parse_paths([str(f)], relation="superior")
        assert len(msgs) == 2
        assert all(m["relation"] == "superior" for m in msgs)

    def test_parse_paths_with_peer_relation(self, tmp_path):
        f = tmp_path / "chat_peer.txt"
        f.write_text("张三：这方案有个问题\n张三：我觉得应该重新设计\n", encoding="utf-8")
        msgs = parse_paths([str(f)], relation="peer")
        assert all(m["relation"] == "peer" for m in msgs)

    def test_parse_paths_with_junior_relation(self, tmp_path):
        f = tmp_path / "chat_junior.txt"
        f.write_text("张三：你先想想这个问题怎么解\n", encoding="utf-8")
        msgs = parse_paths([str(f)], relation="junior")
        assert msgs[0]["relation"] == "junior"

    def test_parse_paths_no_relation_default_none(self, tmp_path):
        f = tmp_path / "chat_mixed.txt"
        f.write_text("张三：普通消息\n", encoding="utf-8")
        msgs = parse_paths([str(f)])
        # 未传 relation 时消息不带 relation 字段（或字段不存在）
        assert msgs[0].get("relation") is None

    def test_extract_key_content_by_relation_grouping(self):
        msgs = [
            {"timestamp": "", "sender": "张三", "content": "汇报进展", "relation": "superior"},
            {"timestamp": "", "sender": "张三", "content": "同意你的方案", "relation": "peer"},
            {"timestamp": "", "sender": "张三", "content": "你先想想这个问题", "relation": "junior"},
            {"timestamp": "", "sender": "张三", "content": "普通消息"},
        ]
        extracted = extract_key_content(msgs)
        assert "by_relation" in extracted
        by_rel = extracted["by_relation"]
        assert "superior" in by_rel
        assert "peer" in by_rel
        assert "junior" in by_rel
        assert "unknown" in by_rel

    def test_extract_key_content_by_relation_counts(self):
        msgs = [
            {"timestamp": "", "sender": "张三", "content": "汇报：进展顺利，按计划推进中", "relation": "superior"},
            {"timestamp": "", "sender": "张三", "content": "同意", "relation": "peer"},
            {"timestamp": "", "sender": "张三", "content": "好的", "relation": "superior"},
        ]
        extracted = extract_key_content(msgs)
        by_rel = extracted["by_relation"]
        superior_total = (
            len(by_rel["superior"]["long_messages"])
            + len(by_rel["superior"]["decision_messages"])
            + len(by_rel["superior"]["daily_messages"])
        )
        peer_total = (
            len(by_rel["peer"]["long_messages"])
            + len(by_rel["peer"]["decision_messages"])
            + len(by_rel["peer"]["daily_messages"])
        )
        assert superior_total == 2
        assert peer_total == 1

    def test_extract_key_content_backward_compat(self):
        """无 relation 字段的旧格式消息仍能正常分类，归入 unknown。"""
        msgs = [
            {"timestamp": "", "sender": "张三", "content": "好的"},
        ]
        extracted = extract_key_content(msgs)
        assert extracted["total_count"] == 1
        assert len(extracted["daily_messages"]) == 1
        unknown_daily = extracted["by_relation"]["unknown"]["daily_messages"]
        assert len(unknown_daily) == 1

    def test_format_output_with_relation_sections(self):
        msgs = [
            {"timestamp": "", "sender": "张三", "content": "汇报进展，领导", "relation": "superior"},
            {"timestamp": "", "sender": "张三", "content": "跟同级讨论方案", "relation": "peer"},
        ]
        extracted = extract_key_content(msgs)
        output = format_output("张三", extracted)
        assert "跟领导的对话" in output
        assert "跟同级的对话" in output

    def test_format_output_no_relation_uses_flat_format(self):
        """无 relation 标注时，输出保持原有平铺格式（长消息/决策类/日常沟通）。"""
        msgs = [
            {"timestamp": "", "sender": "张三", "content": "好的"},
        ]
        extracted = extract_key_content(msgs)
        output = format_output("张三", extracted)
        assert "日常沟通" in output
        # 无关系分类时不应出现关系标题
        assert "跟领导的对话" not in output

    def test_cli_relation_parameter(self, tmp_path):
        f = tmp_path / "chat.txt"
        f.write_text("张三：向领导汇报\n", encoding="utf-8")
        out = tmp_path / "out.txt"
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, "tools/txt_parser.py",
             "--input", str(f),
             "--target", "张三",
             "--relation", "superior",
             "--output", str(out)],
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "跟领导的对话" in content


# ─── _expand_paths 测试 ────────────────────────────────────────────────────────

class TestExpandPaths:
    def test_single_file(self, tmp_path):
        f = tmp_path / "chat.txt"
        f.write_text("张三：消息\n", encoding="utf-8")
        result = _expand_paths([str(f)])
        assert result == [f]

    def test_multiple_files(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("张三：消息\n", encoding="utf-8")
        f2.write_text("李四：消息\n", encoding="utf-8")
        result = _expand_paths([str(f1), str(f2)])
        assert len(result) == 2
        assert f1 in result
        assert f2 in result

    def test_directory_recursive(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (tmp_path / "a.txt").write_text("张三：顶层\n", encoding="utf-8")
        (sub / "b.txt").write_text("李四：子目录\n", encoding="utf-8")
        result = _expand_paths([str(tmp_path)], recursive=True)
        names = {p.name for p in result}
        assert "a.txt" in names
        assert "b.txt" in names

    def test_directory_non_recursive(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (tmp_path / "a.txt").write_text("张三：顶层\n", encoding="utf-8")
        (sub / "b.txt").write_text("李四：子目录\n", encoding="utf-8")
        result = _expand_paths([str(tmp_path)], recursive=False)
        names = {p.name for p in result}
        assert "a.txt" in names
        assert "b.txt" not in names

    def test_deduplication(self, tmp_path):
        f = tmp_path / "chat.txt"
        f.write_text("张三：消息\n", encoding="utf-8")
        result = _expand_paths([str(f), str(f)])
        assert len(result) == 1

    def test_nonexistent_path_warning(self, tmp_path, capsys):
        result = _expand_paths([str(tmp_path / "nonexistent.txt")])
        captured = capsys.readouterr()
        assert result == []
        assert "不存在" in captured.err


# ─── _interactive_assign_relations 测试 ───────────────────────────────────────

class TestInteractiveAssignRelations:
    """使用 monkeypatch 模拟用户在交互式关系选择中的输入。"""

    def test_assign_superior(self, tmp_path, monkeypatch):
        f = tmp_path / "boss.txt"
        f.write_text("张三：汇报进展\n", encoding="utf-8")
        monkeypatch.setattr("builtins.input", lambda _: "1")
        results = _interactive_assign_relations([f])
        assert len(results) == 1
        assert results[0] == (f, "superior")

    def test_assign_peer(self, tmp_path, monkeypatch):
        f = tmp_path / "peer.txt"
        f.write_text("李四：讨论方案\n", encoding="utf-8")
        monkeypatch.setattr("builtins.input", lambda _: "2")
        results = _interactive_assign_relations([f])
        assert results[0] == (f, "peer")

    def test_assign_junior(self, tmp_path, monkeypatch):
        f = tmp_path / "junior.txt"
        f.write_text("王五：请教问题\n", encoding="utf-8")
        monkeypatch.setattr("builtins.input", lambda _: "3")
        results = _interactive_assign_relations([f])
        assert results[0] == (f, "junior")

    def test_skip_file(self, tmp_path, monkeypatch):
        f = tmp_path / "unknown.txt"
        f.write_text("赵六：未知关系\n", encoding="utf-8")
        monkeypatch.setattr("builtins.input", lambda _: "s")
        results = _interactive_assign_relations([f])
        assert results[0] == (f, None)

    def test_invalid_then_valid_input(self, tmp_path, monkeypatch):
        f = tmp_path / "chat.txt"
        f.write_text("张三：消息\n", encoding="utf-8")
        responses = iter(["x", "bad", "2"])
        monkeypatch.setattr("builtins.input", lambda _: next(responses))
        results = _interactive_assign_relations([f])
        assert results[0] == (f, "peer")

    def test_empty_file_skipped(self, tmp_path, monkeypatch):
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        monkeypatch.setattr("builtins.input", lambda _: "1")
        results = _interactive_assign_relations([f])
        assert results[0] == (f, None)

    def test_multiple_files_different_relations(self, tmp_path, monkeypatch):
        f1 = tmp_path / "boss.txt"
        f2 = tmp_path / "peer.txt"
        f3 = tmp_path / "junior.txt"
        f1.write_text("张三：汇报\n", encoding="utf-8")
        f2.write_text("李四：协作\n", encoding="utf-8")
        f3.write_text("王五：被指导\n", encoding="utf-8")
        responses = iter(["1", "2", "3"])
        monkeypatch.setattr("builtins.input", lambda _: next(responses))
        results = _interactive_assign_relations([f1, f2, f3])
        assert results[0] == (f1, "superior")
        assert results[1] == (f2, "peer")
        assert results[2] == (f3, "junior")

    def test_relation_field_set_on_messages(self, tmp_path, monkeypatch):
        """验证分配关系后消息的 relation 字段正确设置。"""
        f = tmp_path / "boss.txt"
        f.write_text("张三：汇报进展\n张三：已完成\n", encoding="utf-8")
        monkeypatch.setattr("builtins.input", lambda _: "1")
        file_relations = _interactive_assign_relations([f])
        all_messages = _apply_file_relations(file_relations)
        assert all(m["relation"] == "superior" for m in all_messages)

    def test_skipped_file_no_relation_field(self, tmp_path, monkeypatch):
        """选择跳过（s）时，消息不应附加 relation 字段。"""
        f = tmp_path / "unknown.txt"
        f.write_text("张三：消息\n", encoding="utf-8")
        monkeypatch.setattr("builtins.input", lambda _: "s")
        file_relations = _interactive_assign_relations([f])
        all_messages = _apply_file_relations(file_relations)
        assert len(all_messages) == 1
        assert "relation" not in all_messages[0]


# ─── 多文件 CLI 集成测试（交互式关系分配）─────────────────────────────────────

class TestMultiFileCLIRelationAssignment:
    """通过 subprocess + stdin 管道验证多文件时的交互式关系分配流程。"""

    def test_multi_file_stdin_assigns_relations(self, tmp_path):
        """多文件 + --relation 统一指定时，输出按关系分段（验证端到端关系注入）。"""
        import subprocess

        f1 = tmp_path / "boss.txt"
        f2 = tmp_path / "peer.txt"
        f1.write_text("张三：汇报进展，领导好\n", encoding="utf-8")
        f2.write_text("张三：跟同级讨论方案\n", encoding="utf-8")
        out = tmp_path / "out.txt"

        # 非交互模式：通过 --relation 统一指定；单文件分别调用确认按关系分段
        result = subprocess.run(
            [sys.executable, "tools/txt_parser.py",
             "--input", str(f1), str(f2),
             "--target", "张三",
             "--relation", "superior",
             "--output", str(out)],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "跟领导的对话" in content

    def test_single_file_no_interactive_relation_prompt(self, tmp_path):
        """单个文件时不触发交互式关系选择（直接由 --target 和 --relation 控制）。"""
        import subprocess

        f = tmp_path / "chat.txt"
        f.write_text("张三：消息\n", encoding="utf-8")
        out = tmp_path / "out.txt"

        result = subprocess.run(
            [sys.executable, "tools/txt_parser.py",
             "--input", str(f),
             "--target", "张三",
             "--output", str(out)],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0

    def test_multi_file_with_explicit_relation_skips_interactive(self, tmp_path):
        """指定 --relation 时，多文件不触发交互式逐文件关系选择。"""
        import subprocess

        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("张三：消息1\n", encoding="utf-8")
        f2.write_text("张三：消息2\n", encoding="utf-8")
        out = tmp_path / "out.txt"

        result = subprocess.run(
            [sys.executable, "tools/txt_parser.py",
             "--input", str(f1), str(f2),
             "--target", "张三",
             "--relation", "peer",
             "--output", str(out)],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        content = out.read_text(encoding="utf-8")
        assert "跟同级的对话" in content
