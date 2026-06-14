"""分析配置页面。

提供场景选择、方法配置和执行分析的界面。
"""

import dash_mantine_components as dmc
from dash import html, dcc, callback, Output, Input, State, dcc
import polars as pl
import numpy as np


# 支持的方法列表
METHODS = [
    ("DID", "双差分法 - 适合有处理组和控制组、有前后时间点的政策效果评估"),
    ("PSM", "倾向得分匹配 - 适合存在选择偏差的观察数据"),
    ("RD", "断点回归 - 适合有明确断点/阈值的准实验场景"),
    ("IV", "工具变量法 - 处理内生性问题，需要工具变量"),
    ("CF", "因果森林 - 异质性处理效应分析，精准定位"),
]

# 场景模板
SCENARIOS = [
    ("促销活动效果", "DID", "评估促销活动对销售额的影响"),
    ("渠道效果归因", "PSM", "比较不同渠道对转化率的影响"),
    ("产品迭代评估", "DID", "评估新版本功能对用户行为的影响"),
    ("补贴政策评估", "RD", "评估补贴政策在阈值处的效果"),
    ("用户分层分析", "CF", "分析不同用户群体的异质性效应"),
]


def render_analysis_page():
    """渲染分析配置页面。

    返回:
        html.Div: 页面内容
    """
    return html.Div(
        style={"maxWidth": "1000px", "margin": "0 auto", "padding": "20px"},
        children=[
            dmc.Title("配置分析", order=1, mb="md"),
            dmc.Text("选择适合你数据的因果推断方法并配置参数。", size="sm", c="dimmed", mb="md"),

            # 方法选择
            dmc.Paper(
                p="lg",
                shadow="md",
                radius="md",
                mb="md",
                children=[
                    dmc.Title("步骤 1: 选择分析方法", order=3, mb="md"),
                    dmc.Grid(
                        children=[
                            dmc.GridCol(
                                span=4,
                                children=[
                                    dmc.Card(
                                        p="md",
                                        shadow="sm",
                                        radius="md",
                                        children=[
                                            dmc.Radio(
                                                label=dmc.Text(method_name, fw=600),
                                                value=method_id,
                                                name="method-selector",
                                            ),
                                            dmc.Text(desc, size="xs", c="dimmed", mt="xs"),
                                        ],
                                    ),
                                ],
                            )
                            for method_id, (method_name, desc) in enumerate(
                                [(m[0], m[1]) for m in METHODS]
                            )
                        ],
                    ),
                ],
            ),

            # 列配置区域
            dmc.Paper(
                p="lg",
                shadow="md",
                radius="md",
                mb="md",
                id="column-config-area",
                children=[
                    dmc.Title("步骤 2: 配置数据列", order=3, mb="md"),
                    dmc.Text("请从上传的数据中选择对应的列。", size="sm", c="dimmed", mb="md"),
                    html.Div("请先上传数据...", style={"color": "#6b7280"}),
                ],
            ),

            # 执行按钮
            dmc.Button(
                "开始分析",
                id="run-analysis-btn",
                color="green",
                size="lg",
                fullWidth=True,
                mb="md",
            ),

            # 结果区域
            html.Div(id="analysis-results-area"),
        ],
    )


@callback(
    Output("column-config-area", "children"),
    Input("current-page", "data"),
    State("app-data-store", "data"),
)
def render_column_config(page, store_data):
    """根据选择的方法动态渲染列配置区域。

    参数:
        page: 当前页面
        store_data: 存储的数据（含列名）

    返回:
        html.Div: 配置区域内容
    """
    if page != "analysis":
        return html.Div()

    columns = []
    if store_data and "columns" in store_data:
        columns = store_data["columns"]

    if not columns:
        return [
            dmc.Title("步骤 2: 配置数据列", order=3, mb="md"),
            dmc.Alert("尚未上传数据，请先上传数据。", color="orange", title="提示"),
        ]

    # DID配置
    return [
        dmc.Title("步骤 2: 配置数据列 (DID)", order=3, mb="md"),
        dmc.Grid(
            children=[
                dmc.GridCol(
                    span=6,
                    children=[
                        dmc.Stack(
                            [
                                dmc.Text("处理组列 (0/1)", fw=500),
                                dmc.Select(
                                    id="treatment-col",
                                    placeholder="选择处理组标识列",
                                    data=[{"value": c, "label": c} for c in columns],
                                ),
                            ],
                            gap="xs",
                        ),
                    ],
                ),
                dmc.GridCol(
                    span=6,
                    children=[
                        dmc.Stack(
                            [
                                dmc.Text("时间列 (0/1)", fw=500),
                                dmc.Select(
                                    id="time-col",
                                    placeholder="选择时间标识列",
                                    data=[{"value": c, "label": c} for c in columns],
                                ),
                            ],
                            gap="xs",
                        ),
                    ],
                ),
                dmc.GridCol(
                    span=12,
                    children=[
                        dmc.Stack(
                            [
                                dmc.Text("结果变量列", fw=500),
                                dmc.Select(
                                    id="outcome-col",
                                    placeholder="选择结果变量列",
                                    data=[{"value": c, "label": c} for c in columns],
                                ),
                            ],
                            gap="xs",
                        ),
                    ],
                ),
            ],
        ),
    ]


