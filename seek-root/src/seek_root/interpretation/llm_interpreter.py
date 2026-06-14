"""LLM业务解读模块。

本模块负责将统计结果翻译成业务人员能理解的语言，
使用OpenAI兼容的LLM API生成可读性强的分析报告。

类:
    LLMInterpreter: LLM业务解读器
"""

from typing import Any, Dict, Optional
import json

from seek_root.config.settings import settings
from seek_root.core.base import AnalysisResult, CausalMethod


class LLMInterpreter:
    """LLM业务解读器类。

    使用大语言模型将因果推断的统计结果解读为业务语言。

    参数:
        api_key (str, optional): LLM API密钥，默认使用配置中的密钥
        api_base (str, optional): LLM API地址，默认使用配置中的地址
        model (str, optional): 模型名称，默认使用配置中的模型

    示例:
        >>> interpreter = LLMInterpreter()
        >>> result = analyzer.get_result()
        >>> interpretation = interpreter.interpret(result)
        >>> print(interpretation["conclusion"])
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        """初始化LLM解读器。

        参数:
            api_key: API密钥
            api_base: API地址
            model: 模型名称
        """
        self.api_key = api_key or settings.llm_api_key
        self.api_base = api_base or settings.llm_api_base
        self.model = model or settings.llm_model

    def interpret(self, result: AnalysisResult) -> Dict[str, str]:
        """解读分析结果。

        根据分析结果，生成业务友好的解读文本。

        参数:
            result: 分析结果对象

        返回:
            dict: 包含以下键的字典:
                - conclusion: 一句话总结
                - interpretation: 详细解读
                - business_recommendation: 业务建议
        """
        if not self.api_key:
            # 如果没有API密钥，返回默认解读
            return self._generate_default_interpretation(result)

        try:
            return self._generate_llm_interpretation(result)
        except Exception as e:
            # LLM调用失败时，返回默认解读
            print(f"LLM解读失败: {e}")
            return self._generate_default_interpretation(result)

    def _generate_default_interpretation(self, result: AnalysisResult) -> Dict[str, str]:
        """生成默认解读（当LLM不可用时）。

        使用规则模板生成基础解读。

        参数:
            result: 分析结果对象

        返回:
            dict: 解读字典
        """
        method_name = result.method.name_cn
        effect = result.effect_estimate
        significant = "显著" if result.is_significant else "不显著"

        # 一句话结论
        effect_direction = "正向" if effect > 0 else "负向"
        conclusion = (
            f"本次{result.method.name_cn}分析显示，处理效应为{effect_direction}，"
            f"效应值为{abs(effect):.4f}，统计上{significant}（p值={result.p_value:.4f}）。"
        )

        # 详细解读
        interpretation = (
            f"分析方法：{method_name}\n"
            f"处理组样本量：{result.treatment_size}\n"
            f"对照组样本量：{result.control_size}\n"
            f"总样本量：{result.sample_size}\n"
            f"效应估计值：{effect:.4f}\n"
            f"标准误：{result.standard_error:.4f}\n"
            f"95%置信区间：[{result.confidence_interval[0]:.4f}, {result.confidence_interval[1]:.4f}]\n"
            f"p值：{result.p_value:.4f}\n"
            f"统计显著性：{significant}"
        )

        # 业务建议
        if result.is_significant:
            if effect > 0:
                recommendation = (
                    f"建议采纳该处理方案。数据表明该方案对目标指标有显著的正向影响，"
                    f"预期提升幅度为{abs(effect):.2f}个单位。"
                )
            else:
                recommendation = (
                    f"建议重新评估该处理方案。数据显示该方案对目标指标有显著的负向影响，"
                    f"预期下降幅度为{abs(effect):.2f}个单位。"
                )
        else:
            recommendation = (
                f"建议进一步分析。目前数据显示处理效应在统计上不显著，"
                f"可能需要更大的样本量或不同的分析方法。"
            )

        return {
            "conclusion": conclusion,
            "interpretation": interpretation,
            "business_recommendation": recommendation,
        }

    def _generate_llm_interpretation(self, result: AnalysisResult) -> Dict[str, str]:
        """使用LLM生成解读。

        调用OpenAI兼容API生成业务友好的解读。

        参数:
            result: 分析结果对象

        返回:
            dict: 解读字典
        """
        from openai import OpenAI

        client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_base,
        )

        # 构建提示词
        prompt = self._build_prompt(result)

        # 调用LLM
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "你是一位专业的数据分析师，擅长将统计结果翻译成业务人员能理解的语言。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=1000,
        )

        content = response.choices[0].message.content

        # 解析结果
        return self._parse_llm_response(content, result)

    def _build_prompt(self, result: AnalysisResult) -> str:
        """构建LLM提示词。

        根据分析结果构建详细的提示词。

        参数:
            result: 分析结果对象

        返回:
            str: 提示词文本
        """
        method_desc = result.method.description
        effect = result.effect_estimate
        p_value = result.p_value
        ci_lower, ci_upper = result.confidence_interval
        significant = "是" if result.is_significant else "否"

        prompt = f"""请帮我解读以下{result.method.name_cn}分析结果：

