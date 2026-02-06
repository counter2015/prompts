这个仓库参考了[DCjanus/prompts](https://github.com/DCjanus/prompts)
Skills 编写可参考 Claude 官方的 [技能创作最佳实践](https://platform.claude.com/docs/zh-CN/agents-and-tools/agent-skills/best-practices) 文档。


## 运行前提

本仓库内的所有脚本与 skills 默认假设当前环境已安装最新版 [`uv`](https://github.com/astral-sh/uv)。

## 仓库结构

- [`AGENTS.md`](AGENTS.md)：Codex 中所有代理共享的基础约束与工作流
- [`skills/`](skills)：按功能分类的技能库，详情见下方技能列表
- [`scripts/`](scripts)：放置 uv script 模式的工具脚本（约束见 [scripts/AGENTS.md](scripts/AGENTS.md)）
  - [`token_count.py`](scripts/token_count.py)：基于 [tiktoken](https://github.com/openai/tiktoken) 的 token 计数 CLI
  - [`token_tree.py`](scripts/token_tree.py)：统计仓库内所有 Git 跟踪文本文件的 token 数，按树状结构输出；支持全局比例进度条、对齐条形显示与百分比，可用 `--bar-width` 调整条形宽度

### 技能列表

| 技能 | 说明 |
| --- | --- |
| [`github-pr-issue`](skills/github-pr-issue/SKILL.md) | GitHub CLI 使用指引（issue/PR 查看、编辑与创建，含团队 PR 规范） |
| [`counter2015-preferences`](skills/counter2015-preferences/SKILL.md) | counter2015 在不同语言中偏好的第三方库与使用场景清单 |
| [`pwdebug`](skills/pwdebug/SKILL.md) | 通过命令行复用浏览器会话进行前端调试 |
| [`tech-doc`](skills/tech-doc/SKILL.md) | 技术协作文档的统一写作指南 |
| [`fetch-url`](skills/fetch-url/SKILL.md) | 渲染 URL 并输出多格式内容或原始 HTML（Playwright + trafilatura） |
| [`skill-generator`](skills/skill-generator/SKILL.md) | 生成或更新技能脚手架（目录、SKILL.md 与可选资源目录） |
| [`web-reverse-analysis`](skills/web-reverse-analysis/SKILL.md) | 从给定网址做技术分析与逆向拆解，并输出可复现的实现方案 |