@callback(
    Output("analysis-results-area", "children"),
    Output("current-page", "data", allow_duplicate=True),
    Input("run-analysis-btn", "n_clicks"),
    State("treatment-col", "value"),
    State("time-col", "value"),
    State("outcome-col", "value"),
    State("app-data-store", "data"),
    prevent_initial_call=True,
)
def run_analysis(n_clicks, treatment_col, time_col, outcome_col, store_data):
    """执行因果推断分析。

    参数:
        n_clicks: 按钮点击次数
        treatment_col: 处理组列名
        time_col: 时间列名
        outcome_col: 结果变量列名
        store_data: 存储的数据

    返回:
        tuple: (结果内容, 页面跳转)
    """
    if not n_clicks:
        return html.Div(), "analysis"

    # 校验
    if not treatment_col or not outcome_col:
        return dmc.Alert("请先选择数据列！", color="red", title="配置错误"), "analysis"

    try:
        # 创建示例数据（实际应用中应从存储中读取）
        n_samples = 200
        np.random.seed(42)
        treatment = np.random.randint(0, 2, n_samples)
        time = np.random.randint(0, 2, n_samples)

        # 结果变量: 基础 + 处理效应 + 时间效应 + 交互项
        att = 15.0
        base = 100 + np.random.normal(0, 10, n_samples)
        outcome = (
            base
            + treatment * time * att
            + time * 8
            + np.random.normal(0, 5, n_samples)
        )

        df = pl.DataFrame({
            "treatment": treatment,
            "time": time,
            "outcome": outcome,
        })

        # 执行DID分析
        from seek_root.core.did import DIDAnalyzer

        analyzer = DIDAnalyzer(df, {
            "treatment_col": "treatment",
            "time_col": "time",
            "outcome_col": "outcome",
        })
        analyzer.fit()
        result = analyzer.get_result()

        # 生成结果卡片
        effect = result.effect_estimate
        ci_low = result.confidence_interval[0]
        ci_high = result.confidence_interval[1]
        p_value = result.p_value
        significant = result.is_significant

        result_content = html.Div(
            children=[
                dmc.Paper(
                    p="xl",
                    shadow="lg",
                    radius="md",
                    style={"background": "#f0fdf4" if significant else "#fef2f2"},
                    children=[
                        dmc.Title("分析结果", order=2, mb="md"),

                        dmc.Grid(
                            children=[
                                dmc.GridCol(
                                    span=4,
                                    children=[
                                        dmc.Stack(
                                            [
                                                dmc.Text("处理效应 (ATT)", size="sm", c="dimmed"),
                                                dmc.Text(f"{effect:.2f}", size="3xl", fw=700, c="#064e3b"),
                                            ],
                                            align="center",
                                            gap="xs",
                                        ),
                                    ],
                                ),
                                dmc.GridCol(
                                    span=4,
                                    children=[
                                        dmc.Stack(
                                            [
                                                dmc.Text("置信区间 (95%)", size="sm", c="dimmed"),
                                                dmc.Text(f"[{ci_low:.2f}, {ci_high:.2f}]", size="xl", fw=600),
                                            ],
                                            align="center",
                                            gap="xs",
                                        ),
                                    ],
                                ),
                                dmc.GridCol(
                                    span=4,
                                    children=[
                                        dmc.Stack(
                                            [
                                                dmc.Text("p值", size="sm", c="dimmed"),
                                                dmc.Text(f"{p_value:.4f}", size="xl", fw=600),
                                            ],
                                            align="center",
                                            gap="xs",
                                        ),
                                    ],
                                ),
                            ],
                        ),

                        html.Div(style={"height": "20px"}),

                        dmc.Divider(),
                        html.Br(),

                        dmc.Title("诊断信息", order=3, mb="md"),
                        dmc.Text(
                            "统计显著性: " + ("显著 (p < 0.05)" if significant else "不显著 (p >= 0.05)"),
                            size="md",
                        ),
                        dmc.Text(
                            f"样本量: {result.sample_size}, 处理组: {result.treatment_size}, 控制组: {result.control_size}",
                            size="md",
                        ),
                        html.Br(),

                        dmc.Title("业务解读", order=3, mb="md"),
                        dmc.Text(
                            f"分析结果显示，处理效应估计值为 {effect:.2f}，"
                            f"95%置信区间为 [{ci_low:.2f}, {ci_high:.2f}]，"
                            f"p值为 {p_value:.4f}。"
                            f"这表明{'处理具有显著的因果效应' if significant else '处理的效应在统计上不显著'}。"
                            f"建议{'继续执行该政策/活动' if significant else '审慎评估或收集更多数据再进行分析'}。",
                            size="md",
                        ),

                        html.Div(style={"height": "20px"}),

                        dmc.Group(
                            [
                                dmc.Button("查看详细报告", id="go-to-results-btn", color="green", size="lg"),
                                dmc.Button("重新分析", variant="outline", size="lg"),
                            ],
                            justify="flex-end",
                        ),
                    ],
                ),
            ],
        )

        return result_content, "results"

    except Exception as e:
        return dmc.Alert(f"分析失败: {str(e)}", color="red", title="错误"), "analysis"


@callback(
    Output("current-page", "data", allow_duplicate=True),
    Input("go-to-results-btn", "n_clicks"),
    prevent_initial_call=True,
)
def go_to_results(n_clicks):
    """导航到结果报告页。"""
    if n_clicks:
        return "results"
    return "analysis"
