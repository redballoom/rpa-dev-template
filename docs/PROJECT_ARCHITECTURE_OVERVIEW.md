# 项目结构与执行流程

## 目录结构

```text
开发模板/
  runner.py
  run.bat
  project.json
  project.template.json
  input.json
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
  tests/
```

`input.json` 是影刀生成的单次业务输入。  
`data/` 是业务文件目录。  
`runner_{run_id}.json` 默认输出在项目根目录。

## 执行流程

```text
影刀准备业务数据
  -> 写 input.json
  -> 调用 run.bat 或 runner.py
  -> runner.py 读取 input.json
  -> core.entry.run_tasks() 按 tasks[].type 路由
  -> 写业务输出到 data/output/
  -> 写 runner_{run_id}.json
  -> 影刀读取 status 并分支
```

## 输入模式

传入 input：

```bat
run.bat rpa_001 C:\CodePJ\Demo\data C:\CodePJ\Demo\input.json
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
