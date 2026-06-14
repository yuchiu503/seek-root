"""Seek Root - 演示数据生成脚本。

生成用于测试因果推断系统的演示数据，包括 DID、PSM、RD、IV、CF 五种方法所需的数据格式。

用法:
    python -m seek_root.demo_data [output_dir]
"""

import os
import sys
from pathlib import Path

import numpy as np
import polars as pl


def generate_did_data(n: int = 200) -> pl.DataFrame:
    """生成 DID (双差分法) 演示数据。

    数据包含: 处理/对照组标识, 处理前/后时间标识, 结果变量, 协变量。

    参数:
        n: 样本量

    返回:
        pl.DataFrame: 包含 DID 分析所需字段的数据框
    """
    rng = np.random.default_rng(42)

    treatment = rng.binomial(1, 0.5, n)  # 是否处理组
    post = rng.binomial(1, 0.5, n)  # 是否处理后时期
    # 真实处理效应: 15
    outcome = (
        50
        + 8 * post
        + 5 * treatment
        + 15 * treatment * post
        + rng.normal(0, 8, n)
    )
    x1 = rng.normal(30, 10, n)
    x2 = rng.exponential(5, n)

    return pl.DataFrame({
        "id": np.arange(n),
        "treatment": treatment,
        "post": post,
        "outcome": np.round(outcome, 2),
        "age": np.round(x1, 1),
        "income": np.round(x2, 1),
    })


def generate_psm_data(n: int = 300) -> pl.DataFrame:
    """生成 PSM (倾向得分匹配) 演示数据。

    参数:
        n: 样本量

    返回:
        pl.DataFrame: 包含 PSM 分析所需字段的数据框
    """
    rng = np.random.default_rng(123)

    age = rng.normal(35, 10, n)
    income = rng.normal(5000, 2000, n)
    education = rng.uniform(6, 16, n)
    # 处理分配取决于协变量 (有选择偏倚)
    ps_score = 1 / (1 + np.exp(-(-2 + 0.05 * age + 0.001 * income + 0.1 * education)))
    treatment = rng.binomial(1, ps_score, n)

    # 结果变量: 真实处理效应 20
    outcome = 30 + 20 * treatment + 0.5 * age + 0.001 * income + 0.3 * education + rng.normal(0, 5, n)

    return pl.DataFrame({
        "id": np.arange(n),
        "treatment": treatment,
        "outcome": np.round(outcome, 2),
        "age": np.round(age, 1),
        "income": np.round(income, 0),
        "education": np.round(education, 1),
    })


def generate_rd_data(n: int = 400, cutoff: float = 50.0) -> pl.DataFrame:
    """生成 RD (断点回归) 演示数据。

    参数:
        n: 样本量
        cutoff: 断点值

    返回:
        pl.DataFrame: 包含 RD 分析所需字段的数据框
    """
    rng = np.random.default_rng(456)

    running_var = rng.normal(cutoff, 15, n)  # 运行变量
    treatment = (running_var >= cutoff).astype(int)  # 在断点右侧接受处理
    # 真实处理效应: 20
    outcome = (
        40
        + 20 * treatment
        + 0.5 * (running_var - cutoff)
        + rng.normal(0, 8, n)
    )

    return pl.DataFrame({
        "id": np.arange(n),
        "running_var": np.round(running_var, 2),
        "treatment": treatment,
        "outcome": np.round(outcome, 2),
    })


def generate_iv_data(n: int = 300) -> pl.DataFrame:
    """生成 IV (工具变量法) 演示数据。

    参数:
        n: 样本量

    返回:
        pl.DataFrame: 包含 IV 分析所需字段的数据框
    """
    rng = np.random.default_rng(789)

    Z = rng.binomial(1, 0.5, n)  # 工具变量
    confounder = rng.normal(0, 1, n)  # 混淆变量
    # 内生处理变量: 受工具变量和混淆变量影响
    treatment = (rng.uniform(0, 1, n) < 0.3 + 0.4 * Z + 0.1 * confounder).astype(int)
    # 结果变量: 真实 LATE = 15
    outcome = 30 + 15 * treatment + 10 * confounder + rng.normal(0, 15, n)

    return pl.DataFrame({
        "id": np.arange(n),
        "instrument": Z,
        "treatment": treatment,
        "outcome": np.round(outcome, 2),
        "age": np.round(rng.normal(35, 10, n), 1),
    })


def generate_cf_data(n: int = 500) -> pl.DataFrame:
    """生成 Causal Forest (因果森林) 演示数据。

    参数:
        n: 样本量

    返回:
        pl.DataFrame: 包含 CF 分析所需字段的数据框
    """
    rng = np.random.default_rng(321)

    X1 = rng.normal(0, 1, n)
    X2 = rng.normal(0, 1, n)
    X3 = rng.uniform(0, 1, n)
    X4 = rng.exponential(1, n)

    # 处理分配概率
    ps = 1 / (1 + np.exp(-(-0.5 + 0.5 * X1)))
    treatment = rng.binomial(1, ps, n)

    # 异质性处理效应: tau(x) = 10 + 5 * X1 - 3 * X2
    tau = 10 + 5 * X1 - 3 * X2
    # 结果变量
    outcome = 40 + treatment * tau + 2 * X1 + 1.5 * X2 + rng.normal(0, 5, n)

    return pl.DataFrame({
        "id": np.arange(n),
        "treatment": treatment,
        "outcome": np.round(outcome, 2),
        "X1": np.round(X1, 2),
        "X2": np.round(X2, 2),
        "X3": np.round(X3, 2),
        "X4": np.round(X4, 2),
    })


def main(output_dir: str = "demo_data"):
    """主函数: 生成并保存所有演示数据。

    参数:
        output_dir: 输出目录
    """
    os.makedirs(output_dir, exist_ok=True)

    datasets = {
        "did_demo.csv": generate_did_data(),
        "psm_demo.csv": generate_psm_data(),
        "rd_demo.csv": generate_rd_data(),
        "iv_demo.csv": generate_iv_data(),
        "cf_demo.csv": generate_cf_data(),
    }

    print(f"🌱 生成 Seek Root 演示数据到目录: {output_dir}")
    print("=" * 60)

    for filename, df in datasets.items():
        filepath = os.path.join(output_dir, filename)
        df.write_csv(filepath)
        print(f"  ✅ {filename}: {len(df)} 行, {len(df.columns)} 列")
        print(f"     字段: {list(df.columns)}")

    print("=" * 60)
    print(f"\n📝 使用方法:")
    print(f"  1. 打开浏览器访问 http://localhost:8050")
    print(f"  2. 点击 '上传数据' 上传 demo_data 目录中的 CSV 文件")
    print(f"  3. 选择对应方法进行分析")
    print(f"\n📌 推荐测试场景:")
    print(f"  - DID: did_demo.csv (字段: treatment, post, outcome)")
    print(f"  - PSM: psm_demo.csv (字段: treatment, outcome, age, income, education)")
    print(f"  - RD: rd_demo.csv (字段: running_var, outcome)")
    print(f"  - IV: iv_demo.csv (字段: instrument, treatment, outcome)")
    print(f"  - CF: cf_demo.csv (字段: treatment, outcome, X1-X4)")


if __name__ == "__main__":
    output_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "demo_data"
    )
    main(output_dir)
