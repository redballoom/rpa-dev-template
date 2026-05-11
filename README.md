# 开发模板

RPA 项目开发模板，基于 Gemini 高阶 RPA 自愈自动化架构。

## 架构

```
开发模板/
├── git_controller.py    # Git 动态路由调度（影刀入口）
├── runner.py             # 业务热重载调度，影刀唯一入口
├── run.bat               # Windows 一键启动脚本
├── core/
│   ├── __init__.py
│   ├── entry.py          # 业务执行入口
│   ├── exceptions.py     # 异常路由分流器（L1 飞书 / L2 Linear + AI 分析）
│   ├── notifier.py       # 告警网关（飞书 L1 + Linear，含分支感知）
│   ├── ai_analyzer.py    # AI 崩溃分析（Volcengine Ark API）
│   └── config.py         # 敏感配置集中管理
├── commands/             # 可插拔业务命令模块（规划中）
├── tests/
│   └── test_exception_routing.py  # 异常路由全链路测试
├── data/                 # 运行数据（.gitignore 忽略）
├── .gitignore
└── requirements.txt
```

## 告警与工单路由

| 异常类型 | 动作 | 说明 |
|----------|------|------|
| `BusinessException` | 飞书 L1 黄牌 | 跳过当前任务，继续执行 |
| `SystemException` | Linear 工单 | 仅生产分支（main）触发，强制中断 |

## 分支策略

| 分支 | 用途 | 说明 |
|------|------|------|
| `main` | 生产环境 | 稳定版本 |
| `fix/bug-test` | 测试/调试 | 不创建 Linear 工单 |
| `fix/*` | Bug 修复 | AI 自动创建 + PR |
| `feat/*` | 功能开发 | 人类开发者使用 |

## 使用方式

### 影刀内调用

```
1. 设置变量 is_test = True/False
2. 调用 Python → git_controller.switch_git_env(is_test, repo_path)
3. 检查返回值 status
4. 调用 BAT → python runner.py --run_id %run_id% --repo_path D:/RPA_Project
5. 读取 runner_%run_id%.json，判断 status
```

### 本地测试

```bash
python tests/test_exception_routing.py   # 异常路由全链路测试
python core/entry.py                     # 业务逻辑测试
python git_controller.py                # Git 切换测试
```
