# 开发模板

RPA 项目开发模板，基于 Gemini 高阶 RPA 自愈自动化架构。

## 架构

```
PJ/开发模板/
├── git_controller.py    # Git 动态路由调度（影刀入口）
├── runner.py            # 业务热重载调度
├── core/
│   ├── __init__.py
│   ├── entry.py         # 业务执行入口
│   └── exceptions.py    # 异常路由分流器（L1 飞书 / L2 Linear）
├── commands/            # 独立 Python 命令脚本
├── tests/               # 单元测试
├── data/                # 运行数据（.gitignore 忽略）
├── .gitignore
└── requirements.txt
```

## 分支策略

| 分支 | 用途 | 说明 |
|------|------|------|
| `main` | 生产环境 | 稳定版本，只能通过 PR 合并 |
| `fix/*` | Bug 修复 | AI 自动创建 + PR |
| `feat/*` | 功能开发 | 人类开发者使用 |

## 使用方式

### 影刀内调用

```
1. 设置变量 is_test = True/False
2. 调用 Python → git_controller.switch_git_env(is_test, repo_path)
3. 检查返回值 status
4. 调用 Python → runner.execute_core_logic(repo_path, run_id)
```

### 本地测试

```bash
python git_controller.py           # 测试 Git 切换
python -m core.entry               # 测试业务逻辑
pytest tests/                      # 运行测试
```
