#!/usr/bin/env python3
"""
版本管理器

负责影分身 Skill 文件的版本存档和回滚。

用法：
    python version_manager.py --action list    --slug my-shadow --base-dir ./shadows
    python version_manager.py --action backup  --slug my-shadow --base-dir ./shadows
    python version_manager.py --action rollback --slug my-shadow --version v2 --base-dir ./shadows
    python version_manager.py --action cleanup --slug my-shadow --base-dir ./shadows
"""

from __future__ import annotations

import json
import shutil
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone

MAX_VERSIONS = 10  # 最多保留的版本数


def list_versions(skill_dir: Path) -> list:
    """列出所有历史版本"""
    versions_dir = skill_dir / "versions"
    if not versions_dir.exists():
        return []

    versions = []
    for v_dir in sorted(versions_dir.iterdir()):
        if not v_dir.is_dir():
            continue

        # 从目录名解析版本号
        version_name = v_dir.name

        # 优先从存档的 meta.json 读取存档时间
        archived_at = None
        meta_file = v_dir / "meta.json"
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                ts = meta.get("updated_at") or meta.get("created_at")
                if ts:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    archived_at = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass

        # fallback：用目录修改时间近似
        if not archived_at:
            mtime = v_dir.stat().st_mtime
            archived_at = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

        # 统计文件
        files = [f.name for f in v_dir.iterdir() if f.is_file()]

        versions.append({
            "version": version_name,
            "archived_at": archived_at,
            "files": files,
            "path": str(v_dir),
        })

    return versions


def backup(skill_dir: Path) -> str:
    """将当前版本存档到 versions/ 目录，返回被存档的版本号"""
    meta_path = skill_dir / "meta.json"
    if not meta_path.exists():
        print("错误：找不到 meta.json，无法确定当前版本", file=sys.stderr)
        return ""

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    current_version = meta.get("version", "v1")

    version_dir = skill_dir / "versions" / current_version
    version_dir.mkdir(parents=True, exist_ok=True)

    archived_files = []
    for fname in ("SKILL.md", "work.md", "persona.md", "meta.json"):
        src = skill_dir / fname
        if src.exists():
            shutil.copy2(src, version_dir / fname)
            archived_files.append(fname)

    cleanup_old_versions(skill_dir)

    print(f"已存档版本 {current_version}，文件：{', '.join(archived_files)}")
    return current_version


def rollback(skill_dir: Path, target_version: str) -> bool:
    """回滚到指定版本"""
    version_dir = skill_dir / "versions" / target_version

    if not version_dir.exists():
        print(f"错误：版本 {target_version} 不存在", file=sys.stderr)
        return False

    # 先存档当前版本（包含 meta.json）
    meta_path = skill_dir / "meta.json"
    current_version = "unknown"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        current_version = meta.get("version", "v?")
        backup_dir = skill_dir / "versions" / f"{current_version}_before_rollback"
        backup_dir.mkdir(parents=True, exist_ok=True)
        for fname in ("SKILL.md", "work.md", "persona.md", "meta.json"):
            src = skill_dir / fname
            if src.exists():
                shutil.copy2(src, backup_dir / fname)

    # 从目标版本恢复文件（SKILL.md、work.md、persona.md、meta.json）
    restored_files = []
    for fname in ("SKILL.md", "work.md", "persona.md", "meta.json"):
        src = version_dir / fname
        if src.exists():
            shutil.copy2(src, skill_dir / fname)
            restored_files.append(fname)

    # 更新 meta：标记回滚状态（无论 meta.json 是否从版本目录恢复）
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["version"] = target_version + "_restored"
        meta["updated_at"] = datetime.now(timezone.utc).isoformat()
        meta["rollback_from"] = current_version
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"已回滚到 {target_version}，恢复文件：{', '.join(restored_files)}")
    return True


def cleanup_old_versions(skill_dir: Path, max_versions: int = MAX_VERSIONS):
    """清理超出限制的旧版本"""
    versions_dir = skill_dir / "versions"
    if not versions_dir.exists():
        return

    # 按版本号排序，保留最新的 max_versions 个
    version_dirs = sorted(
        [d for d in versions_dir.iterdir() if d.is_dir()],
        key=lambda d: d.stat().st_mtime,
    )

    to_delete = version_dirs[:-max_versions] if len(version_dirs) > max_versions else []

    for old_dir in to_delete:
        shutil.rmtree(old_dir)
        print(f"已清理旧版本：{old_dir.name}")


def main():
    parser = argparse.ArgumentParser(description="Skill 版本管理器")
    parser.add_argument("--action", required=True, choices=["list", "backup", "rollback", "cleanup"])
    parser.add_argument("--slug", required=True, help="影分身 slug")
    parser.add_argument("--version", help="目标版本号（rollback 时使用）")
    parser.add_argument(
        "--base-dir",
        default="./shadows",
        help="影分身 Skill 根目录（默认：./shadows）",
    )

    args = parser.parse_args()
    base_dir = Path(args.base_dir).expanduser()
    skill_dir = base_dir / args.slug

    if not skill_dir.exists():
        print(f"错误：找不到 Skill 目录 {skill_dir}", file=sys.stderr)
        sys.exit(1)

    if args.action == "list":
        versions = list_versions(skill_dir)
        if not versions:
            print(f"{args.slug} 暂无历史版本")
        else:
            print(f"{args.slug} 的历史版本：\n")
            for v in versions:
                print(f"  {v['version']}  存档时间: {v['archived_at']}  文件: {', '.join(v['files'])}")

    elif args.action == "backup":
        result = backup(skill_dir)
        if not result:
            sys.exit(1)

    elif args.action == "rollback":
        if not args.version:
            print("错误：rollback 操作需要 --version", file=sys.stderr)
            sys.exit(1)
        success = rollback(skill_dir, args.version)
        if not success:
            sys.exit(1)

    elif args.action == "cleanup":
        cleanup_old_versions(skill_dir)
        print("清理完成")


if __name__ == "__main__":
    main()
