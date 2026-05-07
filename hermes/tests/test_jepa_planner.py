import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/scripts')
from jepa_planner import *

def test_encode_state():
    state = jepa_encode_state("下载100张图片并重命名", {'cwd': '/test'}, ['磁盘空间小'])
    assert len(state.risk_points) > 0
    assert state.step_count >= 2
    print(f"  ✓ encode_state: risks={state.risk_points}")

def test_generate_paths():
    state = jepa_encode_state("从网站下载数据", {}, [])
    paths = jepa_generate_paths(state, 3)
    assert len(paths) > 0
    print(f"  ✓ generate_paths: {len(paths)} path(s)")

def test_simulate():
    state = jepa_encode_state("下载后删除临时目录", {}, [])
    path = [{'step': 'download'}, {'step': 'delete_temp'}]
    sim = jepa_simulate(path, state)
    assert sim.success_probability < 1.0
    assert any('delete' in f.get('step_name', '') for f in sim.failure_points)
    print(f"  ✓ simulate: prob={sim.success_probability:.0%}, failures={len(sim.failure_points)}")

def test_select_path():
    state = jepa_encode_state("test", {}, [])
    p1 = [{'step': 'safe_approach'}]
    p2 = [{'step': 'risky_approach'}]
    sims = [jepa_simulate(p1, state), jepa_simulate(p2, state)]
    result = jepa_select_path(sims)
    assert result['selected'] is not None
    print(f"  ✓ select_path: {result['reason']}")

def test_update_state():
    state = jepa_encode_state("download 3 files", {}, [])
    r = jepa_update_state(state, {'files_created': ['a.jpg'], 'errors': ['timeout']},
                           {'files_created': ['a.jpg', 'b.jpg', 'c.jpg']})
    assert r['deviation'] > 0.1
    print(f"  ✓ update_state: deviation={r['deviation']:.2f}, replan={r['needs_replan']}")

def test_reflect():
    log = [{'status': 'success', 'deviation': 0.05},
           {'status': 'failed', 'deviation': 0.6, 'errors': ['timeout']}]
    r = jepa_reflect(log)
    assert len(r['lessons']) > 0
    print(f"  ✓ reflect: {len(r['lessons'])} lessons, {len(r['pattern_updates'])} patterns")

def test_end_to_end():
    task = "从网站下载提示词图片并按主题分类存储"
    state = jepa_encode_state(task, {'cwd': '/data'}, ['无API', '网络慢'])
    paths = jepa_generate_paths(state, 2)
    sims = [jepa_simulate(p, state) for p in paths]
    best = jepa_select_path(sims)
    assert best['selected'] is not None
    report = jepa_format_simulation_report(sims, best)
    assert '推演报告' in report
    print(f"  ✓ end_to_end: {best['reason']}")

if __name__ == '__main__':
    tests = [test_encode_state, test_generate_paths, test_simulate,
             test_select_path, test_update_state, test_reflect, test_end_to_end]
    passed = sum(1 for t in tests if (t(), True)[1])
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"  ✗ {t.__name__}: {e}")
    print(f"\n结果: {passed}/{len(tests)} 通过")
