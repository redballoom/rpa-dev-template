# 项目结构与执行流程

## 目录结构

```text
开发模板/
  runner.py
  run.bat
  project.json
  project.template.json
  input_{run_id}.json
  core/
    entry.py
    config.py
    exceptions.py
    logger.py
    notifier.py
    ai_analyzer.py
  data/
    input/
    output/
    temp/
  logs/
  crash_snapshots/
  docs/
  schemas/
    input.schema.json
    workflow.schema.json
    handoff.schema.json
  .rpa_ai/
    workflow.template.json
  tools/
    doctor.py
  tests/
```

`input_{run_id}.json` 是推荐的单次业务输入命名，用于并发隔离。固定 `input.json` 仅作为单实例串行兼容写法。
`data/` 是业务文件目录。  
`runner_{run_id}.json` 默认输出在项目根目录。

`.rpa_ai/workflow.template.json` 负责描述 AI 协作 Gate 和 Skill 兼容关系。`schemas/` 负责给输入、工作流和 handoff 提供机器可读约束。`tools/doctor.py` 用于初始化、迁移和升级后的模板自检。

## 执行流程

```text
影刀准备业务数据
  -> 写 input_{run_id}.json
  -> 调用 run.bat 或 runner.py
  -> runner.py 读取 input_file
  -> core.entry.run_tasks() 按 tasks[].type 路由
  -> 写业务输出到 data/output/
  -> 写 runner_{run_id}.json
  -> 影刀读取 status 并分支
```

## 输入模式

传入 input：

```bat
run.bat rpa_001 C:\CodePJ\Demo\data C:\CodePJ\Demo\input_rpa_001.json
```

不传 input：

```bat
python runner.py --run_id rpa_001 --repo_path C:\CodePJ\Demo
```

## 设计原则

- 影刀流程保持薄，只做调度和 UI 自动化。
- Python 业务逻辑可测试、可复现、可沉淀。
- `payload` 是业务变化入口。
- 输出协议稳定，便于影刀分支和 AI 修复。
