"""
JEPA Planner — Predict Before Acting Engine
Core functions: encode_state, generate_paths, simulate, select_path, update_state, reflect
"""

import json, os, re
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TaskState:
    task: str = ""
    description: str = ""
    current_directory: str = ""
    existing_files: list = field(default_factory=list)
    constraints: list = field(default_factory=list)
    dependencies: dict = field(default_factory=dict)
    risk_points: list = field(default_factory=list)
    artifacts: dict = field(default_factory=dict)
    tools_available: list = field(default_factory=list)
    step_count: int = 0
    execution_history: list = field(default_factory=list)


@dataclass
class SimulationResult:
    path: list = field(default_factory=list)
    path_description: str = ""
    success_probability: float = 0.0
    risk_level: RiskLevel = RiskLevel.MEDIUM
    resource_cost: int = 0
    failure_points: list = field(default_factory=list)
    side_effects: list = field(default_factory=list)
    fallback_options: list = field(default_factory=list)
    reasoning: str = ""


def jepa_encode_state(task: str, context: Optional[dict] = None,
                      constraints: Optional[list] = None) -> TaskState:
    if context is None:
        context = {}
    if constraints is None:
        constraints = []
    state = TaskState(task=task, constraints=constraints, description=context.get('description', ''),
                      current_directory=context.get('cwd', '.'), existing_files=context.get('files', []),
                      tools_available=context.get('tools', []))
    
    text = (task + ' ' + state.description).lower()
    risk_patterns = {
        'network_io': ['download', 'upload', 'fetch', 'curl', 'api', 'http', '下载', '爬取', '网'],
        'destructive': ['delete', 'remove', 'rm', 'overwrite', 'format', '删除', '覆盖', '清除'],
        'external_dep': ['database', 'server', 'remote', 'service', 'docker', '数据库', '服务器'],
        'large_scale': ['batch', 'all', 'every', 'thousands', 'hundreds', '100+', '批量', '全部', '所有'],
        'encoding': ['encoding', 'unicode', 'charset', 'garbled', '编码', '乱码'],
        'permission': ['sudo', 'chmod', 'admin', 'permission', '权限'],
    }
    for risk_type, keywords in risk_patterns.items():
        if any(k in text for k in keywords):
            state.risk_points.append(risk_type)
    
    deps = {}
    if any(p in text for p in ['download', 'fetch', '下载', '爬取']):
        deps['download'] = ['storage_space', 'network']
    if any(p in text for p in ['rename', 'convert', '重命名', '转换']):
        deps['transform'] = ['download_complete']
    if any(p in text for p in ['upload', 'publish', '上传', '发布']):
        deps['publish'] = ['transform_complete']
    state.dependencies = deps
    
    state.step_count = max(1, len(deps) * 2 + sum(1 for i in ['batch', 'multiple', 'each', 'all', '批量', '多个', '每个', '全部']
                                                   if i in text) * 2)
    return state


def jepa_generate_paths(state: TaskState, N: int = 3) -> list:
    t = state.task.lower()
    if any(k in t for k in ['download', 'scrape', 'fetch', '爬取', '下载']):
        task_type = 'data_collection'
    elif any(k in t for k in ['convert', 'transform', '转换']):
        task_type = 'transformation'
    elif any(k in t for k in ['deploy', 'config', 'setup', '部署', '配置']):
        task_type = 'deployment'
    else:
        task_type = 'general'

    strategies = {
        'data_collection': [
            [{'step': 'analyze_sources'}, {'step': 'prepare_targets'}, {'step': 'collect_sequential'}, {'step': 'verify'}, {'step': 'finalize'}],
            [{'step': 'prepare'}, {'step': 'parallel_fetch'}, {'step': 'verify_retry'}, {'step': 'finalize'}],
            [{'step': 'scout'}, {'step': 'temp_staging'}, {'step': 'validate'}, {'step': 'move_and_rename'}, {'step': 'cleanup'}],
        ],
        'transformation': [
            [{'step': 'backup'}, {'step': 'test_single'}, {'step': 'batch_transform'}, {'step': 'verify'}],
            [{'step': 'dry_run'}, {'step': 'parallel_transform'}, {'step': 'spot_check'}],
            [{'step': 'validate_inputs'}, {'step': 'incremental_convert'}, {'step': 'generate_diff'}],
        ],
        'general': [
            [{'step': 'assess'}, {'step': 'plan_detailed'}, {'step': 'execute_step1'}, {'step': 'verify_step1'}, {'step': 'continue'}],
            [{'step': 'prototype'}, {'step': 'iterate'}, {'step': 'finalize'}],
            [{'step': 'parallel_prep'}, {'step': 'execute_phases'}, {'step': 'integration_test'}],
        ]
    }

    paths = []
    for n in range(N):
        path = strategies.get(task_type, strategies['general'])[n % 3].copy()
        if 'network_io' in state.risk_points:
            path.append({'step': 'retry_failed'})
        paths.append(path)
    return paths


