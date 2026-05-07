---
name: jepa-planner
description: "JEPA-inspired planning framework: predict before acting. Multi-step consequence simulation, path search, and self-correcting execution for complex tasks."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [planning, jepa, world-model, orchestration, multi-step, reliability]
    related_skills: [writing-plans, subagent-driven-development, systematic-debugging, test-driven-development]
---

# JEPA Planner: Predict Before Acting

## Overview

JEPA Planner 受 Yann LeCun 的 JEPA（Joint Embedding Predictive Architecture）架构启发，将 **"先预测后果再行动"** 的核心思想嵌入到 Hermes Agent 的执行流程中。

### 核心问题

传统 LLM Agent 的执行是**开环的**：
```
规划 → 执行 Step 1 → 执行 Step 2 → ... → 遇到错误 → 补救
                                                  ↑
                                          （崩溃才知错了）
```

这种模式在面对 5+ 步骤的复杂任务时，中间步骤的微小偏差会被累积放大，最终导致"路易十五的诅咒"——**无法预判自己行动的后果**。

### JEPA Planner 的解决思路

```
传统模式（开环）：
  规划 → 执行 → 盲 → 执行 → 盲 → ... → 崩溃

JEPA 模式（带推演）：
  编码当前状态 → 推演 N 条路径的后果 → 筛选 → 执行一步 → 
  反馈 → 更新状态表征 → 重新推演 → 继续
```

### 架构映射

| JEPA 组件 | Hermes 中的对应 |
|-----------|----------------|
| **编码器 (Encoder)** | `jepa_encode_state()` — 将当前上下文编码为结构化状态表征 |
| **预测器 (Predictor)** | `jepa_simulate()` — 在表征空间推演每条路径的后果 |
| **规划器 (Planner)** | `jepa_select_path()` — 根据推演结果选择最优路径 |
| **损失函数** | 预期成功率 / 资源消耗 / 风险评分 |
| **世界模型** | LLM 自身的推理能力 + 工具调用经验 |

---

## When to Use

**必须使用**当任务满足以下任意条件：
- 步骤数 ≥ 5
- 包含破坏性操作（删除、覆盖、格式化）
- 涉及外部资源（数据库、API、远程服务器）
- 依赖链复杂（步骤 B 的成功依赖于步骤 A 的输出）
- 错误恢复成本高

**可以跳过**当：
- 单步任务（查询、读取）
- 确定性任务（简单转换）
- 用户明确要求"直接执行"

---

## 执行流程

```
┌─────────────────────────────────────────────────────────┐
│                    任务输入                              │
└────────────────────┬────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Phase 1: 状态编码 & 路径生成                            │
│  ├─ jepa_encode_state(task, context, constraints)       │
│  └─ jepa_generate_paths(state, N=3)                     │
└────────────────────┬────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Phase 2: 推演 & 路径筛选                                │
│  ├─ jepa_simulate(path, state) → 后果评估                │
│  ├─ 对每路径评估: 成功率/资源/风险/副作用                 │
│  └─ jepa_select_path(ranked_paths)                     │
└────────────────────┬────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Phase 3: 按步执行 & 状态跟踪                             │
│  ├─ 执行规划的第一步或一组                               │
│  ├─ jepa_update_state(实际结果 vs 预期)                  │
│  └─ 偏差 > 阈值 → 回退到 Phase 2 重新推演                │
└────────────────────┬────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Phase 4: 验证 & 总结                                   │
│  ├─ 逐步骤验证结果                                      │
│  ├─ jepa_reflect(execution_log)                         │
│  └─ 更新世界模型（经验回放）                              │
└─────────────────────────────────────────────────────────┘
```

## Core Functions

```python
jepa_encode_state(task, context, constraints) → TaskState
jepa_generate_paths(state, N=3) → list[paths]
jepa_simulate(path, state) → SimulationResult
jepa_select_path(simulations) → dict(selected, reason)
jepa_update_state(state, actual, expected) → dict(deviation, needs_replan)
jepa_reflect(execution_log) → dict(lessons, pattern_updates)
```

### Full Example

```python
import sys, os
sys.path.insert(0, os.path.expanduser('~/.hermes/skills/software-development/jepa-planner/scripts'))
from jepa_planner import *

state = jepa_encode_state(
    task="从网站下载100张图片并按主题分类",
    context=jepa_format_task_context(),
    constraints=["网络不稳定"]
)
paths = jepa_generate_paths(state, N=3)
sims = [jepa_simulate(p, state) for p in paths]
best = jepa_select_path(sims)
report = jepa_format_simulation_report(sims, best)
```

---

## Prompt Template (Manual Mode)

### Phase 1
```markdown
## JEPA Phase 1: 状态编码
任务: {task} | 目录: {cwd} | 约束: {constraints}
依赖链: step1→step2→... | 风险点: [网络,文件,编码,批量]
```

### Phase 2
```markdown
## JEPA Phase 2: 推演
路径A(安全): {steps}; 成功率X%; 风险Y
路径B(效率): {steps}; 成功率X%; 风险Y
选择: 路径A — 原因: ...
```

### Phase 3
```markdown
## JEPA Phase 3: 验证
步骤:{name} | 预期:X | 实际:Y | 偏差:Z%
决策: 继续/重试/回退
```

### Phase 4
```markdown
## JEPA Phase 4: 反思
完成度:X% | 教训:... | 改进:...
```

---

## 仓库结构

```
JEPA-/
├── hermes/                    # Hermes Skill
│   ├── JEPA-PLANNER.md        # 完整技能文档（本文件）
│   ├── scripts/
│   │   └── jepa_planner.py    # Python 推演引擎
│   ├── tests/
│   │   └── test_jepa_planner.py # 测试套件 (11/11 ✅)
│   └── references/
│       ├── jepa-phases.md     # Phase prompt 模板
│       └── consequence-patterns.md # 11种后果模式
├── openclaw/
│   └── SOUL.md                # OpenClaw 小黑 agent 设定
└── README.md                  # 本文件
```

## 原则

1. **先推演，再执行** — 破坏性操作前必须推演
2. **偏差即信号** — 实际≠预期是学习信号
3. **路径多样性** — 至少 3 条备选
4. **低成本回退** — 每步后检查偏差
5. **经验积累** — 每次执行后反思
