#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "typer",
# ]
# ///

"""生成 skill 目录与 SKILL.md 骨架。"""

from __future__ import annotations

import re
from pathlib import Path

import typer

app = typer.Typer(add_completion=False, no_args_is_help=True)


class SkillScaffold:
    """封装 skill 脚手架生成逻辑。"""

    def __init__(self, repo_root: Path) -> None:
        """初始化仓库根目录与 skills 目录。"""
        self.repo_root = repo_root
        self.skills_root = repo_root / "skills"

    def create(
        self,
        name: str,
        description: str,
        resources: list[str],
    ) -> list[Path]:
        """创建 skill 目录、SKILL.md 与可选资源目录。"""
        self._validate_name(name)

        skill_dir = self.skills_root / name
        if skill_dir.exists():
            raise ValueError(f"skill 已存在: {skill_dir}")

        created: list[Path] = []
        skill_dir.mkdir(parents=True, exist_ok=False)
        created.append(skill_dir)

        for resource in resources:
            subdir = skill_dir / resource
            subdir.mkdir(parents=True, exist_ok=True)
            created.append(subdir)

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(self._skill_md_template(name, description), encoding="utf-8")
        created.append(skill_md)

        return created

    @staticmethod
    def _validate_name(name: str) -> None:
        """校验 skill 名称符合规范。"""
        if len(name) > 64:
            raise ValueError("skill 名称长度不能超过 64")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
            raise ValueError("skill 名称仅允许小写字母、数字和连字符，且需以字母或数字开头")

    @staticmethod
    def _skill_md_template(name: str, description: str) -> str:
        """生成 SKILL.md 模板内容。"""
        return f"""---
name: {name}
description: {description}
---

# {name}

## Workflow

1. 明确输入、约束与目标输出。
2. 只保留与任务直接相关的流程指引。
3. 细节较多时拆分到 `references/`。
4. 需要重复执行或高确定性步骤时放到 `scripts/`。

## References

- 按需添加：`references/*.md`

## Scripts

- 按需添加：`scripts/*.py`
"""


def parse_resources(raw: str | None) -> list[str]:
    """解析资源目录参数。"""
    if not raw:
        return []

    allowed = {"scripts", "references", "assets"}
    values = [item.strip() for item in raw.split(",") if item.strip()]
    invalid = [item for item in values if item not in allowed]
    if invalid:
        raise ValueError(f"不支持的 resources: {', '.join(invalid)}")
    # 保持顺序并去重
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped


def repo_root_from_script() -> Path:
    """基于脚本位置推断仓库根目录。"""
    return Path(__file__).resolve().parents[3]


@app.command(help="生成一个新的 skill 脚手架。")
def main(
    name: str = typer.Option(..., "--name", help="skill 名称（小写+连字符）"),
    description: str = typer.Option(..., "--description", help="skill 触发描述"),
    resources: str | None = typer.Option(
        None,
        "--resources",
        help="可选资源目录，逗号分隔：scripts,references,assets",
    ),
) -> None:
    """命令行入口。"""
    try:
        parsed_resources = parse_resources(resources)
        scaffold = SkillScaffold(repo_root=repo_root_from_script())
        created = scaffold.create(
            name=name,
            description=description,
            resources=parsed_resources,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo("created:")
    for path in created:
        typer.echo(f"- {path}")


if __name__ == "__main__":
    app()
