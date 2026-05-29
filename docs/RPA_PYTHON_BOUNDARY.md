# RPA / Python / AI 职责边界

本模板采用三层协作：

1. 影刀 RPA 负责页面操作、文件下载上传、账号登录、人工确认、生成 `input.json`、调度 `run.bat`。
2. Python Code 项目负责读取业务输入、处理数据、写业务输出、输出 `runner_{run_id}.json`、记录日志和异常快照。
3. AI 负责在 Code 项目内实现和维护 Python 业务逻辑、测试和文档。

## 影刀负责

- 页面点击、输入、下载、上传、截图。
- 登录、验证码、弹窗、人工确认。
- 准备业务输入文件到 `data/input/`。
- 写入项目根目录的 `input.json`。
- 调用 `run.bat` 或 `runner.py`。
- 读取 `runner_{run_id}.json` 并按 `status` 分支。

## Python 负责

- 可选读取 `input.json`。
- 解析 `payload`。
- 处理 Excel、CSV、JSON、文本、文件汇总、字段映射、规则判断。
- 把业务结果写入 `data/output/`。
- 输出 `runner_{run_id}.json`。
- 写入 `logs/` 和 `crash_snapshots/`。

## AI 负责

- 根据需求实现 Python 业务模块。
- 维护 `payload` 协议示例。
- 补充测试和文档。
- 根据 `runner_{run_id}.json`、日志和快照修复问题。

## AI 默认不负责

- 未经明确要求修改影刀 UI 流程。
- 在生产运行时切换 Git 分支。
- 写入真实密钥、生产账号或个人绝对路径。
- 跳过验证直接宣称修复完成。

## 判断规则

需要页面状态或人工交互的动作放在影刀。  
能通过结构化输入输出稳定复现、需要测试和复用的逻辑放在 Python。  
业务规则变化时优先改 Python 代码和 `payload` 约定，不把复杂判断塞回影刀流程。
