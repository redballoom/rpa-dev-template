# 影刀与 Python 接口示例

本文档说明影刀如何向 Code 项目传入业务参数，以及 Python 如何返回标准结果。

## 输入示例：可运行模板示例

```json
{
  "project": "开发模板",
  "tasks": [
    {
      "id": "filter-001",
      "name": "筛选待处理记录",
      "type": "filter_records",
      "payload": {
        "input_file": "data/input/records.json",
        "output_file": "data/output/filtered_records.json",
        "status_field": "status",
        "match_value": "ready"
      }
    }
  ],
  "context": {
    "operator": "yingdao",
    "env": "test",
    "source": "shadowbot",
    "app_name": "文件汇总项目"
  }
}
```

## 输入示例：无 input.json

影刀可以不传 `input_file`。此时 `runner.py` 不读取输入文件，业务代码使用默认逻辑：

```bat
python runner.py --run_id rpa_001 --repo_path C:\CodePJ\Demo
```

## 输入示例：传 input.json

```bat
python runner.py --run_id rpa_001 --repo_path C:\CodePJ\Demo --work_dir C:\CodePJ\Demo\data --input_file C:\CodePJ\Demo\input.json
```

## 标准输出

Python 默认在项目根目录输出 `runner_{run_id}.json`：

```json
{
  "status": "success",
  "message": "处理完成",
  "data": {
    "run_id": "rpa_001",
    "results": [
      {
        "task": {
          "id": "merge_files",
          "name": "筛选待处理记录",
          "type": "filter_records",
          "payload": {
            "output_file": "data/output/filtered_records.json"
          }
        },
        "status": "ok",
        "data": {
          "input_file": "data/input/records.json",
          "output_file": "data/output/filtered_records.json",
          "total_count": 3,
          "matched_count": 2,
          "skipped_count": 1
        }
      }
    ],
    "warnings": [],
    "errors": [],
    "retryable": false,
    "crash_snapshot_dir": "",
    "log_path": "logs/run_rpa_001.log"
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

影刀不直接解析 Python 堆栈。异常排查交给日志、快照和 AI 修复流程。

## 协议形态示例

真实业务可以使用 `merge_excel`、`download_report`、`filter_abnormal_orders` 等自定义 `tasks[].type`，但这些类型接入前必须由 AI 按任务契约实现对应 handler。模板不会默认假成功。
