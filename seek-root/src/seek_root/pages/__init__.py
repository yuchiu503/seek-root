"""Dash页面模块初始化文件。

导出页面创建函数。
"""

from seek_root.pages.home import create_home_page
from seek_root.pages.data_upload import create_data_page
from seek_root.pages.analysis import create_analysis_page
from seek_root.pages.results import create_results_page
from seek_root.pages.about import create_about_page

__all__ = [
    "create_home_page",
    "create_data_page",
    "create_analysis_page",
    "create_results_page",
    "create_about_page",
]
