# RPA AI 自愈架构 — 快速上手指南

> 本文档面向**新接入的 AI 助手**（Claude Code / GPT / 其他）。
> 阅读本文后，你应该能**不问任何问题**直接编写业务模块并正确接入框架。

---

## 1. 你需要做什么

你的任务只有一个：**编写纯函数，处理业务数据。**
不要碰浏览器、不要碰 UI、不要写 RPA 流程——这些是影刀的事。

---

## 2. 文件结构与职责

```
项目根目录/
├── run.bat                    # 影刀调用的启动脚本（不用管）
├── runner.py                  # 影刀入口（不用管）
├── git_controller.py          # 影刀调 Git 切分支（不用管）
├── project.json               # 项目配置（影刀生成，你只读不写）
│
├── core/                      # ← 你的主战场
│   ├── entry.py               # 业务入口（调度任务）
│   ├── exceptions.py          # 异常定义（你要用这两个类）
│   ├── notifier.py            # 告警（批量汇总飞书 + Linear 工单，不用管）
│   └── config.py              # 配置加载（不用管）
│
├── commands/                  # ← 业务模块写在这里
│   ├── __init__.py            # 命令注册表
│   └── your_module.py         # 你的业务逻辑
│
└── tests/                     # 测试
```

**核心规则：只改 `commands/` 和 `core/entry.py`，其他文件不要碰。**

---

## 3. 编写业务模块的完整流程

### Step 1: 在 `commands/` 下创建业务模块

文件名用小写下划线，如 `commands/track_order.py`：

```python
"""
commands/track_order.py — 物流单号查询模块
"""
import requests
from core.exceptions import BusinessException, SystemException


def query_order_status(tracking_no: str, carrier: str = "auto") -> dict:
    """
    查询物流单号的最新状态。

    Args:
        tracking_no: 物流追踪号
        carrier: 承运商代码（auto=自动识别）

    Returns:
        {"status": "delivered", "location": "深圳", "update_time": "2026-05-07 10:00"}

    Raises:
        BusinessException: 单号格式不合法（跳过继续）
        SystemException: API 调用失败 / 数据结构变更（中断报错）
    """
    # --- 参数校验 ---
    if not tracking_no or len(tracking_no) < 5:
        raise BusinessException(
            message=f"物流单号格式不合法: {tracking_no}",
            project="物流追踪",
            context={"tracking_no": tracking_no, "carrier": carrier},
        )

    # --- 业务调用 ---
    try:
        resp = requests.get(
            f"https://api.example.com/track/{tracking_no}",
            params={"carrier": carrier},
            timeout=30,
        )
        data = resp.json()

    except requests.Timeout:
        raise SystemException(
            message=f"物流 API 超时: {tracking_no}",
            project="物流追踪",
            payload={"tracking_no": tracking_no, "carrier": carrier, "timeout": 30},
            action=f"查询物流单号 {tracking_no} 的运输状态",
            expected="HTTP 200 + JSON 响应",
            actual="requests.Timeout: 30s 无响应",
        )
    except requests.ConnectionError as e:
        raise SystemException(
            message=f"物流 API 连接失败: {e}",
            project="物流追踪",
            payload={"tracking_no": tracking_no},
            action=f"连接物流 API 查询单号 {tracking_no}",
            expected="成功建立连接并返回数据",
            actual=f"ConnectionError: {e}",
        )

    # --- 结果解析 ---
    try:
        return {
            "status": data["data"]["status"],
            "location": data["data"]["current_location"],
            "update_time": data["data"]["last_update"],
        }
    except (KeyError, TypeError) as e:
        raise SystemException(
            message=f"物流 API 返回结构异常: {e}",
            project="物流追踪",
            payload={"raw_response": str(data)[:500]},  # 截取前500字符
            action=f"解析物流 API 响应数据",
            expected="data.status / data.current_location / data.last_update 字段存在",
            actual=f"{type(e).__name__}: 缺少必要字段，可能是 API 版本升级导致结构变更",
        )


# 导出注册
HANDLERS = {
    "query_order": query_order_status,
}
```

### Step 2: 在 `commands/__init__.py` 中注册

```python
from commands.track_order import HANDLERS as track_handlers

COMMAND_REGISTRY = {
    **track_handlers,
    # 新模块在这里追加:
    # from commands.your_module import HANDLERS as your_handlers
    # COMMAND_REGISTRY = { **your_handlers }
}
```

### Step 3: 在 `core/entry.py` 中接入

