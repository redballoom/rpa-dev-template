# 体系审计报告

审计日期：2026-06-04
审计范围：开发模板（全部代码、文档、测试）+ rpa-contract-first Skill
测试状态：50/50 全部通过，框架骨架健康

---

## 一、开发模板缺陷

### 1.1 run_id 来源口径矛盾 [实际 Bug]

- 位置：`runner.py` 第 154 行
- 现象：文档（README、SHADOWBOT_INPUT_CONTRACT）明确写"run_id 不要求写入 input.json，由影刀通过命令行传入"。但 `runner.py` 有 `run_id = input_data.get("run_id", run_id)`，如果 input.json 里传了 run_id，会静默覆盖命令行值。`docs/examples/input_success.json` 里实际包含 `"run_id": "EXAMPLE_SUCCESS_001"`。
- 后果：影刀传入的 run_id 可能不是最终使用的 run_id，导致 `runner_{run_id}.json` 文件名与实际内容对不上。
- 建议：选定一个口径——要么文档承认可以从 input.json 读（并更新 README），要么代码去掉 `input_data.get("run_id", run_id)` 这行，并修正示例文件。

### 1.2 AI 分析器默认模型 ID 冲突 [实际 Bug]

- 位置：`config.py` 第 77 行 vs `project.template.json` 第 15 行
- 现象：`config.py` 硬编码默认值 `"ep-20260509143138-njpgt"`（火山引擎 Ark 端点格式），`project.template.json` 写 `"glm-4-7-251222"`（智谱 GLM 格式）。配置加载是 template → project.json 深度合并，用户只填 API key 不改 model 时，会用 GLM 模型 ID 调 Ark API。
- 后果：AI 分析请求大概率返回模型不存在错误。ai_analyzer 做了 graceful degradation 不阻断主流程，但 AI 分析静默失效。
- 建议：统一 model ID 默认值，或在 config.py 里加一条 model 和 API URL 的兼容性校验。

### 1.3 飞书通知空 Webhook 时的无效请求 [实际 Bug]

- 位置：`notifier.py` `_feishu_post()` 函数
- 现象：`FEISHU_WEBHOOK` 为空字符串时，仍执行 `requests.post("", json=data, timeout=10)`，触发 `MissingSchema` 异常后 catch 打印 `[notifier] 飞书请求异常`。
- 后果：每次运行都打一条让人困惑的错误日志，不影响主流程但污染日志。
- 建议：在 `_feishu_post` 开头加 `if not FEISHU_WEBHOOK: return True` 判空。

### 1.4 生产分支判断硬编码 [潜在 Bug]

- 位置：`notifier.py` `_is_production_env()` 函数
- 现象：`return _get_current_branch(repo_path) == "main"` 只认 `main` 分支。
- 后果：如果生产分支叫 `master`、`release` 或其他名字，Linear 工单会被错误跳过。生产环境出事时不自动创建工单。
- 建议：将生产分支名列表放入 `project.json` 配置项，或在 `config.py` 中定义 `PRODUCTION_BRANCHES` 列表。

### 1.5 .gitignore 缺少测试缓存条目 [已修复]

- 位置：项目根目录 `.gitignore`
- 现象：`.gitignore` 已覆盖运行产物（`runner_*.json`、`logs/`、`crash_snapshots/`、`data/`）、`project.json`、`.runner.lock`、Python 缓存和 IDE 文件。但缺少 `.pytest_cache/`、`.coverage`、`htmlcov/` 三个测试缓存路径。
- 修复状态：已补充。

### 1.6 handler 组织方式不一致 [文档/代码不匹配]

- 位置：`core/entry.py`
- 现象：`calc_summary` 是 entry.py 内的私有函数 `_process_calc_summary`，`filter_records` 是独立文件 `core/handlers/record_filter.py`。处理器实现规范说"真实业务 handler 放入 `core/handlers/`"，但模板自带两个示例用了两种方式。
- 后果：新接入业务时 AI 或开发者可能选择错误的组织方式。
- 建议：在处理器实现规范中明确说明"小需求可以在 entry.py 内部，中大型需求应拆到 handlers/ 目录"的判断标准，或将 calc_summary 也移到 handlers/ 保持一致。

### 1.7 运行幂等性缺失 [数据风险]