分析方法说明：{method_desc}

分析结果：
- 处理组样本量：{result.treatment_size}
- 对照组样本量：{result.control_size}
- 总样本量：{result.sample_size}
- 处理效应（ATT/ATE）：{effect:.4f}
- 标准误：{result.standard_error:.4f}
- 95%置信区间：[{ci_lower:.4f}, {ci_upper:.4f}]
- p值：{p_value:.4f}
- 是否统计显著：{significant}

请生成以下内容：
1. 一句话总结：用通俗易懂的语言概括分析的主要发现
2. 详细解读：解释每个指标的 business meaning
3. 业务建议：基于分析结果，给出具体的业务建议

请用中文回答，保持专业但易懂的语言风格。"""

        return prompt

    def _parse_llm_response(
        self,
        content: str,
        result: AnalysisResult,
    ) -> Dict[str, str]:
        """解析LLM响应。

        从LLM返回的文本中提取各部分内容。

        参数:
            content: LLM返回的原始文本
            result: 原始分析结果（用于补充信息）

        返回:
            dict: 解读字典
        """
        # 简化实现：直接使用LLM返回的完整内容
        # 实际可以根据内容中的标记（如### 总结 ###）来解析

        # 尝试按段落分割
        lines = content.split("\n")

        conclusion = ""
        interpretation = ""
        recommendation = ""

        current_section = ""
        for line in lines:
            line = line.strip()
            if "总结" in line or "结论" in line:
                current_section = "conclusion"
            elif "详细" in line or "解读" in line or "说明" in line:
                current_section = "interpretation"
            elif "建议" in line:
                current_section = "recommendation"
            elif line and current_section:
                if current_section == "conclusion":
                    conclusion += line + " "
                elif current_section == "interpretation":
                    interpretation += line + " "
                elif current_section == "recommendation":
                    recommendation += line + " "

        # 如果解析失败，使用默认结构
        if not conclusion:
            conclusion = content[:200] + "..."

        if not interpretation:
            interpretation = content

        if not recommendation:
            recommendation = self._generate_default_interpretation(result)["business_recommendation"]

        return {
            "conclusion": conclusion.strip(),
            "interpretation": interpretation.strip(),
            "business_recommendation": recommendation.strip(),
        }

    def batch_interpret(
        self,
        results: list[AnalysisResult],
    ) -> list[Dict[str, str]]:
        """批量解读多个分析结果。

        参数:
            results: 分析结果列表

        返回:
            list[dict]: 解读结果列表
        """
        interpretations = []
        for result in results:
            interpretations.append(self.interpret(result))
        return interpretations
