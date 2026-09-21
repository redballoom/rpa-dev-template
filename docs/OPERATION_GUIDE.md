# 运行与排障指南

本文只说明环境初始化、生产调用、结果消费和常见运行问题。输入字段以 `SHADOWBOT_INPUT_CONTRACT.md` 为准，代码分层以 `DEVELOPMENT_GUIDE.md` 为准，职责边界以 `RPA_PYTHON_BOUNDARY.md` 为准。

## 初始化运行环境

生产入口只使用项目虚拟环境，不回退系统 Python：

```bat
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

本地开发再安装测试依赖：

```bat
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

初始化、迁移或模板升级后执行：

```bat
.venv\Scripts\python.exe tools\doctor.py
```

doctor 失败时，先修复必需文件、JSON、忽略规则、入口解释器或本机路径问题，再接入业务。

## 生产调用

影刀生成独立输入文件后调用：

```bat
run.bat {run_id} {work_dir} {input_file}
```

三个位置参数均为必填。`run_id` 不写入输入 JSON；输入信封必须包含 `schema_version: "1.0"` 和非空 `tasks[]`。

示例：

```bat
run.bat rpa_20260921_001 C:\RPA\Demo\data C:\RPA\Demo\input_rpa_20260921_001.json
```

本地诊断使用同一输入契约，但不作为生产入口：

```bat
.venv\Scripts\python.exe runner.py --run_id rpa_20260921_001 --repo_path C:\RPA\Demo --work_dir C:\RPA\Demo\data --input_file C:\RPA\Demo\input_rpa_20260921_001.json
```

## 运行产物

一次正常调用会生成：

- `runner_{run_id}.json`：影刀消费的私有完整结果。
- `evidence/runs/{run_id}.summary.json`：可提交或上传的脱敏摘要。
- `logs/run_{run_id}.log`：Python 日志。
- `crash_snapshots/crash_{run_id}.json`：发生系统异常时的脱敏快照。
- `data/output/`：业务输出。

影刀先等待 BAT 结束，再读取本次新生成的 runner。BAT 非零退出通常表示虚拟环境、参数、路径或 Python 启动故障；BAT 正常结束后，业务结果以 runner 的 `status` 为准。

## 状态消费

| status | 含义 | 默认动作 |
| --- | --- | --- |
| `success` | 全部成功 | 完成 |
| `warning` | 存在业务跳过，无系统错误 | 记录后完成 |
| `retryable_error` | 系统错误具有暂时性 | 停止并记录；由 Python 业务设计决定重试范围 |
| `pending_fix` | 存在不可重试系统问题 | 停止，进入修复闭环 |
| `locked` | 未取得 Python 执行锁，业务尚未开始 | 等待后重试 |
| `fatal` | 输入、配置或入口级错误 | 停止并通知维护 |

当前影刀模板的 `RunEvidence` 只记录外部结果，不会自动用 Python 非成功状态改写影刀主流程。需要停止或告警时，应在影刀侧显式分支；影刀不要解析 Python traceback。

## 重试边界

`data.retryable=true` 是错误性质提示，不是整次运行的自动重放指令。

- 只读请求、短暂网络错误、限流和轮询，可由 Python service 做有限重试和退避。
- 上传、创建、写回等有副作用的操作，必须先具备幂等键、upsert 或完成状态记录。
- 影刀默认不因 `retryable_error` 重跑整个 BAT。
- 只有业务契约明确说明整次运行可重复时，影刀才执行 `tasks[]` 级重放。
- `locked` 表示业务尚未开始，可以由影刀等待后重试。

## 批任务中断策略

默认 `context.fail_fast=true`：`BusinessException` 记录为 warning 后继续，`SystemException` 记录为 error 并中断后续任务。

只有任务彼此独立时，才可以设置：

```json
{
  "context": {"fail_fast": false}
}
```

也可以对单个独立任务设置 `continue_on_error=true`。存在前后依赖、上传、写回或不可重复副作用时，不要放宽中断策略。

## 可选外部集成

飞书、Linear 和 AI 默认关闭。只有本地 `project.json` 中对应开关为 `true` 时才访问外部服务：

```json
{
  "project": "业务项目名",
  "integrations": {
    "feishu": {"enabled": false, "webhook": ""},
    "linear": {"enabled": false, "api_key": "", "team_id": ""},
    "ai": {
      "enabled": false,
      "base_url": "https://api.openai.com/v1",
      "api_key": "",
      "model": "",
      "api_format": "chat_completions",
      "timeout": 30
    }
  }
}
```

真实密钥只写入被 Git 忽略的本地 `project.json`。`integrations.ai.api_format` 支持 `chat_completions` 和 `responses`；DashScope 示例见 `examples/project.dashscope.example.json`。

## 常见故障

- `.venv` 不存在：创建虚拟环境并安装依赖，不能依赖系统 Python 回退。
- BAT 非零退出且没有新 runner：先检查退出码、参数、`work_dir`、`input_file` 和 `.venv`。
- runner 为 `fatal`：检查输入文件是否存在、JSON 是否可解析、Schema 版本和任务结构是否合法。
- runner 为 `pending_fix`：按 `ISSUE_FIX_WORKFLOW.md` 收集 runner、日志、快照和脱敏输入样本。
- runner 为 `locked`：确认没有另一个 Python 运行仍占用项目后再重试。
- handler 未找到：实现对应 `tasks[].type`，不要把未实现的 payload 草案当成可运行输入。
- 输出路径被拒绝：将业务输出放在 `data/output/` 下，不传入越界绝对路径或 `..`。

## 上线前检查

上线前执行：

```bat
.venv\Scripts\python.exe -m pytest tests -v
.venv\Scripts\python.exe tools\doctor.py
```

再按 `ACCEPTANCE_CHECKLIST.md` 核对输入、输出、状态消费、重试幂等、Evidence 和未验证风险。外部 Agent、Skill 或项目管理工具可以辅助研发，但不是运行依赖，也不得改变 runner 的状态语义。
