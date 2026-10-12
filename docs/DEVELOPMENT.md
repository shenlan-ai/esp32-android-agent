# 规格驱动开发

已验证工具：OpenSpec 1.13.1。Windows 下若 PowerShell 限制 npm 脚本，使用 `openspec.cmd`。项目文件使用 UTF-8。

## 开始变更

```text
openspec list --specs
openspec list
openspec new change <change-id>
openspec instructions proposal --change <change-id> --json
```

读取相关正式规格；按照指引依次完成 proposal.md、specs、design.md、tasks.md。需求和场景保留英文结构标题和 SHALL/MUST，内容使用中文。

变更中维护 files.txt，每行一个仓库相对路径或有限目录通配符，例如 `server/android_agent/adb.py`。OpenSpec 自身文件归属其变更，正式规格生成路径也应列入范围。禁止 `*`、`**` 或 `**/*` 覆盖全仓库。

不改变产品行为时在 `.openspec.yaml` 写 `skip_specs: true`，明确为什么无需 delta；仍填写设计、任务、文件范围和验证记录。

## 实现与检查

```text
openspec validate <change-id> --strict --no-interactive
python scripts/check_changes.py
python -m unittest discover -s scripts/tests
```

实现前规格校验，修改范围扩展先更新 artifacts。新增功能需要适合该行为的测试。完成任务后更新 checkbox，在 validation.md 记录证据。

范围检查默认比较 HEAD 与工作树，并包含未跟踪文件。首次提交前检查所有项目文件。CI 使用 `python scripts/check_changes.py --base <base-sha>`，包含基线之后所有修改；旧归档清单不能为新修改提供范围。

## 完成变更

```text
openspec archive <change-id> --yes
openspec validate --all --strict --no-interactive
openspec validate --archived --no-interactive
python scripts/check_changes.py
```

归档前全部任务完成且 validation.md 存在；未完成任务不能勾选或归档。归档更新正式规格，自动生成的规格仍是该变更的一部分。

首次规范变更同时纳入之前已经讨论并写出的架构文档。后续代码与说明必须先有新变更。Git 提交信息包含变更 ID，不自动发布远程版本。
