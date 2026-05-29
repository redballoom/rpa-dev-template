# 输入契约

本模板面向影刀 RPA 调度的 Code 项目。影刀负责准备业务数据，Python 负责处理业务数据。

## 运行方式

传入 `input.json`：`runner.py` 读取输入，按 `tasks[].type` 路由到对应 handler 执行业务逻辑。

推荐 BAT 调用：

```bat
run.bat {run_id} {work_dir} {input_file}
```

推荐 Python 调用：

```bat
python runner.py --run_id {run_id} --repo_path {repo_path} --work_dir {work_dir} --input_file {input_file}
```

不传 `input_file` 时，`runner.py` 按默认逻辑运行。

## 文件位置

| 文件或目录 | 说明 |
| --- | --- |
| `input.json` | 影刀生成的单次业务输入，放在项目根目录 |
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