def jepa_simulate(path: list, state: TaskState) -> SimulationResult:
    if not path:
        return SimulationResult(path=[], success_probability=0.0, risk_level=RiskLevel.CRITICAL)
    failure_points, side_effects, fallbacks = [], [], []
    for i, step in enumerate(path):
        s = step.get('step', '')
        a = step.get('action', s)
        action_lower = (s + ' ' + a).lower()
        failures = []
        if any(k in action_lower for k in ['download', 'fetch', 'curl', 'api']):
            failures.extend(['network_timeout', 'rate_limit'])
        if any(k in action_lower for k in ['write', 'save', 'create', 'mkdir', 'move']):
            failures.append('disk_space')
        if any(k in action_lower for k in ['delete', 'remove', 'overwrite']):
            failures.append('data_loss')
        if any(k in action_lower for k in ['convert', 'transform', 'rename', 'encode']):
            failures.append('format_error')
        if failures:
            failure_points.append({'step_index': i, 'step_name': s, 'risks': failures})
        if 'download' in action_lower:
            side_effects.append('increased_disk_usage')
        if 'delete' in action_lower or 'remove' in action_lower:
            side_effects.append('irreversible_data_loss_risk')
        if 'download' in action_lower or 'fetch' in action_lower:
            fallbacks.extend(['retry_with_backoff', 'use_mirror'])
        if 'delete' in action_lower:
            fallbacks.append('move_to_trash_instead')
        if 'parallel' in action_lower:
            fallbacks.append('fallback_to_sequential')
    prob = max(0.05, min(1.0, 0.95 - len(failure_points) * 0.08 -
                         (0.05 if any(r == 'network_io' for r in state.risk_points) else 0) -
                         (0.05 if any(r == 'destructive' for r in state.risk_points) else 0)))
    risk = RiskLevel.LOW
    if prob < 0.3:
        risk = RiskLevel.CRITICAL
    elif prob < 0.6:
        risk = RiskLevel.HIGH
    elif prob < 0.8:
        risk = RiskLevel.MEDIUM
    desc = ' → '.join(s.get('step', '?') for s in path)
    return SimulationResult(path=path, path_description=desc, success_probability=round(prob, 2),
                            risk_level=risk, resource_cost=len(path) + len(failure_points) * 2,
                            failure_points=failure_points, side_effects=list(set(side_effects)),
                            fallback_options=list(set(fallbacks)))


def jepa_select_path(simulations: list) -> dict:
    if not simulations:
        return {'selected': None, 'reason': 'No valid paths', 'all_scores': []}
    penalties = {RiskLevel.LOW: 0.0, RiskLevel.MEDIUM: 0.15, RiskLevel.HIGH: 0.3, RiskLevel.CRITICAL: 0.6}
    scored = []
    for i, sim in enumerate(simulations):
        score = sim.success_probability - penalties.get(sim.risk_level, 0.3) - min(sim.resource_cost / 20, 1) * 0.1
        scored.append({'path_index': i, 'score': round(score, 3),
                       'success_probability': sim.success_probability,
                       'risk_level': sim.risk_level.value, 'resource_cost': sim.resource_cost})
    scored.sort(key=lambda x: x['score'], reverse=True)
    return {'selected': simulations[scored[0]['path_index']].path,
            'reason': f"Path {scored[0]['path_index']+1}: success={scored[0]['success_probability']:.0%}, risk={scored[0]['risk_level']}",
            'all_scores': scored}


