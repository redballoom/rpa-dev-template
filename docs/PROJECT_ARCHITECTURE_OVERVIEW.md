# 项目架构总览

> 目标：让人一眼看懂这个项目里，影刀做什么，Python 做什么，AI 做什么，`Craft Agent` 在哪里参与。  
> 适用对象：RPA 开发、Python 开发、AI 协作开发、验收人。

## 1. 一句话理解

这个项目可以理解成四层协作：

1. 影刀负责“拿数据、点页面、调入口、读结果、做分支”。
2. Python 负责“真正执行业务逻辑、处理数据、写日志、输出标准结果”。
3. AI 分两类：
   - 运行时 AI：分析崩溃快照，给出根因和修复建议。
   - `Craft Agent`：在另一个 AI 工作区里接手 Python 修复、补测试、更新文档。
4. 人类负责需求拆分、最终验收、合并发布。

## 2. 角色分工图

```mermaid
flowchart LR
    U["业务目标 / 人类决策"]

    subgraph RPA["影刀 RPA 层"]
        Y1["打开页面 / 登录 / 点击 / 下载 / 上传 / 截图"]
        Y2["生成 run_id"]
        Y3["写入 input_{run_id}.json"]
        Y4["调用 run.bat"]
        Y5["读取 runner_{run_id}.json"]
        Y6["按 status 分支: 继续 / 重试 / 挂起 / 通知人工"]
    end

    subgraph PY["Python 执行层"]
        P1["runner.py: 调度入口"]
        P2["config.py: 加载配置与自检"]
        P3["entry.py: 执行业务任务"]
        P4["业务处理: 清洗 / 校验 / 去重 / 转换 / API / DB"]
        P5["exceptions.py: 异常分类与状态判定"]
        P6["logger.py: 写 logs/run_{run_id}.log"]
        P7["notifier.py: 飞书汇总 / Linear 工单"]
        P8["输出 runner_{run_id}.json"]
        P9["写 crash_snapshots/crash_{run_id}.json"]
    end

    subgraph AI["AI 协作层"]
        A1["ai_analyzer.py: 读取 crash snapshot"]
        A2["运行时 AI: 输出根因 / 分类 / 修复建议 / 测试建议"]
        A3["Craft Agent 工作区: 接手 Python 修复"]
        A4["补测试 / 更新文档 / 准备验收说明"]
    end

    subgraph EXT["外部协作对象"]
        E1["飞书"]
        E2["Linear"]
        E3["Git 分支 / PR"]
    end

    U --> Y1
    Y1 --> Y2
    Y2 --> Y3
    Y3 --> Y4
    Y4 --> P1
    P1 --> P2
    P2 --> P3
    P3 --> P4
    P4 --> P5
    P5 --> P6
    P5 --> P7
    P5 --> P8
    P5 --> P9
    P9 --> A1
    A1 --> A2
    A2 -->|分析结果用于增强同一张工单| E2
    E2 --> A3
    A3 --> A4
    A4 --> E3
    P7 --> E1
    P7 -->|真正执行建单 仅一次| E2
    P8 --> Y5
    Y5 --> Y6
```

## 3. 一眼看懂各层职责

| 角色 | 它负责什么 | 它不负责什么 |
|------|------------|--------------|
| 影刀 | 页面操作、文件下载上传、调用 `run.bat`、读取 `runner`、按状态分支 | 不解析 Python 堆栈，不写业务规则，不修 Python |
| Python | 读取输入、执行业务逻辑、异常分类、日志、通知、输出标准结果 | 不做人机交互，不接管影刀页面流程 |
| 运行时 AI | 读取 `crash snapshot`，给根因、分类、修复建议 | 不直接改线上影刀流程 |
| `Craft Agent` | 在独立 AI 工作区里修改 Python、补测试、更新文档、准备修复分支 | 不代替影刀执行 UI 操作 |
| 人类 | 提需求、确认边界、验收、合并发布 | 不需要手工解析所有技术细节 |

## 4. 主执行流程图

这张图描述“任务正常进入系统并执行”的主链路。

```mermaid
sequenceDiagram
    participant H as 人类 / 业务方
    participant Y as 影刀
    participant B as run.bat
    participant R as runner.py
    participant C as config.py
    participant E as entry.py
    participant X as exceptions.py
    participant N as notifier.py
    participant O as runner_{run_id}.json

    H->>Y: 提出业务目标
    Y->>Y: 打开页面 / 登录 / 下载数据
    Y->>Y: 生成 run_id
    Y->>Y: 写 input_{run_id}.json
    Y->>B: 调用 run.bat run_id input_file
    B->>R: 启动 Python 调度
    R->>C: 加载 project.template.json + project.json
    C-->>R: 返回配置与校验结果
    R->>E: 传入 run_id / tasks / context
    E->>E: 执行业务逻辑
    E->>E: 数据清洗 / 校验 / 去重 / 转换 / API / DB

    alt 业务警告
        E->>X: BusinessException
        X-->>E: 记录 warning 并继续
    else 系统异常
        E->>X: SystemException
        X->>N: 创建通知与工单信息
        X-->>E: 返回 error 信息
    else 全部正常
        E-->>R: 返回 results
    end

    R->>O: 写 runner_{run_id}.json
    O-->>Y: 返回 status / message / data
    Y->>Y: 按 status 分支处理
```

