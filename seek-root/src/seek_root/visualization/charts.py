"""ECharts图表渲染模块。

本模块负责将分析结果渲染为ECharts图表，
支持在Dash应用中嵌入交互式图表。

类:
    EChartsRenderer: ECharts图表渲染器
"""

from typing import Any, Dict, List, Optional
import json

from seek_root.core.base import DiagnosticPlot, AnalysisResult


class EChartsRenderer:
    """ECharts图表渲染器类。

    将分析结果和诊断图表转换为ECharts配置，
    生成可以在Dash应用中渲染的HTML/JSON。

    参数:
        theme (str, optional): 主题设置 ('light' 或 'dark')

    示例:
        >>> renderer = EChartsRenderer(theme='light')
        >>> chart_html = renderer.render_diagnostic_plot(plot)
        >>> # 在Dash中显示
        >>> html.Div(dcc.Graph(figure=chart_html))
    """

    # 探索绿配色方案
    LIGHT_THEME = {
        "primary": "#10b981",      # 主色 - 绿色
        "secondary": "#8b5cf6",   # 辅助色 - 紫色
        "background": "#ffffff",   # 背景色
        "text": "#1a1a2e",        # 文字色
        "grid": "#e5e7eb",         # 网格线色
        "positive": "#10b981",     # 正向效应
        "negative": "#ef4444",     # 负向效应
    }

    DARK_THEME = {
        "primary": "#34d399",      # 主色 - 浅绿色
        "secondary": "#a78bfa",    # 辅助色 - 浅紫色
        "background": "#1a1a2e",   # 背景色
        "text": "#f1f5f9",         # 文字色
        "grid": "#374151",         # 网格线色
        "positive": "#34d399",     # 正向效应
        "negative": "#f87171",      # 负向效应
    }

    def __init__(self, theme: str = "light") -> None:
        """初始化ECharts渲染器。

        参数:
            theme: 主题 ('light' 或 'dark')
        """
        self.theme = theme
        self.colors = self.LIGHT_THEME if theme == "light" else self.DARK_THEME

    def render_diagnostic_plot(self, plot: DiagnosticPlot) -> Dict[str, Any]:
        """渲染诊断图表。

        将DiagnosticPlot对象转换为ECharts配置字典。

        参数:
            plot: 诊断图表对象

        返回:
            dict: ECharts配置字典，可直接用于echarts.init()
        """
        config = plot.data.copy()

        # 添加通用配置
        config.setdefault("title", {"text": plot.title})
        config.setdefault("tooltip", {
            "trigger": "axis",
            "axisPointer": {"type": "cross"}
        })
        config.setdefault("legend", {
            "data": self._extract_legend_data(config),
            "top": 10,
        })
        config.setdefault("grid", {
            "left": "10%",
            "right": "10%",
            "bottom": "15%",
            "top": "20%",
            "containLabel": True,
        })

        # 应用主题颜色
        config = self._apply_theme(config)

        return config

    def render_analysis_result(self, result: AnalysisResult) -> Dict[str, Any]:
        """渲染分析结果图表。

        将完整的分析结果渲染为一组图表。

        参数:
            result: 分析结果对象

        返回:
            dict: 包含多个图表配置的字典
        """
        charts = {}

        # 渲染所有诊断图表
        for i, plot in enumerate(result.diagnostic_plots):
            charts[f"chart_{i}"] = self.render_diagnostic_plot(plot)

        # 添加汇总图表
        charts["summary"] = self._create_summary_chart(result)

        return charts

    def _create_summary_chart(self, result: AnalysisResult) -> Dict[str, Any]:
        """创建结果汇总图表。

        创建显示关键指标的汇总图表。

        参数:
            result: 分析结果对象

        返回:
            dict: ECharts配置字典
        """
        effect = result.effect_estimate
        is_positive = effect > 0

        # 效应值仪表盘
        gauge_data = [
            {
                "value": abs(effect),
                "name": "效应值",
                "title": {"offsetCenter": ["0%", "70%"]},
                "detail": {
                    "valueAnimation": True,
                    "offsetCenter": ["0%", "40%"],
                    "formatter": lambda x: f"{x:.2f}",
                    "color": self.colors["positive"] if is_positive else self.colors["negative"],
                },
            }
        ]

        gauge_config = {
            "title": {"text": f"{result.method.name_cn} - 处理效应", "left": "center"},
            "series": [
                {
                    "type": "gauge",
                    "startAngle": 180,
                    "endAngle": 0,
                    "min": 0,
                    "max": abs(effect) * 2 if effect != 0 else 1,
                    "splitNumber": 8,
                    "axisLine": {
                        "lineStyle": {
                            "width": 6,
                            "color": [
                                [0.3, self.colors["negative"]],
                                [0.7, "#fbbf24"],
                                [1, self.colors["positive"]],
                            ],
                        }
                    },
                    "pointer": {"icon": "path://M12.8,0.7l12,40.1H0.7L12.8,0.7z", "length": "12%"},
                    "axisTick": {"length": 8, "distance": -20},
                    "splitLine": {"length": 20, "distance": -20},
                    "axisLabel": {"distance": -40, "color": self.colors["text"], "fontSize": 10},
                    "title": {"show": False},
                    "detail": {
                        "valueAnimation": True,
                        "width": "60%",
                        "lineHeight": 40,
                        "borderRadius": 8,
                        "offsetCenter": [0, "10%"],
                        "fontSize": 24,
                        "fontWeight": "bold",
                        "formatter": lambda x: f"{x:.2f}",
                        "color": self.colors["text"],
                    },
                    "data": [{"value": abs(effect), "name": "效应值"}],
                }
            ],
        }

        return gauge_config

    def _apply_theme(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """应用主题配置。

        将当前主题的颜色应用到图表配置中。

        参数:
            config: 原始图表配置

        返回:
            dict: 应用主题后的配置
        """
        # 深拷贝避免修改原配置
        config = json.loads(json.dumps(config))

        # 更新颜色
        if "series" in config:
            for series in config["series"]:
                if "itemStyle" in series and "color" in series["itemStyle"]:
                    # 替换为主题色
                    for key, value in [("positive", self.colors["positive"]), ("negative", self.colors["negative"])]:
                        if key in str(series["itemStyle"]["color"]):
                            series["itemStyle"]["color"] = value
                if "lineStyle" in series and "color" in series.get("lineStyle", {}):
                    series["lineStyle"]["color"] = self.colors["primary"]

        return config

    def _extract_legend_data(self, config: Dict[str, Any]) -> List[str]:
        """提取图例数据。

        从图表配置中提取所有系列的名称作为图例。

        参数:
            config: 图表配置

        返回:
            list: 系列名称列表
        """
        legend_data = []
        if "series" in config:
            for series in config["series"]:
                if "name" in series:
                    legend_data.append(series["name"])
        return legend_data

    def create_html(self, chart_config: Dict[str, Any]) -> str:
        """生成ECharts HTML代码。

        将图表配置转换为完整的HTML代码，
        可直接在浏览器中打开查看。

        参数:
            chart_config: ECharts配置字典

        返回:
            str: 完整的HTML代码
        """
        config_json = json.dumps(chart_config, ensure_ascii=False)

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Seek Root - 因果分析图表</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            background-color: {self.colors['background']};
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        #chart {{
            width: 100%;
            height: 500px;
        }}
    </style>
</head>
<body>
    <div id="chart"></div>
    <script>
        var chart = echarts.init(document.getElementById('chart'), '{self.theme}');
        var option = {config_json};
        chart.setOption(option);
        window.addEventListener('resize', function() {{
            chart.resize();
        }});
    </script>
</body>
</html>
"""
        return html

    def render_to_dash_figure(self, chart_config: Dict[str, Any]) -> Dict[str, Any]:
        """渲染为Dash Graph组件的figure格式。

        转换为Dash的dcc.Graph组件可以使用的figure格式。

        参数:
            chart_config: ECharts配置字典

        返回:
            dict: Dash figure字典，包含'data'和'layout'
        """
        # 将ECharts配置转换为Plotly格式
        # 注意：这里返回的是简化版本，实际项目中可能需要更复杂的转换

        figure = {
            "data": [],
            "layout": {
                "title": chart_config.get("title", {}).get("text", ""),
                "template": "plotly_white" if self.theme == "light" else "plotly_dark",
                "height": 400,
            }
        }

        return figure
