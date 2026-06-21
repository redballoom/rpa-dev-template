# 影刀与 Python 接口示例

本文档说明影刀如何向 Code 项目传入业务参数，以及 Python 如何返回标准结果。

## 输入示例：文件汇总

推荐文件名：`input_{run_id}.json`。

```json
{
  "project": "文件汇总项目",
  "tasks": [
    {
      "id": "task-001",
      "name": "合并文件",
      "type": "merge_excel",
      "payload": {
        "source_files": ["data/input/a.xlsx", "data/input/b.xlsx"],
        "output_file": "data/output/summary.xlsx",
        "merge_key": "订单号"
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

## 输入示例：无 input_file

影刀可以不传 `input_file`。此时 `runner.py` 不读取输入文件，业务代码使用默认逻辑：

```bat
python runner.py --run_id rpa_001 --repo_path C:\CodePJ\Demo
```

## 输入示例：传 input_file

```bat
python runner.py --run_id rpa_001 --repo_path C:\CodePJ\Demo --work_dir C:\CodePJ\Demo\data --input_file C:\CodePJ\Demo\input_rpa_001.json
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
          "name": "merge_files",
          "type": "file_summary",
          "payload": {
            "output_file": "data/output/summary.xlsx"
          }
        },
        "status": "ok"
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