```python
from commands import COMMAND_REGISTRY

def _process_single_task(task, project):
    """根据 task 配置分发到对应命令"""
    cmd_name = task.get("command")      # 如 "query_order"
    cmd_args = task.get("args", {})     # 如 {"tracking_no": "HK2025050001"}

    handler = COMMAND_REGISTRY.get(cmd_name)
    if not handler:
        raise SystemException(
            message=f"未知命令: {cmd_name}",
            project=project,
            payload={"task": task},
            action=f"分发任务到命令处理器",
            expected=f"命令 {cmd_name} 在 COMMAND_REGISTRY 中已注册",
            actual=f"COMMAND_REGISTRY 中找不到 {cmd_name}，可能未在 commands/__init__.py 注册",
        )

    return handler(**cmd_args)
```

---

## 4. 异常使用规范（极其重要）

> **通知机制：批量汇总模式。** 异常不会在触发时逐个发送飞书消息，而是由框架收集后统一发送。你只需要正确抛出异常，不需要关心通知逻辑。

### BusinessException — 业务异常，跳过继续

**什么时候用**：数据本身有问题（格式错误、不在范围内、业务规则不满足）

```python
raise BusinessException(
    message="简要描述问题",
    project="项目名称",          # 从 task 配置中获取
    context={                   # 诊断上下文（汇总到飞书卡片）
        "tracking_no": "xxx",
        "reason": "单号已过期",
    },
)
```

> 注意：`context` 中的内容会出现在飞书汇总通知的"跳过明细"中。

### SystemException — 系统异常，中断报工单

**什么时候用**：代码 Bug、外部服务故障、数据结构变更

```python
raise SystemException(
    message="简要描述报错",
    project="项目名称",
    payload={                   # 诊断上下文（写入 Linear 工单）
        "url": "https://...",
        "raw_response": "...",
    },
    action="正在做什么时出错",   # 必填！如"查询物流单号 HK001 的状态"
    expected="本来应该怎样",     # 必填！如"返回 JSON 响应"
    actual="实际发生了什么",     # 必填！如"HTTP 500 内部错误"
)
```

> **三要素必填**：`action` / `expected` / `actual` 是工单质量的核心。
> 不填会导致 Linear 工单信息不足，AI 修复时需要额外沟通。
> `actual` 可以省略（默认用 message 兜底），但 `action` 和 `expected` 必须填。

> 注意：SystemException 会自动创建 Linear 工单 + 中断后续任务 + 出现在飞书汇总通知的"异常明细"中。

### 兜底异常处理

在 `entry.py` 的外层 `except Exception` 中，框架会自动把未捕获的异常包装为 `SystemException`。
但这种自动包装的工单质量较低（缺少 action/expected），所以**业务模块内部应该主动捕获并抛出带上下文的异常**。

---

## 5. 影刀传给 Python 的任务格式

影刀通过 `project.json` 或动态生成的 JSON 文件传入任务列表：

```json
{
  "tasks": [
    {
      "command": "query_order",
      "args": {
        "tracking_no": "HK2025050001",
        "carrier": "SF"
      }
    },
    {
      "command": "query_order",
      "args": {
        "tracking_no": "HK2025050002"
      }
    }
  ]
}
```

每个 task 的字段：
- `command`（str）：对应 `COMMAND_REGISTRY` 中的函数名
- `args`（dict）：传递给函数的关键字参数
- `id`（int，可选）：任务序号，用于日志追踪

---

## 6. project.json 配置说明

此文件由影刀生成/维护，AI 只读：

```json
{
  "project": "项目名称",
  "feishu_webhook": "飞书机器人 Webhook URL（BusinessException 通知用）",
  "linear": {
    "api_key": "Linear API Key（SystemException 工单用）",
    "team_id": "Linear Team ID",
    "project_name": "Linear 项目名称（工单归集）",
    "project_id": "Linear 项目 ID（留空自动查找/创建）"
  }
}
```

---

## 7. 返回值规范

你的业务函数必须返回一个可序列化为 JSON 的字典：

```python
# 正确
return {"status": "delivered", "location": "深圳"}

# 错误（不能返回自定义对象）
return OrderStatus.DELIVERED  # 不可序列化
```

返回值会被 `entry.py` 收集到 `results` 数组中，最终写入 `runner_{run_id}.json` 供影刀读取。

---

## 8. 禁止事项

1. **不要引入 selenium/playwright/pyautogui** — 浏览器操作由影刀完成
2. **不要使用 `raise Exception()`** — 必须用 BusinessException 或 SystemException
3. **不要修改 `runner.py` / `notifier.py` / `config.py` / `git_controller.py`** — 框架文件
4. **不要在业务函数中做 I/O 写入** — 只返回字典，影刀负责持久化
5. **不要硬编码配置** — 从 `core.config` 导入或通过函数参数传入
