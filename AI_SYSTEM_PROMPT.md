# [Project Context] RPA AI-Self-Healing Workflow（自动化自愈架构）

## 1. System Objective
本项目是一个高度解耦的现代 RPA DevSecOps 工作流。旨在通过"逻辑与执行解耦"，实现网页端 RPA 自动化的极高稳定性和代码级 Bug 的"AI 全自动自愈"。

## 2. Architecture & Tech Stack
系统采用物理层面的职责分离，严禁越界：
* **Execution Layer（执行层 - 影刀/Shadowbot）：** 仅负责 UI 驱动交互（点击、输入）。严禁在其中编写复杂判断逻辑。
* **Logic Layer（逻辑层 - Python 3.x）：** 负责 DOM 解析、数据清洗、正则匹配与异常路由。代码托管于本地/Git，作为唯一真相源。
* **IPC Protocol（进程间通信）：** RPA 与 Python 之间严格通过 `runner_{run_id}.json` 进行状态握手（影刀生成 UUID 作为 run_id，Python 回写时必须携带），RPA 校验一致后判定执行有效，防止进程暴毙导致读取历史脏数据。
* **Alert Layer（告警层 - 飞书）：** 负责 L1 业务监控通知（黄牌）和 L2 系统异常通知（红色），采用**批量汇总模式**——执行完毕后一次性发送，不逐个轰炸。
* **Issue Tracker（工单层 - Linear）：** 专门接收未经捕获的代码级 Bug，作为唤醒下游 AI Agent（如 Claude Code）进行代码自愈的触发器。

## 3. Core Mechanisms（核心运行机制）
任何试图修改或扩展本项目的 AI，必须深刻理解并遵循以下机制：

### 3.1 异常分流路由（Exception Routing - 极其关键）
系统在 `core/exceptions.py` 中定义了严格的异常层级，严禁混淆：
* **`BusinessException`（业务异常）：** 如账号异常、金额超限。处理动作：**静默拦截 → 收集到 warnings 列表 → 流程继续**。AI 严禁因业务异常修改逻辑代码。
* **`SystemException`（系统级异常）：** 如 KeyError、DOM 结构变更引起的 AttributeError。处理动作：**捕获完整 Traceback & Payload → 创建 Linear 工单（仅生产分支） → 收集到 errors 列表 → 强制中断进程**。

> **通知策略：批量汇总模式。** 不再逐个即时发送飞书消息。所有 BusinessException 和 SystemException 在执行过程中被收集，执行完毕后由 `send_execution_summary()` 一次性发送飞书汇总卡片。全部成功时静默不通知。

> **分支感知逻辑：** 测试分支（fix/bug-test）下 SystemException 不会创建 Linear 工单，避免调试期间的误报污染工单系统。

### 3.2 动态热重载（Hot-Reloading）
为彻底解决 Python `sys.modules` 的内存缓存污染问题，允许 AI 修改代码后 RPA 立刻生效，入口文件 `runner.py` 强制使用了 `importlib.reload(core_module)`。

### 3.3 幂等性与防幽灵状态（Idempotency）
RPA 在每次调用 Python 前会生成全局唯一的 UUID（`run_id`）并注入。Python 必须在 JSON 返回体中携带此 `run_id`，RPA 校验一致后才判定执行有效，防止进程暴毙导致读取历史脏数据。

## 4. Directory Structure（核心目录结构）

```
.
├── AI_SYSTEM_PROMPT.md       # 本文件（AI 上下文）
├── CONTRIBUTING.md           # 业务模块编写指南（新 AI 必读）
├── project.json              # 项目运行配置（影刀生成，Python 读取）
├── git_controller.py         # Git 动态路由调度（影刀入口：切换 main / fix/bug-test）
├── runner.py                 # 影刀唯一调用入口（负责热重载、IPC JSON 落盘）
├── run.bat                   # Windows 一键启动脚本
├── core/                     # 核心逻辑库
│   ├── __init__.py
│   ├── entry.py              # 业务执行入口点（被 runner 调用，包含全局 try-except 兜底）
│   ├── exceptions.py         # 自定义异常类（BusinessException, SystemException）
│   ├── notifier.py           # 消息通知网关（飞书批量汇总 + Linear 工单，含分支感知）
│   └── config.py             # 配置加载（优先读 project.json，fallback 默认值）
├── commands/                 # 可插拔业务命令模块（新业务代码写在这里）
│   ├── __init__.py           # 命令注册表（COMMAND_REGISTRY）
│   └── ...                   # 业务模块（如 track_order.py）
├── tests/                    # 单元测试
│   └── test_exception_routing.py
├── data/                     # 运行时数据（.gitignore 忽略）
├── .gitignore
└── requirements.txt
```

