# 影刀与 Python 接口样例

> 用途：给影刀开发、Python 开发、AI 修复统一参考，避免对输入输出协议靠口头约定。  
> 说明：样例文件放在 [`docs/examples`](D:\CraftPJ\开发模板\docs\examples)。

## 1. 样例清单

### 输入样例

- `input_success.json`
- `input_business_warning.json`
- `input_retryable_error.json`
- `input_system_error.json`

### 输出样例

- `runner_success.json`
- `runner_business_warning.json`
- `runner_retryable_error.json`
- `runner_system_error.json`

## 2. 使用方式

### 影刀侧

- 设计新流程时，先参考输入样例组织 `input_{run_id}.json`
- 读取结果时，只按输出样例中的 `status` 和标准字段消费
- 不自行扩展“只在某个流程里有效”的私有状态

### Python / AI 侧

- 写新功能时，优先兼容这些输入样例
- 修复 bug 时，可直接基于这些样例补测试
- 如果协议发生升级，应先补样例再改实现

## 3. 协议维护规则

- 每新增一种重要状态或异常场景，至少补 1 组输入输出样例
- 生产问题修复后，如具备脱敏条件，应把失败样例转为文档样例或测试样例
- 样例中的路径、账号、项目名应保持脱敏
