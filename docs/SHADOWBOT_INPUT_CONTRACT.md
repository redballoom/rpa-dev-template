# 输入契约

本模板面向影刀 RPA 调度的 Code 项目。影刀负责准备业务数据，Python 负责处理业务数据。

## 运行方式

传入 `input_file`：`runner.py` 读取输入，按 `tasks[].type` 路由到对应 handler 执行业务逻辑。

推荐 BAT 调用：

```bat
run.bat {run_id} {work_dir} {input_file}
```

推荐 Python 调用：

```bat
python runner.py --run_id {run_id} --repo_path {repo_path} --work_dir {work_dir} --input_file {input_file}
```

不传 `input_file` 时，`runner.py` 按默认逻辑运行。

`run_id` 由影刀或 BAT 通过命令行传入，不写入输入文件。即使输入文件中出现顶层 `run_id`，Python 也以命令行 `--run_id` 为准。

## 文件位置

| 文件或目录 | 说明 |
| --- | --- |
| `input_{run_id}.json` | 推荐命名。影刀生成的单次业务输入，放在项目根目录，适合并发隔离 |
| `input.json` | 兼容命名。仅适合单实例串行运行，不建议并发流程共用 |
| `data/input/` | 业务输入文件，如 Excel、CSV、下载文件 |
| `data/output/` | 业务输出文件，如汇总结果 |
| `data/temp/` | 临时文件 |
| `runner_{run_id}.json` | Python 标准执行结果 |
| `logs/` | Python 运行日志 |
| `crash_snapshots/` | 系统异常快照 |

## 输入结构

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

## 字段约定

| 字段 | 必填 | 说明 |
|------|:---:|------|
| `project` | ✅ | 项目名，决定配置加载和 Linear 工单归属 |
| `tasks[].id` | ✅ | 任务唯一标识，用于日志追踪 |
| `tasks[].name` | ✅ | 任务显示名，出现在日志和飞书卡片 |
| `tasks[].type` | ✅ | **路由键**，决定 `entry.py` 调用哪个 handler |
| `tasks[].payload` | ✅ | 业务数据，handler 的实际输入，不同项目自定义 |
| `context.operator` | 推荐 | 触发者，写入 crash snapshot 和 Linear 工单 |
| `context.env` | 推荐 | 环境（test/prod），写入 crash snapshot 和 Linear 工单 |
| `context.source` | 推荐 | 调用来源，写入 crash snapshot 和 Linear 工单 |
| `context.app_name` | 可选 | 应用名，写入 Linear 工单
| `context.fail_fast` | 可选 | 系统异常后是否中断后续任务，默认 `true`。独立批任务可设为 `false` |
| `tasks[].continue_on_error` | 可选 | 单任务系统异常后是否继续执行后续任务，默认 `false` |

## 并发约定

- 推荐影刀为每次运行生成独立输入文件，例如 `input_{run_id}.json`。
- `runner_{run_id}.json`、`logs/run_{run_id}.log`、`crash_snapshots/crash_{run_id}.json` 均按 `run_id` 隔离。
- `.runner.lock` 只保护 Python 执行阶段，不能保护影刀写入固定 `input.json` 的阶段。
- 若必须使用固定 `input.json`，应保证同一项目目录同一时刻只有一个影刀流程写入和执行。