- 位置：`runner.py` `execute()` 函数
- 现象：同一 run_id 跑两次时，`runner_{run_id}.json`、日志、crash snapshot 都会静默覆盖，无标记说明"本次覆盖上次"。
- 后果：retryable_error 重试时如果没换 run_id，排障时看到的日志可能是第二次运行的而非出问题那次的。
- 建议：写入结果文件时检查是否已存在同名文件，如存在则在结果中追加 `"previous_run_overwritten": true` 标记，或将旧文件归档。

### 1.8 异常语义灰色地带 [设计缺陷]

- 位置：`core/handlers/record_filter.py` 第 44-55 行
- 现象：input_file 不存在时抛 `SystemException`（exc_category=ENVIRONMENT_ISSUE），状态码 `pending_fix`。但文件不存在常是影刀下载失败造成的，Python 修不了，需要影刀重跑。
- 后果：修复流程文档里 AI 修复步骤和实际情况不匹配——AI 拿到 `pending_fix` 去改 Python 代码，但实际问题是影刀侧的。
- 建议：在异常体系中增加一个子分类或标记字段（如 `"fix_target": "shadowbot"` vs `"fix_target": "python"`），让修复流程能区分"Python 能修的"和"必须影刀重跑的"。

### 1.9 _process_single_task 混合真实路由和模板演示 [代码组织]

- 位置：`core/entry.py` `_process_single_task()` 函数
- 现象：该函数同时包含 `calc_summary`（真实 handler）、`filter_records`（真实 handler）和 `template_demo`（纯演示用异常模拟，靠 task id 数值触发不同异常）。
- 后果：接手时难以分清哪些是真实业务、哪些是演示代码。
- 建议：在代码注释中明确标注 `template_demo` 段为"仅用于模板状态码演示，接入真实业务后可删除"，或在第一个真实业务接入时将 template_demo 逻辑剥离。

### 1.10 配置模块加载时机问题 [边缘场景]

- 位置：`core/config.py` 模块级语句
- 现象：`_cfg = _load_merged_config()` 在 import 时执行。运行时 `project.json` 被修改后，需要 `importlib.reload(core.config)` 才能拿到新值。`runner.py` 对 `entry.py` 做了 reload，但没有对 `config.py` 做。
- 后果：正常场景不受影响（每次 run.bat 都是新进程），但如果未来嵌入长驻进程使用会出问题。
- 建议：当前不需要修，但在 config.py 头部注释中说明"配置在 import 时加载，长驻进程需手动 reload"。

### 1.11 三份契约模板存在维护漂移风险 [文档架构]

- 位置：`docs/任务设计模板.md`、`docs/REQUIREMENT_TEMPLATE.md`、`SKILL.md` 的 Contract Output Format
- 现象：三处各定义了相似但不完全相同的契约字段结构。
- 后果：随时间推移，三处定义的字段会逐渐漂移，审查时不知道以哪个为准。Spec 里也提到了此风险。
- 建议：选定 `docs/任务设计模板.md` 为唯一规范版，`REQUIREMENT_TEMPLATE.md` 和 `SKILL.md` 中的契约格式引用它（"按 docs/任务设计模板.md 输出"），不再各自重复定义字段。

---

## 二、Skill 工作流盲区

### 2.1 没有"轻量模式" [流程成本]

- 现象：Skill 固定走 11 步工作流。对于"给已有 handler 加一个 payload 字段"这类小改动，走完全流程成本偏高。Spec 里说"小业务允许生成轻量契约"，但 Skill 没实现这个分支。
- 后果：用户面对小任务时倾向于跳过 Skill，导致 Skill 使用率下降。
- 建议：在 Workflow 开头加一步判断——如果是对已有 type 的 payload 字段增删改，走 4 步轻量流程（确认变更 → 更新 payload 表 → 更新示例 input.json → 更新测试）。

### 2.2 没有"增强已有业务"变体 [场景缺失]

- 现象：Skill 覆盖了"新建业务"（主流程）和"故障修复"（Repair Loop Variant），但"修改/增强已有 handler"没有对应流程。
- 后果：日常工作中最常见的第三种场景（修改已有 handler）缺少指导。
- 建议：增加 "Enhancement Variant"，流程为：读现有契约和 handler → 识别变更点 → 评估向后兼容性 → 产出变更契约 → 用户确认 → 实现。

### 2.3 契约确认后没有持久化锚点 [上下文风险]

