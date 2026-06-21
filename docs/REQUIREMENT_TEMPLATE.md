# AI 业务开发需求模板

给 AI 开发 Code 项目业务代码时，建议按以下格式描述需求。

## 背景

- 项目名称：
- 影刀已经完成的动作：
- Python 需要完成的动作：
- 是否允许修改影刀流程：默认否

## 输入

`input_{run_id}.json` 示例：

```json
{
  "project": "",
  "tasks": [
    {
      "id": "",
      "name": "",
      "type": "",
      "payload": {}
    }
  ],
  "context": {
    "operator": "yingdao",
    "env": "test",
    "source": "shadowbot",
    "app_name": ""
  }
}
```

说明：

- `payload` 中每个字段的含义：
- `data/input/` 中会有哪些文件：
- 文件格式、字段名、编码、分隔符：
- 是否需要设置 `context.fail_fast=false` 以支持独立批任务继续执行：

## 输出

- 业务输出文件路径：
- 输出格式：
- 关键字段：
- 空数据、重复数据、异常数据处理规则：

## 状态与异常

- 何时返回 `success`：
- 何时返回 `warning`：
- 何时返回 `retryable_error`：
- 何时返回 `pending_fix` 或 `fatal`：

## 验收

- 本地验证命令：
- 预期输出文件：
- 预期 `runner_{run_id}.json.status`：
- 需要补充的测试：
