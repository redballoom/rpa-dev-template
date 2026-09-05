# 可迁移运行证据

每次 `runner.py` 结束时，除本机私有的 `runner_{run_id}.json` 外，还会生成：

```text
evidence/runs/{run_id}.summary.json
```

摘要用于 G4/G5、PR 或跨机器复核。它可以提交或上传；原始 runner、输入、日志、snapshot 和业务输出仍保持忽略，不应进入 Git。

## 摘要证明什么

- `run.run_id`、最终状态、UTC 开始/结束时间、运行时 Git commit 和工作树是否干净。
- `runtime.entrypoint` 是 `run.bat` 还是直接 `runner.py`。
- Python 实现、版本、脱敏后的解释器标识，以及项目虚拟环境或系统回退策略。
- 计划、记录、成功、跳过、失败、warning 和 error 数量。
- warning/error 仅按 `kind + code + category + retryable` 聚合。
- 输入文件和原始 runner 的字节数与 SHA-256，不复制其内容或绝对路径。
- `integrity.sha256` 校验摘要自身除 `integrity` 外的规范化 JSON 内容。

## 白名单与禁止字段

摘要采用封闭白名单，Schema 各对象均设置 `additionalProperties=false`。允许的业务侧信息只有运行状态、计数、异常代码/类别和重试标记。

以下源字段及其值不得复制进摘要：`task`、`name`、`payload`、`message`、`context`、`traceback`、`account`、`cookie`、`token`、`secret`、`credentials`、`authorization`、`api_key`、`session`、原始 `response`。输入和 runner 只保存哈希与字节数。

## 生产入口与解释器

`run.bat` 保持原来的三个位置参数：

```bat
run.bat {run_id} {work_dir} {input_file}
```

它优先使用项目 `.venv\Scripts\python.exe`；项目虚拟环境不存在时，明确回退 PATH 中的 `python`。两种选择都会写入摘要。直接运行 `runner.py` 时，摘要会标记入口为 `runner.py`，不能冒充生产 BAT 验证。

初始化或迁移后运行：

```bat
python tools\doctor.py
```

doctor 会核对 BAT 的项目虚拟环境选择策略、`runner.py` 路径和入口环境标记是否一致。

## 独立复核

另一台机器无需原始 runner 即可检查摘要格式、白名单和自身完整性：

```bat
python tools\evidence.py evidence\runs\{run_id}.summary.json
```

返回 `valid=true` 且 `run.working_tree_clean=true`，才能把该文件作为精确 commit 的交付证据引用。若本机仍保留输入或 runner，可再将其 SHA-256 与 `artifacts` 中记录的值比对。

已脱敏样例见 `docs/examples/evidence_summary_success.json`，机器可读契约见 `schemas/evidence-summary.schema.json`。
