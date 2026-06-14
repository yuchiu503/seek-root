"""结果报告页面。

展示完整的分析结果、诊断图表和业务解读。
"""

import dash_mantine_components as dmc
from dash import html, dcc


def render_results_page():
    """渲染结果报告页面。

    返回:
        html.Div: 页面内容
    """
    return html.Div(
        style={"maxWidth": "1200px", "margin": "0 auto", "padding": "20px"},
        children=[
            dmc.Title("分析结果报告", order=1, mb="md"),

            # 核心指标卡片
            dmc.Grid(
                children=[
                    dmc.GridCol(
                        span=3,
                        children=[
                            dmc.Paper(
                                p="md",
                                shadow="sm",
                                radius="md",
                                style={"background": "#ecfdf5"},
                                children=[
                                    dmc.Text("处理效应", size="sm", c="dimmed"),
                                    dmc.Text("15.00", size="2xl", fw=700, c="#064e3b"),
                                ],
                            ),
                        ],
                    ),
                    dmc.GridCol(
                        span=3,
                        children=[
                            dmc.Paper(
                                p="md",
                                shadow="sm",
                                radius="md",
                                style={"background": "#eff6ff"},
                                children=[
                                    dmc.Text("P值", size="sm", c="dimmed"),
                                    dmc.Text("0.002", size="2xl", fw=700, c="#1e3a8a"),
                                ],
                            ),
                        ],
                    ),
                    dmc.GridCol(
                        span=3,
                        children=[
                            dmc.Paper(
                                p="md",
                                shadow="sm",
                                radius="md",
                                style={"background": "#f5f3ff"},
                                children=[
                                    dmc.Text("置信区间", size="sm", c="dimmed"),
                                    dmc.Text("[8.45, 21.55]", size="xl", fw=700, c="#4c1d95"),
                                ],
                            ),
                        ],
                    ),
                    dmc.GridCol(
                        span=3,
                        children=[
                            dmc.Paper(
                                p="md",
                                shadow="sm",
                                radius="md",
                                style={"background": "#fef3c7"},
                                children=[
                                    dmc.Text("显著性", size="sm", c="dimmed"),
                                    dmc.Text("显著 (p<0.05)", size="xl", fw=700, c="#78350f"),
                                ],
                            ),
                        ],
                    ),
                ],
                mb="xl",
            ),

            # 详细解读
            dmc.Paper(
                p="xl",
                shadow="sm",
                radius="md",
                mb="xl",
                children=[
                    dmc.Title("业务解读", order=3, mb="md"),
                    dmc.Text(
                        "本次分析使用 DID 方法，评估了处理组与控制组之间的差异。"
                        "处理效应估计值为 15.00，P值为 0.002，95%置信区间为 [8.45, 21.55]。"
                        "这些指标表明处理具有显著的因果效应，说明该政策/活动能够带来正向的效果。"
                        "建议继续执行该措施，并进一步收集数据以验证长期效果。",
                        size="md",
                        lineHeight=1.8,
                    ),
                ],
            ),

            # 诊断图表
            dmc.Paper(
                p="xl",
                shadow="sm",
                radius="md",
                mb="xl",
                children=[
                    dmc.Title("诊断图表", order=3, mb="md"),

                    dmc.Grid(
                        children=[
                            dmc.GridCol(
                                span=6,
                                children=[
                                    dmc.Text("平行趋势检验", fw=600, mb="sm"),
                                    dmc.Text(
                                        "处理组和控制组在处理前具有相似的时间趋势，满足 DID 的平行趋势假设。"
                                        "处理后处理组结果显著上升，控制组变化平缓。",
                                        size="sm",
                                        c="dimmed",
                                    ),
                                ],
                            ),
                            dmc.GridCol(
                                span=6,
                                children=[
                                    dmc.Text("效应分解", fw=600, mb="sm"),
                                    dmc.Text(
                                        "处理组平均值变化：+18.5"
                                        "控制组平均值变化：+8.2"
                                        "净处理效应 (DID): +10.3",
                                        size="sm",
                                        c="dimmed",
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),

            # 操作按钮
            dmc.Group(
                children=[
                    dmc.Button("导出PDF报告", variant="filled", color="green", size="lg"),
                    dmc.Button("分享分析", variant="outline", size="lg"),
                    dmc.Button("回到首页", variant="subtle", size="lg", id="back-to-home"),
                ],
                justify="flex-end",
            ),
        ],
    )
