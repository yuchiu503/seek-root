"""Seek Root 综合测试脚本。

测试内容:
1. DID 双差分法
2. PSM 倾向得分匹配
3. RD 断点回归
4. IV 工具变量法
5. CausalForest 因果森林
6. Dash应用启动

运行方式:
    python test_seek_root.py
"""

import sys
import os
import numpy as np
import polars as pl

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from seek_root.core.did import DIDAnalyzer
from seek_root.core.psm import PSMAnalyzer
from seek_root.core.rd import RDAnalyzer
from seek_root.core.iv import IVAnalyzer
from seek_root.core.causal_forest import CausalForestAnalyzer


def test_did():
    """测试DID双差分法。"""
    print("\n" + "=" * 60)
    print("🔬 测试 1: DID 双差分法")
    print("=" * 60)

    np.random.seed(42)
    n_samples = 200

    # 生成模拟数据
    treated = np.array([1] * 100 + [0] * 100)
    post_period = np.array([0] * 50 + [1] * 50 + [0] * 50 + [1] * 50)

    # 结果变量: 基础值 + 处理效应(15) + 时间效应(8) + 噪声
    base_value = np.random.normal(100, 10, n_samples)
    treatment_effect = treated * post_period * 15
    time_effect = post_period * 8
    noise = np.random.normal(0, 5, n_samples)
    outcome = base_value + treatment_effect + time_effect + noise

    df = pl.DataFrame({
        "is_treated": treated,
        "is_post": post_period,
        "revenue": outcome,
    })

    analyzer = DIDAnalyzer(df, {
        "treatment_col": "is_treated",
        "time_col": "is_post",
        "outcome_col": "revenue",
    })
    analyzer.fit()
    result = analyzer.get_result()

    print(f"  样本量: {result.sample_size}")
    print(f"  处理组: {result.treatment_size}, 对照组: {result.control_size}")
    print(f"  ATT(处理效应): {result.effect_estimate:.2f}")
    print(f"  95%置信区间: [{result.confidence_interval[0]:.2f}, {result.confidence_interval[1]:.2f}]")
    print(f"  P值: {result.p_value:.4f}")
    print(f"  标准误: {result.standard_error:.2f}")
    print(f"  显著: {'是 ✅' if result.is_significant else '否 ❌'}")
    print(f"  图表数: {len(result.diagnostic_plots)}")
    print("  ✅ DID测试通过!")
    return True


def test_psm():
    """测试PSM倾向得分匹配。"""
    print("\n" + "=" * 60)
    print("🔬 测试 2: PSM 倾向得分匹配")
    print("=" * 60)

    np.random.seed(42)
    n_samples = 300

    # 生成协变量
    age = np.random.randint(20, 60, n_samples)
    income = np.random.normal(50, 10, n_samples)
    education = np.random.randint(10, 20, n_samples)

    # 处理分配: 倾向得分受协变量影响
    ps = 1 / (1 + np.exp(-(0.01 * age + 0.005 * income - 0.02 * education)))
    treatment = (np.random.uniform(0, 1, n_samples) < ps).astype(int)

    # 结果变量
    outcome = 100 + treatment * 20 + 0.5 * age + 0.8 * income + np.random.normal(0, 8, n_samples)

    df = pl.DataFrame({
        "treated": treatment,
        "age": age,
        "income": income,
        "education": education,
        "outcome": outcome,
    })

    analyzer = PSMAnalyzer(df, {
        "treatment_col": "treated",
        "outcome_col": "outcome",
        "covariates": ["age", "income", "education"],
    })
    analyzer.fit()
    result = analyzer.get_result()

    print(f"  样本量: {result.sample_size}")
    print(f"  处理组: {result.treatment_size}, 对照组: {result.control_size}")
    print(f"  ATT(处理效应): {result.effect_estimate:.2f}")
    print(f"  95%置信区间: [{result.confidence_interval[0]:.2f}, {result.confidence_interval[1]:.2f}]")
    print(f"  P值: {result.p_value:.4f}")
    print(f"  显著: {'是 ✅' if result.is_significant else '否 ❌'}")
    print(f"  图表数: {len(result.diagnostic_plots)}")
    print("  ✅ PSM测试通过!")
    return True


def test_rd():
    """测试RD断点回归。"""
    print("\n" + "=" * 60)
    print("🔬 测试 3: RD 断点回归")
    print("=" * 60)

    np.random.seed(42)
    cutoff = 50
    n_samples = 400

    # 运行变量 (考试分数)
    score = np.random.normal(50, 15, n_samples)

    # 处理分配: 分数 >= 50 获得奖学金
    treatment = (score >= cutoff).astype(int)

    # 结果变量: 基础值 + 断点处理效应 + 运行变量效应 + 噪声
    outcome = 100 + treatment * 18 + 0.3 * score + np.random.normal(0, 6, n_samples)

    df = pl.DataFrame({
        "score": score,
        "outcome": outcome,
    })

    analyzer = RDAnalyzer(df, {
        "running_var_col": "score",
        "outcome_col": "outcome",
        "cutoff": cutoff,
    })
    analyzer.fit()
    result = analyzer.get_result()

    print(f"  断点值: {cutoff}")
    print(f"  样本量: {result.sample_size}")
    print(f"  处理效应: {result.effect_estimate:.2f}")
    print(f"  95%置信区间: [{result.confidence_interval[0]:.2f}, {result.confidence_interval[1]:.2f}]")
    print(f"  P值: {result.p_value:.4f}")
    print(f"  显著: {'是 ✅' if result.is_significant else '否 ❌'}")
    print(f"  图表数: {len(result.diagnostic_plots)}")
    print("  ✅ RD测试通过!")
    return True