- 现象：Skill 说"Present the contract and wait for user approval"，但确认后契约只存在于对话上下文里。
- 后果：对话过长被截断、或换一个会话继续实现时，AI 找不到之前确认的契约原文。
- 建议：在 "Handoff To Implementation" 步骤中增加"将确认后的契约写入 `docs/superpowers/plans/{date}-{task_type}-contract.md`"。

### 2.4 不支持"一次需求涉及多个 type" [流程限制]

- 现象：一个业务需求可能需要新增 3 种 `tasks[].type`，但 Skill 按单个 type 设计流程。
- 后果：需要走三遍完整流程，效率低。
- 建议：在步骤 4-5 中支持"批量 type 设计"——先列出所有需要的 type 和各自的 payload，再逐个细化。契约输出格式支持多任务节。

### 2.5 契约输出格式与模板文档字段不一致 [漂移已发生]

- 现象：SKILL.md 的 Contract Output Format 有"业务步骤"和"验收"节，但没有"是否允许修改影刀流程"和"Python 输出是否需要影刀读取业务文件"这两个 `docs/任务设计模板.md` 中存在的字段。
- 后果：Skill 产出的契约缺少模板要求的部分信息。
- 建议：SKILL.md 的契约格式直接引用 `docs/任务设计模板.md`，或在 SKILL.md 中补全缺失字段。

---

## 三、跨 Agent 协作注意事项

### 3.1 AGENTS.md 是唯一跨 agent 约束文件

不同 AI 工具读取约定文件的习惯不同：QoderWork 自动读 `AGENTS.md`，Cursor 读 `.cursorrules`，Claude Code 读 `CLAUDE.md`。当前只有 `AGENTS.md`，其他工具可能不读。

建议：为不同工具放一份对应文件（内容可以相同，文件名匹配工具约定），或使用 symlink。

### 3.2 其他 agent 没有 Skill 的"硬门"保护

Skill 的 Hard Gate 确保"不批准契约就不写代码"。其他 agent 只能靠 AGENTS.md 的文档约束，agent 可以选择不读就直接写。

建议：在 AGENTS.md 开头加一条硬规则声明，例如："DO NOT write handler code before reading the contract docs listed in Section 1 and confirming the input/output contract with the user."

### 3.3 推荐的跨 agent 分工方式

在当前 QoderWork 里用 Skill 完成上半段（理解需求 → 设计契约 → 用户审批），把确认后的契约文件写入项目内，然后让任何 agent 拿着这份契约做下半段（实现 handler → 补测试 → 更新文档）。Skill 保障对话质量，AGENTS.md 保障代码质量，两者各管一段。

---

## 四、优先级排序

### P0 — 立即修（安全 / 实际 Bug）

| 编号 | 问题 | 修复成本 | 状态 |
|------|------|----------|------|
| 1.5 | .gitignore 缺少测试缓存条目 | 3 行 | ✅ 已修复 |
| 1.1 | run_id 来源口径统一 | 1-2 行代码 + 文档对齐 | 待修 |
| 1.3 | 飞书空 webhook 判空 | 1 行代码 | 待修 |
| 1.2 | AI model ID 默认值统一 | 1 行代码 | 待修 |

### P1 — 接入第一个真实业务前修

| 编号 | 问题 | 修复成本 |
|------|------|----------|
| 1.11 | 三份契约模板归一化 | 文档重构 |
| 2.1 | Skill 增加轻量模式 | Skill 文档补充 |
| 2.2 | Skill 增加增强已有业务变体 | Skill 文档补充 |
| 2.3 | 契约确认后写入文件 | Skill 流程 + 目录约定 |
| 1.4 | 生产分支配置化 | 3-5 行代码 |
| 1.6 | handler 组织方式统一 | 文档说明或代码迁移 |

### P2 — 按需处理

| 编号 | 问题 | 修复成本 |
|------|------|----------|
| 1.7 | 运行幂等性标记 | 5-10 行代码 |
| 1.8 | 异常语义细分 fix_target | 异常类 + entry.py + 文档 |
| 1.9 | template_demo 代码剥离 | 代码重构 |
| 2.4 | 多 type 批量契约 | Skill 流程补充 |
| 2.5 | Skill 契约格式与模板对齐 | 文档对齐 |
| 1.10 | 配置加载时机文档化 | 注释补充 |
| — | data/logs 清理策略 | 脚本 + 文档 |
| — | payload schema version 策略 | 协议设计 |
