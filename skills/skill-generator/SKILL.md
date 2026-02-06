---
name: skill-generator
description: 生成或更新 Codex skill（目录、SKILL.md、可选 scripts/references/assets 脚手架）并对齐仓库规范；当用户要求新建 skill、重构 skill 结构、补齐 front matter、或快速初始化可复用 skill 模板时使用。
---

# Skill Generator

用于在本仓库中稳定生成高质量 skill，并尽量减少后续返工。

## 快速使用

在当前 `SKILL.md` 所在目录执行：

```bash
./scripts/create_skill.py --name my-skill --description "一句话描述触发场景与能力"
```

说明：必须直接当作可执行文件执行，不要用 `uv run python` 或 `python`。

## 生成流程

1. 先确认 skill 目标、触发条件和输出边界。
2. 用脚本生成目录与 `SKILL.md` 骨架。
3. 如需变体知识，放到 `references/`；如需可复用逻辑，放到 `scripts/`；如需模板资源，放到 `assets/`。
4. 将“何时触发”写入 front matter 的 `description`，不要只写在正文。
5. 运行仓库校验脚本：
   - `../../scripts/skill_check.py`
6. 如需让当前 Codex 会话可见，执行同步：
   - `../../scripts/sync_skills.py`

## 设计规范（业界通用实践）

- 元数据最小化：front matter 仅保留 `name` 与 `description`。
- 渐进加载：`SKILL.md` 只写流程与决策规则，细节放 `references/`。
- 资源按职责拆分：`scripts/` 放可执行逻辑，`assets/` 放输出素材。
- 触发语义明确：`description` 同时描述能力与触发场景，避免含糊词。
- 可验证优先：生成后必须可通过校验脚本，避免“看起来正确但不可触发”。

## 常用命令

```bash
# 最小化生成（仅 SKILL.md）
./scripts/create_skill.py --name tech-radar --description "维护技术选型雷达并输出建议"

# 同时创建 scripts/references 目录
./scripts/create_skill.py --name api-doc-writer --description "根据接口变更生成技术文档" --resources scripts,references

# 生成后立即校验仓库 skills
../../scripts/skill_check.py
```

Reference: [create_skill.py](scripts/create_skill.py)
