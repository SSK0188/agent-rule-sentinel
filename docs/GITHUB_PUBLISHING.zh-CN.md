# 使用自己的 GitHub 账号发布项目

以下步骤需要仓库所有者在自己的 Mac 上执行。项目作者必须对公开代码、许可证和真实维护工作负责。

## 先确认 GitHub CLI 和 Git 可用

```bash
git --version
gh --version
```

若缺少 GitHub CLI，可参考 <https://cli.github.com/>，在 Mac 使用 Homebrew 的常见安装方式是 `brew install gh`。

```bash
gh auth login
```

## 创建公开仓库并推送

下载解压本项目的 ZIP 后，进入包含 `pyproject.toml` 的目录：

```bash
cd /path/to/agent-rule-sentinel
PYTHONPATH=src python3 -m unittest discover -s tests -v

git init -b main
git add .
git commit -m "feat: publish agent-rule-sentinel 0.1.0"
gh repo create agent-rule-sentinel --public --source=. --remote=origin --push
```

如果 Git 提示没有设置身份，先使用真实姓名或你希望公开的开发者署名设置 `git config user.name`、`git config user.email`。不要使用虚假身份。

GitHub 网页也可以先新建 Public 仓库，再在本地用 Git 推送，但新仓库不应提前添加 README、LICENSE 等与本包冲突的初始化文件。

## 发布之后

- 开启 GitHub Actions、Issues 和私密漏洞报告（若可用）。
- 检查 Actions 测试是否通过。
- 创建真实的 `v0.1.0` Release，准确描述测试范围。
- 让真实用户使用、反馈、提交 PR，持续修复问题。
- 不要为任何资助活动伪造 Star、下载量、PR、用户评价或维护身份。

GitHub 公开仓库上线 ≠ 自动满足 Codex for Open Source 审核标准。
