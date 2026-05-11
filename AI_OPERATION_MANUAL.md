# RPA 项目初始化 — AI 操作手册

> 版本: 1.1  
> 最后更新: 2026-05-09  
> 用途: AI 代理按此手册步骤，从模板自动创建新的 RPA 项目
> 关联文档: [人机协助流程](HUMAN_MACHINE_COLLAB.md) — 影刀/Python/AI 职责划分

---

## 前置条件 (Prerequisites)

AI 在执行本手册前，必须确认以下条件满足，任一不满足则报错终止：

| 条件 | 检查方式 | 不满足时 |
|------|----------|----------|
| `D:\CraftPJ\init_project.py` 存在 | 检查文件 | 报错"找不到初始化脚本" |
| `D:\CraftPJ\init_project.bat` 存在 | 检查文件 | 报错"找不到初始化脚本" |
| Git 可用 | `git --version` RC=0 | 报错"Git 未安装" |
| Python 可用 | `python --version` RC=0 | 报错"Python 未安装" |
| 目标项目名不为空 | 用户提供 | 报错"项目名不能为空" |
| 目标目录不存在 | 检查 `D:\CraftPJ\{项目名}` | 报错"目录已存在" |
| 网络可达 (GitHub) | `git ls-remote git@github.com:redballoom/rpa-dev-template.git` | 报错"模板仓库不可达" |

---

## 步骤 1：确认项目信息

向用户确认以下信息：

1. **项目名称**（必填）—— 用于项目目录名、Git commit 信息、PROJECT 变量
   - 例如：`物流项目`、`财务月报`、`订单同步`
   - 可使用中文，不要使用 `&` 符号
2. **GitHub 远程地址**（可选）—— 用于推送远程仓库
   - 例如：`git@github.com:redballoom/物流项目.git`
   - 如果不提供，仅有本地 Git 仓库，不配置远程
3. **是否需要推送到 GitHub**（可选，默认否）
   - 需要提供远程地址 + 确认要求推送

确认后进入下一步。如果用户只给了项目名，直接使用默认参数执行。

---

## 步骤 2：执行初始化脚本

### 方法 A：通过 BAT 执行

```cmd
D:\CraftPJ\init_project.bat {项目名}
```

### 方法 B：通过 Python 执行（推荐 AI 使用）

```cmd
python D:\CraftPJ\init_project.py --name {项目名}
```

如果有远程仓库且要推送：

```cmd
python D:\CraftPJ\init_project.py --name {项目名} --remote git@github.com:redballoom/{项目名}.git --push
```

### 初始化过程说明

脚本自动执行以下动作，AI 需监控每一步的 RC：

| 步骤 | 说明 | 预期结果 |
|------|------|----------|
| 1/4 | 克隆 `rpa-dev-template` | 目录创建成功 |
| 2/4 | 清除模板 Git 历史 + 改写 `run.bat` | run.bat PROJECT 已更新 |
| 3/4 | 初始化新 Git 仓库 + 首次 commit | 首次 commit 完成 |
| 4/4 | 配置远程仓库 + 推送（可选） | 成功或跳过 |

### 错误处理

| 失败步骤 | 处理方式 |
|----------|----------|
| 1/4 克隆失败 | 检查网络/GitHub SSH key，报错终止 |
| 2/4 任意失败 | 手动修正，若不可恢复则删除目录重试 |
| 3/4 Git 失败 | 检查是否是目录残留问题，删除后重试 |
| 4/4 推送失败 | 仅警告，不阻断（用户可后续手动推） |

---

## 步骤 3：验证项目可运行

**必须执行以下验证**，确保新项目能正常跑通。

### 3.1 检查关键文件

```bash
ls "D:\CraftPJ\{项目名}\"
```

必须包含以下文件：
- `run.bat` — BAT 入口
- `runner.py` — Python 调度器
- `core/` — 业务逻辑目录
- `.git/` — Git 仓库

缺失任一文件视为验证失败。

### 3.2 校验 run.bat 内容

```bash
cat "D:\CraftPJ\{项目名}\run.bat"
```

检查点：
- 第一行应为 `@echo off`
- 包含 `set REPO_PATH=%~dp0`
- 包含 `set PROJECT={项目名}`（值正确）
- 最后一行以 `runner.py` 结尾
- **不包含** `chcp` 命令
- **不包含** `&` 符号

### 3.3 运行一次测试

```bash
cd /d D:\CraftPJ\{项目名}
run.bat test_verify
```

期待结果：
- RC=0（或 RC=1 但输出了 JSON）
- 输出目录出现 `runner_{run_id}.json` 文件
- JSON 内容包含 `status` 字段

> 注意：`status` 值可能是 `success`（正常）、`fatal`（运行时错误）或 `warning`（业务跳过）。
> 关键是有 JSON 输出文件。查看 `status` 了解具体结果。

### 3.4 清理测试产物

