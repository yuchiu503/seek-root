"""分析页面模块。

提供因果推断分析的配置和执行功能。
"""

import dash
import dash_mantine_components as dmc
from dash import html, dcc, callback, Output, Input, State, register_page, no_update
import polars as pl
import json

from seek_root.core.base import CausalMethod

dash.register_page(__name__, path="/analysis", title="因果分析")


# 场景定义
SCENARIOS = [
    {
        "id": "promotion",
        "name": "促销活动效果评估",
        "description": "评估满减、优惠券等促销活动对销售额/转化率的影响",
        "methods": ["did", "psm"],
        "icon": "🎯",
    },
    {
        "id": "channel",
        "name": "渠道效果归因",
        "description": "分析不同营销渠道对最终转化的贡献度",
        "methods": ["iv", "causal_forest"],
        "icon": "📊",
    },
    {
        "id": "ab_test",
        "name": "A/B测试因果验证",
        "description": "验证A/B测试结果的因果效应",
        "methods": ["did", "psm"],
        "icon": "🔬",
    },
    {
        "id": "pricing",
        "name": "价格策略影响",
        "description": "分析价格变动对销量和收入的影响",
        "methods": ["rd", "causal_forest"],
        "icon": "💰",
    },
    {
        "id": "custom",
        "name": "自定义分析",
        "description": "灵活配置参数，进行自定义因果推断分析",
        "methods": ["did", "psm", "rd", "iv", "causal_forest"],
        "icon": "⚙️",
    },
]


def layout():
    """分析页面布局。

    返回:
        html.Div: 分析页面组件
    """
    return html.Div(
        style={"maxWidth": "1200px", "margin": "0 auto", "padding": "20px"},
        children=[
            # 页面标题
            dmc.Title("因果推断分析", order=1, mb="md"),
            dmc.Text(
                "选择分析场景，配置分析方法，获取专业的因果分析结果。",
                c="dimmed",
                mb="xl",
            ),
            # 步骤指示器
            dmc.Stepper(
                active=1,
                size="sm",
                children=[
                    dmc.StepperStep(
                        label="选择场景",
                        description="选择分析场景",
                        completedIcon="✓",
                    ),
                    dmc.StepperStep(
                        label="配置方法",
                        description="设置参数",
                        progressIcon="2",
                    ),
                    dmc.StepperStep(
                        label="执行分析",
                        description="运行算法",
                        progressIcon="3",
                    ),
                ],
                mb="xl",
            ),
            # 场景选择
            dmc.Title("选择分析场景", order=2, mb="md"),
            dmc.SimpleGrid(
                cols=3,
                children=[
                    dmc.Card(
                        id={"type": "scenario-card", "index": s["id"]},
                        shadow="md",
                        padding="lg",
                        radius="md",
                        style={
                            "cursor": "pointer",
                            "border": "2px solid transparent",
                        },
                        children=[
                            dmc.Text(s["icon"], size="xl"),
                            dmc.Text(s["name"], weight=700, size="lg", mt="sm"),
                            dmc.Text(s["description"], size="sm", c="dimmed", mt="xs"),
                            dmc.Group(
                                children=[
                                    dmc.Badge(
                                        m.upper(),
                                        variant="light",
                                        color="green",
                                    )
                                    for m in s["methods"]
                                ],
                                mt="md",
                            ),
                        ],
                    )
                    for s in SCENARIOS
                ],
                mb="xl",
            ),
            # 隐藏的存储组件
            dcc.Store(id="selected-scenario", data=None),
            # 方法配置区域（条件显示）
            html.Div(id="method-config-area", style={"display": "none"}),
            # 分析执行区域
            html.Div(id="analysis-execute-area", style={"display": "none"}),
        ],
    )


