#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pydantic",
#     "rich",
#     "typer",
# ]
# ///


"""同步仓库 skills 到 Codex 技能目录。"""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError, field_validator
from rich.console import Console
from rich.table import Table
import typer

console = Console()


class SyncSpec(BaseModel):
    """同步参数模型。"""

    source: Path = Field(description="源 skills 目录")
    dest: Path = Field(description="目标 skills 目录")

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: Path) -> Path:
        """校验源目录存在且是目录。"""
        if not value.exists():
            raise ValueError(f"源目录不存在: {value}")
        if not value.is_dir():
            raise ValueError(f"源路径不是目录: {value}")
        return value

    @field_validator("dest")
    @classmethod
    def normalize_dest(cls, value: Path) -> Path:
        """标准化目标目录路径。"""
        return value


def file_hash(path: Path) -> str:
    """计算文件 SHA-256 哈希。"""
    hasher = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def repo_root_from_script() -> Path:
    """从脚本位置推断仓库根目录。"""
    return Path(__file__).resolve().parent.parent


def codex_home_default() -> Path:
    """返回默认 Codex 目录。"""
    env_home = os.getenv("CODEX_HOME")
    if env_home:
        return Path(env_home).expanduser()
    return Path.home() / ".codex"


def list_skill_dirs(skills_root: Path) -> list[Path]:
    """收集技能目录列表（排除隐藏目录）。"""
    return sorted(
        [
            path
            for path in skills_root.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        ],
        key=lambda path: path.name,
    )


def sync_one_skill(
    source_skill: Path, dest_root: Path, dry_run: bool
) -> tuple[int, int]:
    """同步单个技能目录并返回新增/更新文件计数。"""
    added = 0
    updated = 0
    target_skill = dest_root / source_skill.name

    for src_file in sorted(source_skill.rglob("*")):
        if src_file.is_dir():
            continue
        relative = src_file.relative_to(source_skill)
        dst_file = target_skill / relative
        if not dst_file.exists():
            added += 1
            if not dry_run:
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst_file)
            continue
        if file_hash(src_file) != file_hash(dst_file):
            updated += 1
            if not dry_run:
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst_file)
    return added, updated


def remove_extra_skills(source_root: Path, dest_root: Path, dry_run: bool) -> list[str]:
    """删除目标目录中不存在于源目录的技能目录。"""
    source_names = {path.name for path in list_skill_dirs(source_root)}
    removed: list[str] = []
    for dst_dir in list_skill_dirs(dest_root):
        if dst_dir.name == ".system":
            continue
        if dst_dir.name not in source_names:
            removed.append(dst_dir.name)
            if not dry_run:
                shutil.rmtree(dst_dir)
    return removed


def verify_sync(source_root: Path, dest_root: Path) -> list[str]:
    """校验同步后文件哈希是否一致。"""
    mismatches: list[str] = []
    for source_skill in list_skill_dirs(source_root):
        target_skill = dest_root / source_skill.name
        if not target_skill.exists():
            mismatches.append(f"{source_skill.name}: 目标技能目录不存在")
            continue
        for src_file in sorted(source_skill.rglob("*")):
            if src_file.is_dir():
                continue
            rel = src_file.relative_to(source_skill)
            dst_file = target_skill / rel
            if not dst_file.exists():
                mismatches.append(
                    f"{source_skill.name}/{rel.as_posix()}: 目标文件不存在"
                )
                continue
            if file_hash(src_file) != file_hash(dst_file):
                mismatches.append(f"{source_skill.name}/{rel.as_posix()}: 哈希不一致")
    return mismatches


def main(
    source: Path = typer.Option(
        Path("skills"), "--source", "-s", help="源 skills 目录"
    ),
    dest: Path | None = typer.Option(
        None, "--dest", "-d", help="目标 skills 目录，默认 $CODEX_HOME/skills"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅显示计划，不写入"),
    remove_stale: bool = typer.Option(
        False, "--remove-stale", help="删除目标目录中源目录不存在的技能"
    ),
) -> None:
    """同步仓库 skills 到 Codex 技能目录并做一致性校验。"""
    repo_root = repo_root_from_script()
    resolved_source = (
        (repo_root / source).resolve() if not source.is_absolute() else source.resolve()
    )
    resolved_dest = (
        (codex_home_default() / "skills").resolve()
        if dest is None
        else (repo_root / dest).resolve()
        if not dest.is_absolute()
        else dest.resolve()
    )
    try:
        spec = SyncSpec(source=resolved_source, dest=resolved_dest)
    except ValidationError as exc:
        console.print("[red]参数校验失败[/red]")
        for error in exc.errors():
            console.print(f"• {error['msg']}")
        raise typer.Exit(code=1)

    if not dry_run:
        spec.dest.mkdir(parents=True, exist_ok=True)

    table = Table(show_header=True, header_style="bold")
    table.add_column("Skill")
    table.add_column("Added", justify="right")
    table.add_column("Updated", justify="right")

    total_added = 0
    total_updated = 0
    for source_skill in list_skill_dirs(spec.source):
        added, updated = sync_one_skill(source_skill, spec.dest, dry_run=dry_run)
        total_added += added
        total_updated += updated
        table.add_row(source_skill.name, str(added), str(updated))

    console.print(table)

    removed = (
        remove_extra_skills(spec.source, spec.dest, dry_run=dry_run)
        if remove_stale
        else []
    )
    if removed:
        console.print(f"[yellow]移除过期技能: {', '.join(sorted(removed))}[/yellow]")

    if dry_run:
        console.print("[cyan]dry-run 完成，未写入文件[/cyan]")
        return

    mismatches = verify_sync(spec.source, spec.dest)
    if mismatches:
        console.print("[red]同步后校验失败：存在不一致文件[/red]")
        for item in mismatches:
            console.print(f"• {item}")
        raise typer.Exit(code=1)

    console.print(
        f"[green]同步完成：新增 {total_added}，更新 {total_updated}，目标目录 {spec.dest}[/green]"
    )


if __name__ == "__main__":
    typer.run(main)
