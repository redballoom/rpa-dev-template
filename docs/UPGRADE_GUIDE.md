# 模板升级指南

当前模板版本：`0.4.0`。

本指南只升级新模板或明确选择升级的项目，不自动修改既有业务项目。

## 文件分类

模板基础设施：`runner.py`、`run.bat`、`core/config.py`、`core/exceptions.py`、`core/infrastructure/`、Schema 和 `tools/`。

业务资产：`core/handlers/`、`core/services/`、业务测试、payload 示例和业务文档。升级时不得直接覆盖。

可选治理文件：`.agents/`、`.codex/`、`.trellis/`、`.project-gates/`、`teamwiki/` 等。它们不是运行依赖，不纳入核心模板升级。

## 从旧版本升级到 0.4.0

1. 创建并安装项目 `.venv`；`run.bat` 不再回退系统 Python。
2. 把 `project.json` 的飞书、Linear、AI 配置迁移到 `integrations`，并明确设置各自 `enabled`。
3. 把 `entry.py` 中的业务实现迁到 `core/handlers/`，外部能力迁到 `core/services/`。
4. 将业务输出限制到 `data/output/`，默认文件名加入 `run_id`，关键 JSON 改为原子写入。
5. 确认业务代码没有依赖输入 `context.repo_path`；运行入口会覆盖该字段。
6. 运行 `.venv\Scripts\python.exe tools/doctor.py` 和完整测试。

旧的顶层 `feishu_webhook`、`linear`、`ai` 字段不会激活集成。必须迁移到 `integrations` 并显式设置 `enabled=true`，避免旧项目在升级后意外访问外部服务。