## 5. 异常修复闭环图

这张图描述“Python 出错后，AI 怎么接手修复”，也是 `Craft Agent` 发挥价值的地方。

```mermaid
sequenceDiagram
    participant Y as 影刀
    participant P as Python 运行层
    participant S as crash_snapshot
    participant A as ai_analyzer.py
    participant L as Linear / 工单
    participant C as Craft Agent 工作区
    participant G as Git 修复分支
    participant H as 人类验收

    Y->>P: 发起一次运行
    P->>P: 执行业务逻辑
    P->>S: 写 crash_{run_id}.json
    P->>A: 传入 snapshot 做分析
    A-->>P: 返回根因 / 分类 / 修复建议
    P->>L: 创建 1 张 Linear 工单\n并把 AI 分析写入描述
    P-->>Y: 返回 status = pending_fix
    Y->>Y: 标记任务待修复

    L->>C: Craft Agent 读取工单 / 日志 / snapshot
    C->>C: 定位 Python 修改点
    C->>C: 修复代码并补测试
    C->>G: 提交 fix/{issue_id} 分支
    G-->>H: 发起 PR / 等待验收
    H->>H: 验证 pytest / 本地复现 / runner 输出
    H-->>Y: 通知重新运行
    Y->>P: 重试同类任务
```

## 6. 工单创建逻辑说明

这里最容易误解的点是：图里既有 `crash snapshot -> AI`，又有 `Python / notifier -> Linear`，看上去像创建了两次工单。

实际不是。

一次 `SystemException` 的真实顺序是：

1. `exceptions.py` 先写 `crash_{run_id}.json`
2. `ai_analyzer.py` 读取快照，生成根因、分类、修复建议、测试建议
3. `notifier.py::create_linear_issue()` 调用 Linear `issueCreate`
4. 创建的仍然是同一张工单，只是工单标题和描述里带上了 AI 分析结果
5. 飞书汇总通知里如果有 `issue_url`，只是附上这张工单的链接，不会再创建新工单

可以把它理解成：

```text
先分析 -> 再建单 -> AI 结果写进这 1 张工单 -> 飞书引用这 1 张工单
```

补充规则：

- `BusinessException` 不创建 Linear 工单
- `SystemException` 才尝试创建 Linear 工单
- 非生产分支下可能跳过真实建单，只保留结果和日志

## 7. 关键文件在链路中的位置

| 文件 | 它在流程里的位置 | 作用 |
|------|------------------|------|
| `run.bat` | 影刀调用入口 | 连接影刀和 Python |
| `runner.py` | Python 总调度器 | 读取输入、调配置、执行业务、输出结果 |
| `core/config.py` | 执行前 | 配置加载与自检 |
| `core/entry.py` | 主业务层 | 执行任务和汇总结果 |
| `core/exceptions.py` | 异常路径 | 统一异常编码、状态、snapshot |
| `core/logger.py` | 执行中 | 写运行日志 |
| `core/notifier.py` | 异常后 | 飞书汇总与工单创建 |
| `core/ai_analyzer.py` | 系统异常后 | 分析 crash snapshot |
| `docs/examples/*` | 需求、测试、协作时 | 输入输出协议样例 |

## 8. 推荐展示话术

如果你要对别人解释这个项目，可以直接用这段：

```text
影刀只负责和页面打交道，并把任务标准化后交给 run.bat。
Python 是真正的业务执行引擎，负责数据处理、规则判断、日志、异常和标准输出。
运行出错后，系统会产生日志、runner 结果和 crash snapshot。
AI 先分析 crash snapshot，再由 Craft Agent 在另一个 AI 工作区里接手 Python 修复、补测试、提分支，最后由人类验收合并。
```

## 9. 与现有文档的关系

- 职责边界：见 [RPA_PYTHON_BOUNDARY.md](D:\CraftPJ\开发模板\docs\RPA_PYTHON_BOUNDARY.md)
- 需求模板：见 [REQUIREMENT_TEMPLATE.md](D:\CraftPJ\开发模板\docs\REQUIREMENT_TEMPLATE.md)
- 修复闭环：见 [ISSUE_FIX_WORKFLOW.md](D:\CraftPJ\开发模板\docs\ISSUE_FIX_WORKFLOW.md)
- 验收清单：见 [ACCEPTANCE_CHECKLIST.md](D:\CraftPJ\开发模板\docs\ACCEPTANCE_CHECKLIST.md)
- 接口样例：见 [INTERFACE_EXAMPLES.md](D:\CraftPJ\开发模板\docs\INTERFACE_EXAMPLES.md)