## 5. Alert & Ticket Routing（告警与工单路由）

> **通知策略：批量汇总。** 异常不在触发时逐个通知，而是收集到列表中，执行完毕后由 `send_execution_summary()` 统一发送飞书消息。全部成功时静默不通知。

| 异常类型 | 触发条件 | 通知动作 | 后续处理 |
|----------|----------|----------|----------|
| `BusinessException` | 数据不合规、规则阻断 | 收集到 warnings 列表 → 飞书汇总（黄色卡片） | 跳过当前任务，继续执行 |
| `SystemException` | 代码级 Bug（DOM 变更、未捕获异常） | 创建 Linear 工单（仅 main） + 收集到 errors 列表 → 飞书汇总（红色卡片） | 强制中断，流程终止 |
| 全部成功 | 所有任务正常完成 | **不发通知**（静默） | 继续 |

> **生产分支判断：** `git rev-parse --abbrev-ref HEAD` 返回 `main` 时视为生产环境。测试分支（fix/bug-test）下 SystemException 不创建 Linear 工单。

## 6. IPC Contract（进程间通信契约）

### 影刀 → Python（调用 runner.py）
```bash
python runner.py --run_id <UUID> --repo_path <项目路径> --project <项目名>
```

### Python → 影刀（回写 runner_{run_id}.json）
```json
{
  "status": "success | warning | failed | fatal",
  "message": "处理完成 | 异常摘要",
  "data": {
    "run_id": "<UUID>",
    "results": [...]
  }
}
```

| status | 含义 | 影刀后续动作 |
|--------|------|------------|
| `success` | 全部任务正常完成 | 继续下一环节 |
| `warning` | 存在 BusinessException（跳过） | 记录日志，继续 |
| `failed` | SystemException 触发或任务失败 | 中断流程 |
| `fatal` | Runner 本身崩溃（导入错误等） | 紧急中断 |

## 7. Git Branch Strategy（分支策略）

| 分支 | 用途 | 说明 |
|------|------|------|
| `main` | 生产环境 | 稳定版本，SystemException 触发 Linear 工单 |
| `fix/bug-test` | 测试/调试 | 不创建 Linear 工单，避免污染 |
| `fix/*` | AI 自动 Bug 修复 | 自动创建 + PR |
| `feat/*` | 人工功能开发 | 人类开发者使用 |

## 8. 🤖 Rules for AI Assistant（对当前 AI 的严格指令）

1. **Do not break the IPC Contract：** 任何你编写的 Python 业务模块，其最终状态必须能够封装进字典并由 `runner.py` 写入 JSON。
2. **Respect Exception Hierarchy：** 遇到不符合预期的输入时，请仔细判断。如果是数据本身不合规，抛出 `BusinessException`；如果是目标系统的数据结构变了，抛出 `SystemException`（或让兜底逻辑捕获）。绝对不能使用 `raise Exception` 破坏分流。
3. **Provide Context for Self-Healing：** 如果你在编写抛出 `SystemException` 的代码，必须通过以下参数注入上下文：
   - `payload`（dict）：当时的"毒性上下文"（如引发崩溃的 JSON/HTML 片段）
   - `action`（str）：**必填**，正在做什么时出错（如"查询物流单号 HK001 的状态"）
   - `expected`（str）：**必填**，系统本来应该怎样（如"返回 JSON 响应"）
   - `actual`（str）：实际发生了什么（如"HTTP 500 内部错误"，可省略，默认用 message）
   
   > **详细用法和完整示例参见 [CONTRIBUTING.md](CONTRIBUTING.md)**
4. **No UI Logic in Python：** 不要试图在 Python 中引入 `selenium` 或 `playwright`，所有的浏览器驱动动作全都在外层的 RPA 软件中完成，Python 只做纯数据计算。
5. **Branch-Aware Ticket Creation：** 在创建 Linear 工单前，系统会自动判断当前 Git 分支。测试环境不创建工单，这是预期行为，不需要修复。

---

**[User Request follows below]**