```bash
del /q "D:\CraftPJ\{项目名}\runner_*.json" 2>nul
```

---

## 步骤 4：告知用户结果

向用户报告以下信息，格式可参考：

```
✅ 项目初始化完成！

项目路径: D:\CraftPJ\{项目名}
影刀命令: run.bat {CurrentRunID}
Git 仓库: 已初始化 (首次 commit 完成)
远程仓库: {已配置 / 未配置}
测试验证: {通过 / 失败}

使用方式:
  在影刀「运行或打开」指令中，填写:
    D:\CraftPJ\{项目名}\run.bat

  编写业务逻辑后，参考人机协助流程:
    HUMAN_MACHINE_COLLAB.md
```

---

## 附录 A：架构关键变更（P0/P1）

### ✅ P0 — 崩溃快照（Crash Snapshot）

当 `SystemException` 触发时，自动在 `crash_snapshots/` 目录生成 `crash_{RunID}.json` 文件。该文件包含完整的错误上下文，供 AI 自愈层读取。

**输出格式**（AI 直接读取）：
- error_type, message — 错误摘要
- traceback — 完整堆栈
- action / expected / actual — 业务上下文（触发动作、预期、实际）
- payload — 入参数据
- file / function / line — 代码定位
- project — 所属项目

### ✅ P0 — AI 崩溃分析（AI Crash Analysis）

当 `SystemException` 触发时，`_dump_snapshot()` 后自动调用 `core/ai_analyzer.analyze_crash()`：

- 调用 **Volcengine Ark API**（`chat/completions` 端点）
- 模型：`glm-4-7-251222`（可配置）
- 返回结构化分析：root_cause、suggested_fix、severity、category、priority、summary
- AI 结果嵌入 Linear 工单标题 + 描述
- 降级安全：API Key 缺失 / 超时 / 异常 → 静默跳过，不影响现有流程

### ✅ P0 — pending_fix 状态机

- 系统异常 + 成功创建 Linear 工单 → `status: "pending_fix"`
- 系统异常 + 工单创建失败（如测试环境无 API Key）→ `status: "failed"`
- 目的是让影刀能区分"需要等待修复"和"彻底失败"

### ✅ P1 — 文件锁（FileLock）

- 同一项目路径一次只能运行一个实例
- 第二个实例立即返回 `status: "locked"`，不需要等待
- 防止并发触发 Git 冲突

### ✅ P1 — Pytest 骨架

- `pytest.ini` 已配置，测试放在 `tests/` 目录
- 运行：`python -m pytest`

---

## 附录 B：提升说明

如果在验证过程中（步骤 3）遇到权限错误：

### 确认代码页

```cmd
chcp
```

正常应为 `65001`（UTF-8）。如果不是，不要强行修改，向用户报告异常。

### 中文路径支持

当前系统代码页已为 UTF-8 (65001)，BAT 文件应以 UTF-8 编码保存（无 BOM），不要使用 GBK 编码。

### 遇到 "python: can't open file" 错误

如果 Python 报告无法打开文件且中文路径显示为乱码：
- 检查 BAT 文件编码是否为 UTF-8
- 检查 `set REPO_PATH=%~dp0` 是否写正确
- 不要使用硬编码的中文路径

---

## 附录 C：手动修复 run.bat

如果 run.bat 内容有误，手动修复模板：

```python
# 标准 run.bat 模板 (UTF-8编码)
content = (
    '@echo off\r\n'
    '\r\n'
    'set RUN_ID=%~1\r\n'
    'set REPO_PATH=%~dp0\r\n'
    'set PYTHON=python\r\n'
    'set PROJECT={项目名}\r\n'
    '\r\n'
    '%PYTHON% "%REPO_PATH%runner.py" --run_id "%RUN_ID%" --repo_path "%REPO_PATH:~0,-1%" --project "%PROJECT%"\r\n'
)
with open(r'D:\CraftPJ\{项目名}\run.bat', 'w', encoding='utf-8') as f:
    f.write(content)
```

> **关键要点**:
> - `%~dp0` 末尾自带 `\`，所以 `%REPO_PATH%runner.py` 不要加 `\`
> - `%~dp0` 以 `\` 结尾，传参给 `--repo_path` 时用 `%REPO_PATH:~0,-1%` 去掉末尾 `\`（避免 `\"` 被 Windows 命令解析器当成转义）
> - 文件必须 UTF-8 编码（系统代码页 65001），不要用 GBK
> - 不要包含 `chcp 65001`

---

## 附录 D：从模板中删除的旧功能

以下功能已从核心流程中移除/简化：

| 功能 | 移除原因 | 替代方案 |
|------|----------|----------|
| `_force_crash` 测试标记 | 改用 `id=0` 触发 SystemException | `tasks=[{"id": 0, "name": "crash test"}]` |
| 独立 `diag.py` | P0 异常路由已覆盖诊断需求 | 查看 `crash_snapshots/` 下的快照 |
