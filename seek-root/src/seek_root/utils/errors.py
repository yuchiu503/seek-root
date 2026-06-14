"""Seek Root 错误定义模块。

定义应用程序中使用的所有自定义异常类。

异常类:
    SeekRootError: 应用程序基础异常类
    DataLoadError: 数据加载相关错误
    ValidationError: 数据验证相关错误
    AnalysisError: 分析执行相关错误
"""


class SeekRootError(Exception):
    """Seek Root应用程序的基础异常类。

    所有自定义异常的基类，继承自Python内置Exception类。

    参数:
        message (str): 错误消息
        details (dict, optional): 错误的详细信息
    """

    def __init__(self, message: str, details: dict = None) -> None:
        """初始化基础异常。

        参数:
            message: 错误消息
            details: 错误详情字典
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        """返回异常的字符串表示。

        返回:
            str: 错误消息
        """
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


class DataLoadError(SeekRootError):
    """数据加载错误。

    当数据文件加载失败时抛出，
    包括文件不存在、格式错误、编码问题等。

    参数:
        message (str): 错误消息
        file_name (str, optional): 出错的文件名
        file_type (str, optional): 文件类型
    """

    def __init__(
        self,
        message: str,
        file_name: str = None,
        file_type: str = None,
    ) -> None:
        """初始化数据加载错误。

        参数:
            message: 错误消息
            file_name: 出错的文件名
            file_type: 文件类型
        """
        details = {}
        if file_name:
            details["file_name"] = file_name
        if file_type:
            details["file_type"] = file_type

        super().__init__(message, details)
        self.file_name = file_name
        self.file_type = file_type


class ValidationError(SeekRootError):
    """数据验证错误。

    当数据不满足分析方法要求时抛出，
    包括缺少必需列、数据类型错误、样本量不足等。

    参数:
        message (str): 错误消息
        validation_type (str, optional): 验证类型（如'did', 'psm'等）
        column_name (str, optional): 出问题的列名
    """

    def __init__(
        self,
        message: str,
        validation_type: str = None,
        column_name: str = None,
    ) -> None:
        """初始化数据验证错误。

        参数:
            message: 错误消息
            validation_type: 验证类型
            column_name: 出问题的列名
        """
        details = {}
        if validation_type:
            details["validation_type"] = validation_type
        if column_name:
            details["column_name"] = column_name

        super().__init__(message, details)
        self.validation_type = validation_type
        self.column_name = column_name


class AnalysisError(SeekRootError):
    """分析执行错误。

    当因果推断分析执行过程中发生错误时抛出，
    包括模型拟合失败、数值计算错误等。

    参数:
        message (str): 错误消息
        method (str, optional): 正在执行的分析方法
        step (str, optional): 发生错误的步骤
    """

    def __init__(
        self,
        message: str,
        method: str = None,
        step: str = None,
    ) -> None:
        """初始化分析执行错误。

        参数:
            message: 错误消息
            method: 正在执行的分析方法
            step: 发生错误的步骤
        """
        details = {}
        if method:
            details["method"] = method
        if step:
            details["step"] = step

        super().__init__(message, details)
        self.method = method
        self.step = step
