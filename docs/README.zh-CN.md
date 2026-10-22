# Agent Rule Sentinel 中文说明

本项目提供一个**本地运行、先预览再写入**的 CLI 工具，用同一份 Markdown 规则维护 Codex 的 `AGENTS.md` 和 Claude Code 的 `CLAUDE.md`。

解决的问题：同一项目用两个 AI 编程助手开发时，项目规范容易重复、过期或相互矛盾。工具只更新被标记的托管段落，不替换文件其余内容。

## 安装与使用

需要 Python 3.10 及以上。下载项目后，在项目目录执行：

```bash
python -m pip install -e .
```

进入你自己的软件项目根目录，运行：

```bash
agent-rule-sentinel init
```

打开 `.agent-rule-sentinel/source.md`，填写项目目标、目录结构、测试命令及编码规范，**不要写入密码、API Key 或敏感个人信息**。

```bash
agent-rule-sentinel plan           # 仅预览，不修改文件
agent-rule-sentinel sync --apply   # 明确允许后才写入
agent-rule-sentinel check          # 检测差异，适合 CI
```

只更新 Claude 文件：

```bash
agent-rule-sentinel sync --target claude --apply
```

## 保护规则

- 原有 `AGENTS.md` 和 `CLAUDE.md` 中托管块之外的文字保留。
- 修改前对已有文件生成私密备份，位于 `.agent-rule-sentinel/backups/`。
- 不自动联网、不上传文件、不替用户 Git 提交、不自动运行 AI。
- 检测明显密钥格式、符号链接、超大文件和异常托管标记时拒绝执行。
- 密钥检测只是启发式检查，**不能代替专业的秘密信息扫描或人工检查**。
- 备份中可能含敏感内容。执行 `sync --apply` 首次保存备份前，程序会自动生成 `.agent-rule-sentinel/backups/.gitignore`，避免普通的 `git add .` 把备份一起提交；你也可以在项目根目录的 `.gitignore` 中添加 `.agent-rule-sentinel/backups/` 作为额外保护。若该位置已有不同的忽略配置，程序会拒绝覆盖，需要先人工核查。
- Git 忽略规则**不能保护已经被 Git 跟踪的备份文件**，也不能阻止 `git add -f` 强制添加，更不能清理过去的提交历史。已经意外提交的敏感内容需要单独处理。

## 贡献项目

欢迎 Issue、文档改进、Bug 修复和测试案例。请先阅读 [贡献指南](../CONTRIBUTING.md) 和 [安全政策](../SECURITY.md)。

## 开源与声明

采用 MIT 许可证。项目与 OpenAI、Anthropic 无官方关联；不保证获得任何开源资助或优惠活动资格。
