# RPA 项目初始化 - AI 操作手册

> 版本: 1.0  
> 最后更新: 2026-05-08  
> 用途: AI 代理按此手册步骤，从模板自动创建新的 RPA 项目

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

```cmd
dir /b D:\CraftPJ\{项目名}\
```

必须包含以下文件：
- `run.bat` — BAT 入口
- `runner.py` — Python 调度器
- `core/` — 业务逻辑目录
- `.git/` — Git 仓库

缺失任一文件视为验证失败。

### 3.2 校验 run.bat 内容

```cmd
type D:\CraftPJ\{项目名}\run.bat
```

检查点：
- 第一行应为 `@echo off`
- 包含 `set REPO_PATH=%~dp0`
- 包含 `set PROJECT={项目名}`（值正确）
- 最后一行以 `runner.py` 结尾
- **不包含** `chcp` 命令
- **不包含** `&` 符号

### 3.3 运行一次测试

```cmd
cd /d D:\CraftPJ\{项目名}
run.bat test_verify
```

期待结果：
- RC=0（或 RC=1 但输出了 JSON）
- 输出目录出现 `runner_{run_id}.json` 文件
- JSON 内容包含 `status` 字段

> 注意：`status` 值可能是 `fatal`（测试用例故意抛出的异常），这属于**正常**。关键是有 JSON 输出文件。

### 3.4 清理测试产物

```cmd
del /q D:\CraftPJ\{项目名}\runner_*.json 2>nul
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

  在 runner.py 的 execute() 函数中编写业务逻辑。
```

---

## 附录 A：提权说明

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

## 附录 B：手动修复 run.bat

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
