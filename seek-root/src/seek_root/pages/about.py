"""关于页面。

介绍产品、使用指南和联系方式。
"""

import dash_mantine_components as dmc
from dash import html


def render_about_page():
    """渲染关于页面内容。

    返回:
        html.Div: 页面内容
    """
    return html.Div(
        style={"maxWidth": "1000px", "margin": "0 auto", "padding": "20px"},
        children=[
            # 产品介绍
            dmc.Paper(
                p="xl",
                shadow="md",
                radius="md",
                mb="xl",
                children=[
                    dmc.Title("关于 Seek Root", order=2, mb="md"),
                    dmc.Text(
                        "Seek Root 是一款面向业务人员的因果推断分析平台，"
                        "旨在让每个人都能轻松地进行数据的因果分析。"
                        "使用最新的统计和机器学习技术，帮助用户从数据中发现真正的因果关系。",
                        size="md",
                    ),
                ],
            ),

            # 功能特色
            dmc.Paper(
                p="xl",
                shadow="md",
                radius="md",
                mb="xl",
                children=[
                    dmc.Title("核心功能", order=3, mb="md"),
                    dmc.Grid(
                        children=[
                            dmc.GridCol(
                                span=6,
                                children=[
                                    dmc.Group(
                                        [
                                            dmc.ThemeIcon("📊", size="lg", radius="md", color="green"),
                                            dmc.Stack(
                                                [
                                                    dmc.Text("多方法支持", fw=600),
                                                    dmc.Text("支持 DID、PSM、RD、IV、CF 五种因果推断方法", size="sm", c="dimmed"),
                                                ],
                                                gap=0,
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            dmc.GridCol(
                                span=6,
                                children=[
                                    dmc.Group(
                                        [
                                            dmc.ThemeIcon("🎯", size="lg", radius="md", color="violet"),
                                            dmc.Stack(
                                                [
                                                    dmc.Text("场景模板", fw=600),
                                                    dmc.Text("预设常见业务场景，一键配置分析参数", size="sm", c="dimmed"),
                                                ],
                                                gap=0,
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            dmc.GridCol(
                                span=6,
                                children=[
                                    dmc.Group(
                                        [
                                            dmc.ThemeIcon("💡", size="lg", radius="md", color="blue"),
                                            dmc.Stack(
                                                [
                                                    dmc.Text("智能解读", fw=600),
                                                    dmc.Text("AI 自动生成业务化的分析报告和解读", size="sm", c="dimmed"),
                                                ],
                                                gap=0,
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            dmc.GridCol(
                                span=6,
                                children=[
                                    dmc.Group(
                                        [
                                            dmc.ThemeIcon("📈", size="lg", radius="md", color="orange"),
                                            dmc.Stack(
                                                [
                                                    dmc.Text("可视化图表", fw=600),
                                                    dmc.Text("自动生成诊断图表，直观展示分析结果", size="sm", c="dimmed"),
                                                ],
                                                gap=0,
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),

            # 使用步骤
            dmc.Paper(
                p="xl",
                shadow="md",
                radius="md",
                mb="xl",
                children=[
                    dmc.Title("使用指南", order=3, mb="md"),
                    dmc.Stack(
                        children=[
                            dmc.Group(
                                [
                                    dmc.Badge("1", size="lg", radius="lg"),
                                    dmc.Text("上传数据", fw=600),
                                    dmc.Text("支持 CSV、Excel 格式", size="sm", c="dimmed"),
                                ],
                            ),
                            dmc.Group(
                                [
                                    dmc.Badge("2", size="lg", radius="lg"),
                                    dmc.Text("选择方法", fw=600),
                                    dmc.Text("根据场景选择合适的因果推断方法", size="sm", c="dimmed"),
                                ],
                            ),
                            dmc.Group(
                                [
                                    dmc.Badge("3", size="lg", radius="lg"),
                                    dmc.Text("配置参数", fw=600),
                                    dmc.Text("选择数据列、设置参数", size="sm", c="dimmed"),
                                ],
                            ),
                            dmc.Group(
                                [
                                    dmc.Badge("4", size="lg", radius="lg"),
                                    dmc.Text("查看结果", fw=600),
                                    dmc.Text("获取完整的分析报告和业务解读", size="sm", c="dimmed"),
                                ],
                            ),
                        ],
                        gap="md",
                    ),
                ],
            ),

            # 技术说明
            dmc.Paper(
                p="xl",
                shadow="md",
                radius="md",
                mb="xl",
                children=[
                    dmc.Title("技术架构", order=3, mb="md"),
                    dmc.Stack(
                        children=[
                            dmc.Text("• 数据处理: Polars 高性能数据处理", size="md"),
                            dmc.Text("• 统计分析: NumPy、SciPy、StatsModels", size="md"),
                            dmc.Text("• 机器学习: Scikit-learn", size="md"),
                            dmc.Text("• 前端界面: Dash + Dash Mantine Components", size="md"),
                            dmc.Text("• 部署: 支持本地部署与云端部署", size="md"),
                        ],
                        gap="xs",
                    ),
                ],
            ),

            # 联系信息
            dmc.Paper(
                p="xl",
                shadow="md",
                radius="md",
                children=[
                    dmc.Title("联系我们", order=3, mb="md"),
                    dmc.Stack(
                        children=[
                            dmc.Text("📧 邮箱: contact@seekroot.ai", size="md"),
                            dmc.Text("🌐 网站: https://seekroot.ai", size="md"),
                            dmc.Text("📱 微信: SeekRoot", size="md"),
                        ],
                        gap="xs",
                    ),
                ],
            ),
        ],
    )