@callback(
    Output("method-config-area", "children"),
    Output("method-config-area", "style"),
    Output("selected-scenario", "data"),
    Input({"type": "scenario-card", "index": dcc._children.to_components()[0]["id"]["index"]} if False else "dummy", "n_clicks": 1}, "n_clicks"),
    Input({"type": "scenario-card", "index": SCENARIOS[0]["id"]}, "n_clicks"),
    Input({"type": "scenario-card", "index": SCENARIOS[1]["id"]}, "n_clicks"),
    Input({"type": "scenario-card", "index": SCENARIOS[2]["id"]}, "n_clicks"),
    Input({"type": "scenario-card", "index": SCENARIOS[3]["id"]}, "n_clicks"),
    Input({"type": "scenario-card", "index": SCENARIOS[4]["id"]}, "n_clicks"),
    prevent_initial_call=True,
)
def select_scenario(*args):
    """选择分析场景，显示方法配置。

    参数:
        *args: 场景卡片的点击事件

    返回:
        tuple: (配置组件, 显示样式, 选中场景数据)
    """
    # 找到触发回调的卡片
    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update, no_update, no_update

    triggered_id = ctx.triggered[0]["prop_id"]

    # 解析场景ID
    scenario_id = None
    for s in SCENARIOS:
        if s["id"] in triggered_id:
            scenario_id = s["id"]
            break

    if scenario_id is None:
        return no_update, no_update, no_update

    # 找到场景配置
    scenario = next((s for s in SCENARIOS if s["id"] == scenario_id), None)
    if not scenario:
        return no_update, no_update, no_update

    # 构建配置组件
    config_children = [
        dmc.Title(f"配置 {scenario['name']}", order=2, mt="xl", mb="md"),
        dmc.Alert(
            f"推荐方法: {', '.join([m.upper() for m in scenario['methods']])}",
            color="green",
            title="智能推荐",
            mb="md",
        ),
        # 方法选择
        dmc.Select(
            label="选择分析方法",
            placeholder="选择因果推断方法",
            data=[
                {"value": m, "label": _get_method_label(m)}
                for m in scenario["methods"]
            ],
            value=scenario["methods"][0],
            id="method-select",
            mb="md",
        ),
        # 参数配置
        html.Div(id="param-config-area"),
        # 执行按钮
        dmc.Button(
            "开始分析",
            size="lg",
            variant="filled",
            color="green",
            leftSection="▶️",
            id="run-analysis-btn",
            mt="xl",
        ),
    ]

    return config_children, {"display": "block"}, scenario


def _get_method_label(method: str) -> str:
    """获取方法的中文标签。

    参数:
        method: 方法代码

    返回:
        str: 方法中文标签
    """
    labels = {
        "did": "DID - 双差分法",
        "psm": "PSM - 倾向得分匹配",
        "rd": "RD - 断点回归",
        "iv": "IV - 工具变量法",
        "causal_forest": "Causal Forest - 因果森林",
    }
    return labels.get(method, method)


@callback(
    Output("param-config-area", "children"),
    Input("method-select", "value"),
)
def update_param_config(method):
    """根据选择的方法更新参数配置。

    参数:
        method: 选中的方法

    返回:
        html.Div: 参数配置组件
    """
    if not method:
        return html.Div()

    # 构建参数配置
    children = [
        dmc.Text("配置分析参数", weight=700, mb="sm"),
    ]

    if method == "did":
        children.extend([
            dmc.Select(
                label="处理组标识列",
                placeholder="选择列",
                id="did-treatment-col",
                mb="sm",
            ),
            dmc.Select(
                label="时间标识列",
                placeholder="选择列",
                id="did-time-col",
                mb="sm",
            ),
            dmc.Select(
                label="结果变量列",
                placeholder="选择列",
                id="did-outcome-col",
                mb="sm",
            ),
            dmc.MultiSelect(
                label="协变量（可选）",
                placeholder="选择协变量列",
                id="did-covariates",
                mb="sm",
            ),
        ])
    elif method == "psm":
        children.extend([
            dmc.Select(
                label="处理组标识列",
                placeholder="选择列",
                id="psm-treatment-col",
                mb="sm",
            ),
            dmc.Select(
                label="结果变量列",
                placeholder="选择列",
                id="psm-outcome-col",
                mb="sm",
            ),
            dmc.MultiSelect(
                label="协变量",
                placeholder="选择协变量列",
                id="psm-covariates",
                mb="sm",
            ),
        ])
    # ... 其他方法类似

    return html.Div(children)


@callback(
    Output("analysis-execute-area", "children"),
    Output("analysis-execute-area", "style"),
    Input("run-analysis-btn", "n_clicks"),
    State("selected-scenario", "data"),
    State("method-select", "value"),
    prevent_initial_call=True,
)
def run_analysis(n_clicks, scenario, method):
    """执行因果分析。

    参数:
        n_clicks: 执行按钮点击次数
        scenario: 选中的场景
        method: 选中的方法

    返回:
        tuple: (结果区域组件, 显示样式)
    """
    if n_clicks and n_clicks > 0:
        # 这里应该调用实际的因果分析方法
        # 目前返回模拟结果
        return [
            dmc.Alert(
                "分析功能正在开发中...",
                color="blue",
                title="提示",
                mt="xl",
            ),
        ], {"display": "block"}

    return html.Div(), {"display": "none"}
