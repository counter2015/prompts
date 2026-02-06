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

"""批量校验仓库内 skills 的有效性。"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table
import typer

console = Console()


class Finding(BaseModel):
    """表示一次校验发现。"""

    skill: str = Field(description="技能目录名")
    level: str = Field(description="级别：error 或 warning")
    message: str = Field(description="发现描述")


def repo_root_from_here() -> Path:
    """从脚本位置推断仓库根目录。"""
    return Path(__file__).resolve().parent.parent


def parse_front_matter(skill_md: Path) -> tuple[dict[str, str], str]:
    """解析 SKILL.md 的 YAML front matter 与正文。"""
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text

    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text

    raw = text[4:end].splitlines()
    body = text[end + 5 :]
    data: dict[str, str] = {}
    for line in raw:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data, body


def path_candidates_from_markdown(body: str) -> set[str]:
    """提取 Markdown 文本中的相对路径候选。"""
    candidates: set[str] = set()

    for ref in re.findall(r"\[[^\]]+\]\(([^)]+)\)", body):
        candidates.add(ref.strip())

    for ref in re.findall(r"`([^`\n]+)`", body):
        candidates.add(ref.strip())

    cleaned: set[str] = set()
    path_pattern = re.compile(r"^(?:\./)?[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)+$")
    for candidate in candidates:
        if not candidate:
            continue
        token = candidate.strip().split()[0]
        lower = token.lower()
        if lower.startswith(("http://", "https://")):
            continue
        if token.startswith(("~/", "--")):
            continue
        if "<" in token or ">" in token:
            continue
        normalized = token.replace("\\", "/")
        if not path_pattern.match(normalized):
            continue
        cleaned.add(normalized)
    return cleaned


def resolve_reference(candidate: str, skill_dir: Path, repo_root: Path) -> Path | None:
    """将候选路径解析为文件系统路径。"""
    normalized = candidate.strip()
    if normalized.startswith("./"):
        normalized = normalized[2:]

    if normalized.startswith("skills/"):
        return repo_root / normalized
    return skill_dir / normalized


def validate_skill_dir(skill_dir: Path, repo_root: Path) -> list[Finding]:
    """对单个技能目录做静态校验。"""
    findings: list[Finding] = []
    skill_name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        findings.append(
            Finding(skill=skill_name, level="error", message="缺少 SKILL.md")
        )
        return findings

    front_matter, body = parse_front_matter(skill_md)
    if not front_matter:
        findings.append(
            Finding(
                skill=skill_name, level="error", message="缺少或无法解析 front matter"
            )
        )
    else:
        name = front_matter.get("name", "")
        desc = front_matter.get("description", "")
        if not name:
            findings.append(
                Finding(
                    skill=skill_name, level="error", message="front matter 缺少 name"
                )
            )
        if not desc:
            findings.append(
                Finding(
                    skill=skill_name,
                    level="error",
                    message="front matter 缺少 description",
                )
            )
        if name and name != skill_name:
            findings.append(
                Finding(
                    skill=skill_name,
                    level="error",
                    message=f"name 与目录名不一致：{name} != {skill_name}",
                )
            )

    for candidate in sorted(path_candidates_from_markdown(body)):
        ref_path = resolve_reference(candidate, skill_dir, repo_root)
        if ref_path is None:
            continue
        if not ref_path.exists():
            findings.append(
                Finding(
                    skill=skill_name,
                    level="error",
                    message=f"引用路径不存在：{candidate}",
                )
            )

    return findings


def compile_python_scripts(skill_dir: Path) -> list[Finding]:
    """编译技能脚本中的 Python 文件，验证语法有效。"""
    findings: list[Finding] = []
    skill_name = skill_dir.name
    py_files = (
        sorted((skill_dir / "scripts").rglob("*.py"))
        if (skill_dir / "scripts").exists()
        else []
    )
    for py_file in py_files:
        rel = py_file.relative_to(skill_dir).as_posix()
        try:
            result = subprocess.run(
                ["uv", "run", "python", "-m", "py_compile", str(py_file)],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            findings.append(
                Finding(
                    skill=skill_name,
                    level="error",
                    message=f"无法执行 uv 编译 {rel}：{exc}",
                )
            )
            continue
        if result.returncode != 0:
            stderr = result.stderr.strip() or "无错误输出"
            findings.append(
                Finding(
                    skill=skill_name,
                    level="error",
                    message=f"脚本语法检查失败 {rel}：{stderr}",
                )
            )
    return findings


def collect_skill_dirs(skills_root: Path) -> list[Path]:
    """收集一级技能目录。"""
    return sorted(
        [p for p in skills_root.iterdir() if p.is_dir() and not p.name.startswith(".")],
        key=lambda p: p.name,
    )


def render_findings(findings: Iterable[Finding]) -> None:
    """渲染校验发现结果。"""
    table = Table(show_header=True, header_style="bold")
    table.add_column("Skill")
    table.add_column("Level")
    table.add_column("Message")

    for item in findings:
        level_style = "red" if item.level == "error" else "yellow"
        table.add_row(
            item.skill, f"[{level_style}]{item.level}[/{level_style}]", item.message
        )

    console.print(table)


def main(
    skills_path: Path = typer.Option(
        Path("skills"), "--skills-path", help="skills 目录路径"
    ),
    compile_scripts: bool = typer.Option(
        True,
        "--compile-scripts/--no-compile-scripts",
        help="是否编译检查 skills 下的 Python 脚本",
    ),
) -> None:
    """校验每个 skill 的元数据、引用完整性与脚本语法。"""
    repo_root = repo_root_from_here()
    skills_root = (
        (repo_root / skills_path).resolve()
        if not skills_path.is_absolute()
        else skills_path
    )
    if not skills_root.exists():
        console.print(f"[red]skills 目录不存在：{skills_root}[/red]")
        raise typer.Exit(code=1)

    all_findings: list[Finding] = []
    for skill_dir in collect_skill_dirs(skills_root):
        all_findings.extend(validate_skill_dir(skill_dir, repo_root))
        if compile_scripts:
            all_findings.extend(compile_python_scripts(skill_dir))

    if all_findings:
        render_findings(all_findings)
        errors = sum(1 for f in all_findings if f.level == "error")
        console.print(f"[red]校验失败：{errors} 个错误[/red]")
        raise typer.Exit(code=1)

    console.print("[green]校验通过：所有 skills 均有效[/green]")


if __name__ == "__main__":
    typer.run(main)
