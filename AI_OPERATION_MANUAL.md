# RPA 项目初始化 — AI 操作手册

> 版本: 2.2
> 最后更新: 2026-05-19
> 用途: Craft Agent 按此手册步骤，从模板自动创建新的 RPA 项目

---

## 快速初始化

```bash
# 方式 1: 使用独立的初始化脚本（推荐）
python D:\CraftPJ\init_project.py --name "物流项目"
python D:\CraftPJ\init_project.py --name "海外仓" --target "C:\Users\redballoon\Desktop\PJ"

# 方式 2: 使用 BAT 快捷方式
D:\CraftPJ\init_project.bat 物流项目

# 方式 3: 使用模板内脚本
python scripts/init_project.py --name "物流项目"
```

> `--name` 支持中文
> `--target` 指定输出目录（默认 `D:\CraftPJ`）
> `--remote` + `--push` 可选推送到 GitHub

---

## 前置条件

| 条件 | 检查方式 | 不满足时 |
|------|----------|----------|
| `D:\CraftPJ\init_project.py` 存在 | 检查文件 | 报错"找不到初始化脚本" |
| Git 可用 | `git --version` RC=0 | 报错"Git 未安装" |
| Python 可用 | `python --version` RC=0 | 报错"Python 未安装" |
| 目标项目名不为空 | 用户提供 | 报错"项目名不能为空" |
| 目标目录不存在 | 检查 | 报错"目录已存在" |
| 网络可达 (GitHub) | `git ls-remote git@github.com:redballoom/rpa-dev-template.git` | 报错"模板仓库不可达" |

---

## 初始化过程

初始化脚本自动执行以下动作，AI 需监控每一步的 RC：

| 步骤 | 说明 | 预期结果 |
|------|------|----------|
| 1/5 | 克隆 `rpa-dev-template` | 目录创建成功 |
| 2/5 | 改写 run.bat / project.json / README / CLAUDE.md | 项目名全部更新 |
| 3/5 | 初始化新 Git 仓库 + 首次 commit | 首次 commit 完成 |
| 4/5 | 配置远程仓库 + 推送（可选） | 成功或跳过 |
| 5/5 | pytest 验证 | 全部通过 |

---

## 验证

创建后必须运行验证：

```bash
cd /d D:\CraftPJ\{项目名}
python -m pytest tests/ -v
```

期待结果：全部测试通过（42 passed）。

---

## 手动修复 run.bat

如果 run.bat 内容有误：

```python
content = (
    '@echo off\r\n'
    '\r\n'
    'set RUN_ID=%~1\r\n'
    'set WORK_DIR=%~2\r\n'
    'set INPUT_FILE=%~3\r\n'
    'set REPO_PATH=%~dp0\r\n'
    'set PYTHON=python\r\n'
    'set PROJECT={项目名}\r\n'
    '\r\n'
    '%PYTHON% "%REPO_PATH%runner.py" --run_id "%RUN_ID%" --repo_path "%REPO_PATH:~0,-1%" --work_dir "%WORK_DIR%" --input_file "%INPUT_FILE%" --project "%PROJECT%"\r\n'
)
with open(r'D:\CraftPJ\{项目名}\run.bat', 'w', encoding='utf-8') as f:
    f.write(content)
```

> **关键要点**:
> - `%~dp0` 末尾自带 `\`，所以 `%REPO_PATH%runner.py` 不要加 `\`
> - `%~dp0` 以 `\` 结尾，传参给 `--repo_path` 时用 `%REPO_PATH:~0,-1%` 去掉末尾 `\`
> - 文件必须 UTF-8 编码（系统代码页 65001），不要用 GBK
> - 不要包含 `chcp 65001`
