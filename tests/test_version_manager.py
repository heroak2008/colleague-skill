"""
tests/test_version_manager.py

版本管理器单元测试
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.version_manager import backup, list_versions, rollback, cleanup_old_versions


# ─── 辅助函数 ──────────────────────────────────────────────────────────────────

def make_skill_dir(tmp_path: Path, version: str = "v1", extra_meta: dict | None = None) -> Path:
    """在 tmp_path 下创建一个最小化的 Skill 目录结构。"""
    skill_dir = tmp_path / "my-shadow"
    skill_dir.mkdir()
    (skill_dir / "versions").mkdir()

    meta = {
        "name": "测试影分身",
        "slug": "my-shadow",
        "version": version,
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
        "corrections_count": 0,
    }
    if extra_meta:
        meta.update(extra_meta)

    (skill_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    (skill_dir / "work.md").write_text("# Work v1", encoding="utf-8")
    (skill_dir / "persona.md").write_text("# Persona v1", encoding="utf-8")
    (skill_dir / "SKILL.md").write_text("# SKILL v1", encoding="utf-8")
    return skill_dir


# ─── backup 测试 ──────────────────────────────────────────────────────────────

class TestBackup:
    def test_backup_creates_version_dir(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path)
        result = backup(skill_dir)
        assert result == "v1"
        assert (skill_dir / "versions" / "v1").is_dir()

    def test_backup_archives_all_files(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path)
        backup(skill_dir)
        v_dir = skill_dir / "versions" / "v1"
        for fname in ("SKILL.md", "work.md", "persona.md", "meta.json"):
            assert (v_dir / fname).exists(), f"{fname} should be archived"

    def test_backup_returns_empty_string_without_meta(self, tmp_path):
        skill_dir = tmp_path / "no-meta"
        skill_dir.mkdir()
        (skill_dir / "versions").mkdir()
        result = backup(skill_dir)
        assert result == ""

    def test_backup_content_matches_original(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path)
        backup(skill_dir)
        archived_work = (skill_dir / "versions" / "v1" / "work.md").read_text(encoding="utf-8")
        assert archived_work == "# Work v1"

    def test_backup_idempotent_overwrites(self, tmp_path):
        """再次 backup 同一版本应覆盖旧存档。"""
        skill_dir = make_skill_dir(tmp_path)
        backup(skill_dir)
        (skill_dir / "work.md").write_text("# Work v1 updated", encoding="utf-8")
        backup(skill_dir)
        archived = (skill_dir / "versions" / "v1" / "work.md").read_text(encoding="utf-8")
        assert archived == "# Work v1 updated"


# ─── list_versions 测试 ───────────────────────────────────────────────────────

class TestListVersions:
    def test_empty_when_no_versions(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path)
        assert list_versions(skill_dir) == []

    def test_returns_version_after_backup(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path)
        backup(skill_dir)
        versions = list_versions(skill_dir)
        assert len(versions) == 1
        assert versions[0]["version"] == "v1"

    def test_archived_at_from_meta_json(self, tmp_path):
        """archived_at 应优先读取存档 meta.json 中的 updated_at。"""
        skill_dir = make_skill_dir(tmp_path)
        backup(skill_dir)
        versions = list_versions(skill_dir)
        assert versions[0]["archived_at"] == "2024-01-01 00:00"

    def test_files_list_contains_meta(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path)
        backup(skill_dir)
        versions = list_versions(skill_dir)
        assert "meta.json" in versions[0]["files"]

    def test_multiple_versions_sorted(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, version="v1")
        backup(skill_dir)

        # 模拟升级到 v2 并存档
        meta = json.loads((skill_dir / "meta.json").read_text(encoding="utf-8"))
        meta["version"] = "v2"
        meta["updated_at"] = "2024-06-01T00:00:00+00:00"
        (skill_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        (skill_dir / "work.md").write_text("# Work v2", encoding="utf-8")
        backup(skill_dir)

        versions = list_versions(skill_dir)
        version_names = [v["version"] for v in versions]
        assert "v1" in version_names
        assert "v2" in version_names


# ─── rollback 测试 ────────────────────────────────────────────────────────────

class TestRollback:
    def _setup_two_versions(self, tmp_path) -> Path:
        """创建一个有 v1 存档、当前为 v2 的 skill_dir。"""
        skill_dir = make_skill_dir(tmp_path, version="v1")
        backup(skill_dir)

        meta = json.loads((skill_dir / "meta.json").read_text(encoding="utf-8"))
        meta["version"] = "v2"
        meta["updated_at"] = "2024-06-01T00:00:00+00:00"
        (skill_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        (skill_dir / "work.md").write_text("# Work v2", encoding="utf-8")
        (skill_dir / "persona.md").write_text("# Persona v2", encoding="utf-8")
        (skill_dir / "SKILL.md").write_text("# SKILL v2", encoding="utf-8")
        return skill_dir

    def test_rollback_restores_work_content(self, tmp_path):
        skill_dir = self._setup_two_versions(tmp_path)
        rollback(skill_dir, "v1")
        work = (skill_dir / "work.md").read_text(encoding="utf-8")
        assert work == "# Work v1"

    def test_rollback_updates_meta_version(self, tmp_path):
        skill_dir = self._setup_two_versions(tmp_path)
        rollback(skill_dir, "v1")
        meta = json.loads((skill_dir / "meta.json").read_text(encoding="utf-8"))
        assert meta["version"] == "v1_restored"

    def test_rollback_sets_rollback_from(self, tmp_path):
        skill_dir = self._setup_two_versions(tmp_path)
        rollback(skill_dir, "v1")
        meta = json.loads((skill_dir / "meta.json").read_text(encoding="utf-8"))
        assert meta["rollback_from"] == "v2"

    def test_rollback_creates_before_rollback_backup(self, tmp_path):
        skill_dir = self._setup_two_versions(tmp_path)
        rollback(skill_dir, "v1")
        backup_dir = skill_dir / "versions" / "v2_before_rollback"
        assert backup_dir.is_dir()
        assert (backup_dir / "work.md").read_text(encoding="utf-8") == "# Work v2"

    def test_rollback_before_rollback_includes_meta(self, tmp_path):
        skill_dir = self._setup_two_versions(tmp_path)
        rollback(skill_dir, "v1")
        backup_dir = skill_dir / "versions" / "v2_before_rollback"
        assert (backup_dir / "meta.json").exists()

    def test_rollback_nonexistent_version_returns_false(self, tmp_path):
        skill_dir = self._setup_two_versions(tmp_path)
        result = rollback(skill_dir, "v99")
        assert result is False

    def test_rollback_returns_true_on_success(self, tmp_path):
        skill_dir = self._setup_two_versions(tmp_path)
        result = rollback(skill_dir, "v1")
        assert result is True


# ─── cleanup_old_versions 测试 ────────────────────────────────────────────────

class TestCleanupOldVersions:
    def test_cleanup_removes_oldest_when_over_limit(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path)
        versions_dir = skill_dir / "versions"
        # 创建 12 个版本目录（超过 MAX_VERSIONS=10）
        for i in range(1, 13):
            d = versions_dir / f"v{i}"
            d.mkdir()
            (d / "work.md").write_text(f"v{i}", encoding="utf-8")

        cleanup_old_versions(skill_dir, max_versions=10)
        remaining = sorted(d.name for d in versions_dir.iterdir() if d.is_dir())
        assert len(remaining) == 10

    def test_cleanup_no_op_when_under_limit(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path)
        versions_dir = skill_dir / "versions"
        for i in range(1, 4):
            (versions_dir / f"v{i}").mkdir()
        cleanup_old_versions(skill_dir, max_versions=10)
        remaining = list(versions_dir.iterdir())
        assert len(remaining) == 3
