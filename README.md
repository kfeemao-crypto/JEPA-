# JEPA Planner — 用户使用指南

## 简介

JEPA Planner 是一个受 Yann LeCun JEPA 架构启发的规划-执行框架，核心理念是 **"先预测后果再行动"**。

## 安装

### 方式 1: 直接使用（推荐）

Hermes Agent 会自动加载 skill。复杂任务时，会自动启用 JEPA 推演流程。

### 方式 2: 手动加载

```bash
hermes skill install jepa-planner
```

### 方式 3: Python 直接调用

```python
from hermes_tools import terminal, execute_code

# 使用 execute_code 导入 JEPA planner
result = execute_code("""
import sys
sys.path.insert(0, '/home/kok/.hermes/skills/software-development/jepa-planner/scripts')
from jepa_planner import jepa_encode_state, jepa_simulate, jepa_select_path

state = jepa_encode_state(task, context, constraints)
paths = jepa_generate_paths(state)
sims = [jepa_simulate(p, state) for p in paths]
best = jepa_select_path(sims)
print(best['reason'])
""")
```

## 使用场景

### ✅ 推荐使用
- 批量下载文件
- 多步骤数据处理
- 跨平台文件操作
- API 数据采集
- 需要"先 A 再 B 再 C"依赖链的任务

### ❌ 不需要
- 单步查询
- 纯对话
- 简单的文件读写

## 如何验证 JEPA Planner 在起作用

在执行复杂任务时，你会看到类似这样的输出：

```
【JEPA Phase 1: 状态编码】
步骤数预估: 8
风险点: network_io, encoding, large_scale

【JEPA Phase 2: 推演】
路径 1: 安全优先 — 成功率 92%, 风险 low
路径 2: 效率优先 — 成功率 70%, 风险 medium
→ 选择路径 1

【JEPA Phase 3: 执行 & 验证】
Step 3/8: 下载第1批.png
  预期: 20张
  实际: 18张
  偏差: 10% → 在阈值内，继续
```

## 文件架构

```
~/.hermes/skills/software-development/jepa-planner/
├── SKILL.md                        # 完整技能文档（入口）
├── scripts/
│   └── jepa_planner.py             # Python 推演引擎
├── tests/
│   └── test_jepa_planner.py        # 测试套件
└── references/
    ├── jepa-phases.md              # 详细 Phase 模板
    └── consequence-patterns.md     # 后果模式库
```

## 运行测试

```bash
cd ~/.hermes/skills/software-development/jepa-planner
python tests/test_jepa_planner.py
```

## OpenClaw 版本

OpenClaw 的 JEPA Planner 以 SOUL.md 形式提供：
`jepa-planner/OPENCLAW_SOUL.md`

将内容合并到 `~/.openclaw-standalone/workspace/SOUL.md` 即可启用。
