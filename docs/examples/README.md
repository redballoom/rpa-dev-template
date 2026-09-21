# 示例说明

可直接运行：

- `input_calc_summary.json`：正式的最小业务示例，路由到 `calc_summary`。
- `input_success.json`、`input_business_warning.json`、`input_retryable_error.json`、`input_system_error.json`：使用 `template_demo` 验证状态协议，只用于模板测试，不应复制为真实业务 handler。

配置与证据：

- `project.dashscope.example.json`：可选 AI 集成配置示例，复制到本地 `project.json` 后再填写真实密钥。
- `evidence_summary_success.json`：当前 Evidence Schema 2 的脱敏成功样例。

需要展示尚未实现的业务 payload 时，应在需求文档中使用代码块并明确标注“契约草案”；不要命名为 `input_*.json`，避免被误认为可运行样例。