def jepa_update_state(state: TaskState, actual: dict, expected: dict,
                       threshold: float = 0.2) -> dict:
    deviation = 0.0
    for key in expected:
        if key in actual:
            e, a = expected[key], actual[key]
            if isinstance(e, (int, float)) and isinstance(a, (int, float)) and e != 0:
                deviation += abs((a - e) / e)
            elif isinstance(e, bool):
                deviation += 0.0 if e == a else 1.0
            elif isinstance(e, (list, tuple)) and e:
                deviation += abs(len(e) - len(a)) / max(len(e), 1)
    if expected:
        deviation /= max(len(expected), 1)
    if actual.get('errors'):
        deviation += 0.3
    deviation = min(1.0, deviation)
    needs_replan = deviation > threshold
    state.execution_history.append({'expected': expected, 'actual': actual, 'deviation': deviation, 'needs_replan': needs_replan})
    if actual.get('files_created'):
        state.artifacts.update({f"file_{i}": f for i, f in enumerate(actual['files_created'])})
    return {'deviation': round(deviation, 3), 'needs_replan': needs_replan, 'state': state.to_dict() if hasattr(state, 'to_dict') else {}}


def jepa_reflect(execution_log: list) -> dict:
    if not execution_log:
        return {'lessons': ['No data'], 'pattern_updates': []}
    completed = len(execution_log)
    failed = sum(1 for s in execution_log if s.get('status') == 'failed')
    replans = sum(1 for s in execution_log if s.get('needs_replan', False))
    lessons = [f"Completed {completed} steps, {failed} failures, {replans} replans"]
    pattern_updates = []
    if failed:
        errs = {}
        for s in execution_log:
            if s.get('errors'):
                for e in s['errors']:
                    t = e.split(':')[0] if ':' in e else e[:20]
                    errs[t] = errs.get(t, 0) + 1
        if errs:
            mc = max(errs, key=errs.get)
            lessons.append(f"Most common failure: {mc} ({errs[mc]}x)")
            pattern_updates.append(f"add_risk_check: {mc}")
    if replans:
        lessons.append(f"Re-planned {replans} times")
        pattern_updates.append("reduce_step_size: smaller steps reduce deviation")
    devs = [s.get('deviation', 0) for s in execution_log]
    if devs:
        avg = sum(devs) / len(devs)
        lessons.append(f"Avg deviation: {avg:.1%}")
        if avg > 0.3:
            pattern_updates.append("increase_estimation_accuracy")
    return {'lessons': lessons, 'pattern_updates': list(set(pattern_updates))}


def jepa_format_simulation_report(simulations: list, selected: dict) -> str:
    lines = ["## JEPA 推演报告", ""]
    for i, sim in enumerate(simulations):
        lines.append(f"### 路径 {i+1}: {sim.path_description[:60]}")
        lines.append(f"- 成功率: {sim.success_probability:.0%}")
        lines.append(f"- 风险等级: {sim.risk_level.value}")
        lines.append(f"- 预估工具调用: {sim.resource_cost}")
        if sim.failure_points:
            for f in sim.failure_points[:2]:
                lines.append(f"  - {f['step_name']}: {'; '.join(f['risks'][:2])}")
        lines.append("")
    if selected and selected.get('selected'):
        lines.append(f"### 选择\n→ {selected['reason']}")
    return '\n'.join(lines)


def jepa_format_task_context(cwd: str = None, files: list = None) -> dict:
    import os
    return {'cwd': cwd or os.getcwd(), 'files': files or [], 
            'tools': ['read_file', 'write_file', 'patch', 'terminal', 'search_files', 'execute_code', 'delegate_task']}


if __name__ == '__main__':
    import sys
    task = ' '.join(sys.argv[1:]) or "从网站下载100张图片并按主题分类"
    print(f"📋 任务: {task}")
    state = jepa_encode_state(task, {'cwd': '/home/kok/workspace'}, ['网络不稳定'])
    print(f"  步骤: {state.step_count}, 风险: {state.risk_points}")
    sim = jepa_simulate(jepa_generate_paths(state, 1), state)
    print(f"  模拟: 成功率={sim.success_probability:.0%}, 风险={sim.risk_level.value}")
