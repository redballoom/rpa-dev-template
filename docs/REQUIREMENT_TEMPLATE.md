# Python 需求输入模板

> 用途：以后给 AI 写 Python 功能、修复逻辑、补测试时，统一按本模板提供输入。  
> 原则：没有“输入格式 / 输出格式 / 业务规则 / 异常规则 / 成功标准”，不要直接进入编码。

## 1. 标准模板

```text
需求标题：

业务背景：

业务目标：

影刀已完成：

Python 需要完成：

本次是否允许修改影刀流程：
- 否（默认）
- 是，允许修改范围：

输入数据格式：
- 文件类型：
- 路径来源：
- 字段说明：
- 示例：

输出数据格式：
- 输出文件或返回结构：
- 字段说明：
- 示例：

业务规则：
1.
2.
3.

异常规则：
- 哪些情况记 warning：
- 哪些情况返回 retryable_error：
- 哪些情况进入 pending_fix / failed：
- 必须带出的错误码或分类：

依赖与约束：
- 允许使用的第三方库：
- 不允许访问的系统：
- 性能要求：

成功标准：
1.
2.
3.

测试样例：
- 正常样例：
- 边界样例：
- 异常样例：

不允许做的事：
1.
2.
3.

验收命令：
- python -m pytest tests -q
- 本地复现命令：
```

## 2. 填写说明

### 2.1 业务目标

写清楚“这段 Python 最终要帮影刀解决什么问题”，不要只写“处理数据”或“修复 bug”。

推荐写法：

- 将影刀下载的订单 Excel 清洗为统一字段结构，供后续上传 ERP。
- 校验下载文件中的订单是否重复，并输出 warning 明细。
- 解析供应商 CSV，按业务规则计算结算金额。

### 2.2 影刀已完成

这里明确上游边界，防止 AI 误把影刀职责写回 Python。

示例：

- 已完成登录和订单列表导出。
- 已下载 `orders_2026-05-12.xlsx` 到项目目录。
- 已生成 `input_{run_id}.json` 并传入任务上下文。

### 2.3 Python 需要完成

只写 Python 该做的事，按可执行动作列出。

示例：

1. 读取 Excel 并校验列头。
2. 过滤取消订单。
3. 按店铺编码映射内部仓库。
4. 输出标准 JSON 结果。
5. 发现缺字段时返回 `DATA_INVALID`。

### 2.4 输入数据格式

这是最关键字段之一，至少要给：

- 输入文件类型
- 路径来源
- 核心字段
- 至少 1 个样例

示例：

```json
{
  "run_id": "ORDER_20260512_001",
  "project": "海外仓补货",
  "tasks": [
    {
      "id": "task-001",
      "name": "解析订单",
      "intent": "清洗订单数据",
      "rule_context": "跳过已取消订单",
      "payload": {
        "file_path": "data/orders_20260512.xlsx",
        "shop_id": "S001"
      }
    }
  ],
  "context": {
    "operator": "yingdao",
    "env": "prod",
    "source": "yingdao"
  }
}
```

### 2.5 输出数据格式

建议同时描述：

- Python 处理结果的业务数据
- `runner_{run_id}.json` 的预期状态

示例：

```json
{
  "status": "warning",
  "message": "部分订单被跳过",
  "data": {
    "run_id": "ORDER_20260512_001",
    "results": [],
    "warnings": [
      {
        "code": "ORDER_NOT_FOUND",
        "category": "business",
        "message": "订单不存在"
      }
    ],
    "errors": [],
    "retryable": false,
    "log_path": "logs/run_ORDER_20260512_001.log",
    "crash_snapshot_dir": ""
  }
}
```

### 2.6 业务规则

不要只写“按实际业务处理”，要写成 AI 可以实现和测试的判断条件。

推荐写法：

1. 取消状态订单直接跳过。
2. 金额为空时按 `DATA_INVALID` 记 warning。
3. 同订单号保留最新更新时间的一条记录。

### 2.7 异常规则

这是第二个最关键字段，至少明确：

- warning 条件
- retryable_error 条件
- pending_fix / failed 条件
- 错误码和异常分类

示例：

- 文件缺列头：`fatal`
- 订单金额为空：`warning` + `DATA_INVALID`
- 第三方 API 超时：`retryable_error` + `DEPENDENCY_FAILURE`
- 代码逻辑缺陷：`pending_fix` + `LOGIC_DEFECT`

## 3. 简版模板

适合小修复或小功能，但也不能省掉关键字段。

```text
业务目标：
影刀已完成：
Python 需要完成：
输入数据格式：
输出数据格式：
业务规则：
异常规则：
成功标准：
测试样例：
不允许做的事：
```

## 4. 示例：用于 AI 修复工单

```text
需求标题：修复订单金额为空时程序中断

业务目标：
当订单金额为空时，不中断整批任务，而是记录 warning 并继续处理。

影刀已完成：
已下载订单 Excel，并写出 input_ORDER_20260512_003.json。

Python 需要完成：
读取 Excel；金额为空时记 warning；输出 warning 到 runner json；补充回归测试。

输入数据格式：
Excel 文件，字段包含 order_id、amount、shop_id、status。

输出数据格式：
runner_{run_id}.json；当存在空金额但任务其余可继续时，status=warning。

业务规则：
1. 取消订单跳过。
2. amount 为空时不入 results。
3. 同 order_id 去重，保留最新记录。

异常规则：
- amount 为空：warning + DATA_INVALID
- 文件不存在：fatal
- 解析器代码报错：pending_fix

成功标准：
1. 程序不中断。
2. runner json 中记录 warning。
3. pytest 全绿。

测试样例：
- 正常订单 3 条
- 1 条空金额订单
- 1 条取消订单

不允许做的事：
1. 不修改影刀流程。
2. 不写死本地绝对路径。
3. 不跳过测试。
```
