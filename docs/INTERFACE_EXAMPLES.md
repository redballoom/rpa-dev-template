# 影刀与 Python 接口示例

本文档说明影刀如何向 Code 项目传入业务参数，以及 Python 如何返回标准结果。

## 输入示例：计算汇总

推荐文件名：`input_{run_id}.json`。

```json
{
  "schema_version": "1.0",
  "project": "计算汇总项目",
  "tasks": [
    {
      "id": "calc-001",
      "name": "计算汇总",
      "type": "calc_summary",
      "payload": {
        "numbers": [10, 20, 30, 40],
        "output_file": "data/output/calc_result.json"
      }
    }
  ],
  "context": {
    "operator": "yingdao",
    "env": "test",
    "source": "shadowbot",
    "app_name": "计算汇总项目"
  }
}
```

## 生产调用

影刀通过 BAT 传入本次独立输入文件；三个位置参数均必填：

```bat
run.bat rpa_001 C:\CodePJ\Demo\data C:\CodePJ\Demo\input_rpa_001.json
```

## 本地诊断调用

```bat
.venv\Scripts\python.exe runner.py --run_id rpa_001 --repo_path C:\CodePJ\Demo --work_dir C:\CodePJ\Demo\data --input_file C:\CodePJ\Demo\input_rpa_001.json
```

## 标准输出

Python 默认在项目根目录输出 `runner_{run_id}.json`：

统一外层结构由 `schemas/output.schema.json` 约束。各项目在契约阶段约定
`data.results[].data` 的业务字段，影刀先消费统一状态，再消费业务结果。

```json
{
  "status": "success",
  "message": "处理完成",
  "data": {
    "run_id": "rpa_001",
    "results": [
      {
        "task": {
          "id": "calc-001",
          "name": "计算汇总",
          "type": "calc_summary",
          "payload": {
            "numbers": [10, 20, 30, 40],
            "output_file": "data/output/calc_result.json"
          }
        },
        "status": "ok",
        "data": {
          "count": 4,
          "sum": 100.0,
          "average": 25.0,
          "min": 10.0,
          "max": 40.0,
          "output_file": "data/output/calc_result.json"
        }
      }
    ],
    "warnings": [],
    "errors": [],
    "retryable": false,
    "crash_snapshot_dir": "",
    "log_path": "logs/run_rpa_001.log",
    "evidence_summary_path": "evidence/runs/rpa_001.summary.json"
  }
}
```

## 影刀消费原则

影刀只消费：

- `status`
- `message`
- `data.results`
- `data.warnings`
- `data.errors`
- `data.retryable`

影刀不直接解析 Python 堆栈。异常排查交给日志、快照和人工/AI 修复流程。

`data.retryable=true` 是错误性质提示，不是自动重试命令。影刀默认不重放整个 `tasks[]`；具体重试由 Python handler/service 的业务契约决定。`locked` 因业务尚未开始，可以单独按等待后重试处理。

当前影刀模板的 `RunEvidence` 会读取并记录以上字段，但不会把非成功状态自动转成主流程失败；需要状态驱动动作时，应在影刀侧增加显式分支。