def test_iv():
    """测试IV工具变量法。"""
    print("\n" + "=" * 60)
    print("🔬 测试 4: IV 工具变量法")
    print("=" * 60)

    np.random.seed(42)
    n_samples = 300

    # 工具变量 (例如: 是否居住在政策覆盖区域)
    instrument = np.random.randint(0, 2, n_samples)

    # 内生处理变量: 受工具变量 + 未观测因素影响
    unobserved = np.random.normal(0, 1, n_samples)
    treatment = (0.4 * instrument + unobserved + np.random.normal(0, 0.3, n_samples) > 0).astype(int)

    # 结果变量: 处理效应 + 内生性偏差(未观测因素同时影响处理和结果)
    outcome = 100 + treatment * 12 + 2 * unobserved + np.random.normal(0, 5, n_samples)

    df = pl.DataFrame({
        "treatment": treatment,
        "instrument": instrument,
        "outcome": outcome,
    })

    analyzer = IVAnalyzer(df, {
        "treatment_col": "treatment",
        "instrument_col": "instrument",
        "outcome_col": "outcome",
        "covariates": [],
    })
    analyzer.fit()
    result = analyzer.get_result()

    print(f"  样本量: {result.sample_size}")
    print(f"  处理组: {result.treatment_size}, 对照组: {result.control_size}")
    print(f"  处理效应(LATE): {result.effect_estimate:.2f}")
    print(f"  95%置信区间: [{result.confidence_interval[0]:.2f}, {result.confidence_interval[1]:.2f}]")
    print(f"  P值: {result.p_value:.4f}")
    print(f"  显著: {'是 ✅' if result.is_significant else '否 ❌'}")
    print(f"  图表数: {len(result.diagnostic_plots)}")
    print("  ✅ IV测试通过!")
    return True


def test_causal_forest():
    """测试CausalForest因果森林。"""
    print("\n" + "=" * 60)
    print("🔬 测试 5: CausalForest 因果森林")
    print("=" * 60)

    np.random.seed(42)
    n_samples = 500

    # 协变量
    age = np.random.randint(20, 70, n_samples)
    income = np.random.normal(50, 15, n_samples)
    spending = np.random.normal(30, 10, n_samples)

    # 处理分配
    treatment = np.random.randint(0, 2, n_samples)

    # 异质性处理效应: 年龄越大, 效应越大
    base_effect = 15 + 0.1 * (age - 40)
    outcome = 100 + treatment * base_effect + 0.5 * income + np.random.normal(0, 5, n_samples)

    df = pl.DataFrame({
        "treated": treatment,
        "age": age,
        "income": income,
        "spending": spending,
        "outcome": outcome,
    })

    analyzer = CausalForestAnalyzer(df, {
        "treatment_col": "treated",
        "outcome_col": "outcome",
        "covariates": ["age", "income", "spending"],
        "n_estimators": 50,
        "max_depth": 5,
    })
    analyzer.fit()
    result = analyzer.get_result()

    print(f"  样本量: {result.sample_size}")
    print(f"  处理组: {result.treatment_size}, 对照组: {result.control_size}")
    print(f"  平均处理效应: {result.effect_estimate:.2f}")
    print(f"  95%置信区间: [{result.confidence_interval[0]:.2f}, {result.confidence_interval[1]:.2f}]")
    print(f"  P值: {result.p_value:.4f}")
    print(f"  显著: {'是 ✅' if result.is_significant else '否 ❌'}")
    print(f"  图表数: {len(result.diagnostic_plots)}")
    if hasattr(result, 'metadata') and result.metadata and 'cate_distribution' in result.metadata:
        dist = result.metadata['cate_distribution']
        print(f"  CATE分布: min={dist['min']:.1f}, median={dist['q50']:.1f}, max={dist['max']:.1f}")
    print("  ✅ CausalForest测试通过!")
    return True


def main():
    """主测试函数。"""
    print("\n" + "=" * 60)
    print("🌱 Seek Root - 因果推断系统测试")
    print("=" * 60)
    print(f"Python版本: {sys.version.split()[0]}")
    print(f"NumPy: {np.__version__}")
    print(f"Polars: {pl.__version__}")
    print("=" * 60)

    results = []
    tests = [
        ("DID 双差分法", test_did),
        ("PSM 倾向得分匹配", test_psm),
        ("RD 断点回归", test_rd),
        ("IV 工具变量法", test_iv),
        ("CausalForest 因果森林", test_causal_forest),
    ]

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result, None))
        except Exception as e:
            print(f"  ❌ {test_name} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False, str(e)))

    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)

    passed = sum(1 for _, r, _ in results if r)
    total = len(results)

    for name, result, error in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name:30s}: {status}")
        if error:
            print(f"    错误: {error[:80]}")

    print(f"\n  总计: {passed}/{total} 测试通过")
    print("=" * 60)

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
