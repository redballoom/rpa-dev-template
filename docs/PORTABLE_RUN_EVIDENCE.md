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

返回 `valid=true` 只证明摘要的格式、白名单与完整性，不证明当前代码可交付。若本机仍保留输入或 runner，可再将其 SHA-256 与 `artifacts` 中记录的值比对。

## 版本与重复运行（Schema 2）

Schema 2 保留精确的 `run.commit` 和原始 Git `run.working_tree_clean`，新增 `run.delivery_tree_clean`。后者只允许以下记录文件变化：

- `.project-gates/project.json`、`.project-gates/gate-history.md`；
- `.trellis/tasks/`、`.trellis/workspace/` 下的 `.md`、`.json`、`.jsonl` 记录；
- `evidence/runs/` 下直接存放的 `*.summary.json`。

其他文件一律视为交付内容，包括脚本、Spec、Skill 指令、配置、依赖、契约以及未知文件。生成的摘要不会污染下一次运行的交付清洁度，但原始工作树状态仍如实记录。被 Git 忽略的本地配置和业务输入不属于该代码版本检查的证明范围。

Controller 的 `evidence-check` 将历史有效性 `valid` 与当前交付就绪 `delivery_ready` 分开报告。就绪要求摘要合法、运行成功或 warning、运行时交付代码干净、入口为 `run.bat`，同时摘要 commit 是当前 HEAD 的祖先，所有后续提交都只改记录，当前工作区也只改记录。中间代码修改后又回滚也会要求重新验证。只提交摘要或治理记录不会使已有运行证据失效。

旧 Schema 1 仍可读取，其运行时清洁度继续使用原 `working_tree_clean`，不会把旧的脏工作树运行升级为合格证据。Schema 2 必须使用支持新版本的 Controller；旧 Controller 拒绝未知版本，不能混装发布。

以上检查不替代 PR review、影刀真实调用证据或业务输出回读。`warning` 是否符合业务验收仍需独立判断。

已脱敏样例见 `docs/examples/evidence_summary_success.json`，机器可读契约见 `schemas/evidence-summary.schema.json`。
