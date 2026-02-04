"""本体验证模块."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from src.rerank.models import Candidate, QueryContext


class ValidationStatus(Enum):
    """验证状态."""

    PASSED = "PASSED"
    WARNING = "WARNING"
    FAILED = "FAILED"


@dataclass
class ValidationResult:
    """验证结果.

    Attributes:
        status: 验证状态
        check_type: 检查类型
        message: 验证消息
        suggestion: 改进建议（可选）
    """

    status: ValidationStatus
    check_type: str
    message: str
    suggestion: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "status": self.status.value,
            "check_type": self.check_type,
            "message": self.message,
            "suggestion": self.suggestion,
        }


class Validator(ABC):
    """验证器基类."""

    @abstractmethod
    def validate(
        self,
        candidate: Candidate,
        context: QueryContext,
    ) -> ValidationResult:
        """验证候选指标.

        Args:
            candidate: 候选指标
            context: 查询上下文

        Returns:
            验证结果
        """

    @property
    def name(self) -> str:
        """获取验证器名称."""
        return self.__class__.__name__


class DimensionCompatibilityValidator(Validator):
    """维度兼容性验证器."""

    def validate(
        self,
        candidate: Candidate,
        context: QueryContext,
    ) -> ValidationResult:
        """验证维度兼容性."""
        # 简化实现：检查是否有明显的不兼容
        # 实际应用中可以查询指标维度信息

        # 示例：如果查询包含"按天"，但指标是实时指标
        if "天" in context.query and "实时" in candidate.description:
            return ValidationResult(
                status=ValidationStatus.WARNING,
                check_type="dimension_compatibility",
                message="查询要求按天聚合，但指标是实时指标",
                suggestion="建议使用累计指标或添加时间维度",
            )

        return ValidationResult(
            status=ValidationStatus.PASSED,
            check_type="dimension_compatibility",
            message="维度兼容",
        )


class TimeGranularityValidator(Validator):
    """时间粒度验证器."""

    def validate(
        self,
        candidate: Candidate,
        context: QueryContext,
    ) -> ValidationResult:
        """验证时间粒度."""
        query_lower = context.query.lower()

        # 检测查询中的时间粒度要求
        time_keywords = {
            "实时": "实时",
            "小时": "小时",
            "天": "天",
            "周": "周",
            "月": "月",
            "季": "季",
            "年": "年",
        }

        required_granularity = None
        for keyword, granularity in time_keywords.items():
            if keyword in query_lower:
                required_granularity = granularity
                break

        if required_granularity:
            # 检查指标描述是否匹配
            if required_granularity not in candidate.description:
                return ValidationResult(
                    status=ValidationStatus.WARNING,
                    check_type="time_granularity",
                    message=f"查询要求{required_granularity}级数据，指标可能不匹配",
                    suggestion=f"请确认指标是否支持{required_granularity}粒度",
                )

        return ValidationResult(
            status=ValidationStatus.PASSED,
            check_type="time_granularity",
            message="时间粒度匹配",
        )


class DataFreshnessValidator(Validator):
    """数据新鲜度验证器."""

    def validate(
        self,
        candidate: Candidate,
        context: QueryContext,
    ) -> ValidationResult:
        """验证数据新鲜度."""
        # 简化实现：基于指标名称判断
        # 实际应用中可以查询数据更新时间

        # 如果是"实时"类指标，但查询要求历史数据
        if "实时" in candidate.name and "历史" in context.query:
            return ValidationResult(
                status=ValidationStatus.WARNING,
                check_type="data_freshness",
                message="指标为实时指标，查询可能需要历史数据",
                suggestion="建议使用累计指标或历史快照",
            )

        return ValidationResult(
            status=ValidationStatus.PASSED,
            check_type="data_freshness",
            message="数据新鲜度正常",
        )


class PermissionValidator(Validator):
    """权限验证器."""

    def validate(
        self,
        candidate: Candidate,
        context: QueryContext,
    ) -> ValidationResult:
        """验证权限."""
        # 简化实现：基于业务域判断
        # 实际应用中需要查询用户权限系统

        # 示例：某些敏感域需要特殊权限
        sensitive_domains = ["财务", "风控", "安全"]

        if candidate.domain in sensitive_domains:
            return ValidationResult(
                status=ValidationStatus.WARNING,
                check_type="permission",
                message=f"指标属于敏感域（{candidate.domain}），需要验证权限",
                suggestion="请确认用户有权限访问该域指标",
            )

        return ValidationResult(
            status=ValidationStatus.PASSED,
            check_type="permission",
            message="权限验证通过",
        )


class ValidationPipeline:
    """验证流水线.

    运行多个验证器并汇总结果。
    """

    # 标准验证器集
    STANDARD_VALIDATORS = [
        DimensionCompatibilityValidator(),
        TimeGranularityValidator(),
        DataFreshnessValidator(),
        PermissionValidator(),
    ]

    def __init__(self, validators: list[Validator] | None = None) -> None:
        """初始化验证流水线.

        Args:
            validators: 验证器列表（默认使用标准验证器集）
        """
        self.validators = validators or self.STANDARD_VALIDATORS.copy()

    def validate(
        self,
        candidate: Candidate,
        context: QueryContext,
    ) -> list[ValidationResult]:
        """运行所有验证器.

        Args:
            candidate: 候选指标
            context: 查询上下文

        Returns:
            验证结果列表
        """
        results = []
        for validator in self.validators:
            try:
                result = validator.validate(candidate, context)
                results.append(result)
            except Exception as e:
                # 验证器失败时返回 WARNING
                results.append(
                    ValidationResult(
                        status=ValidationStatus.WARNING,
                        check_type=validator.name,
                        message=f"验证失败: {e}",
                    )
                )

        return results

    def has_failed(self, results: list[ValidationResult]) -> bool:
        """检查是否有 FAILED 状态.

        Args:
            results: 验证结果列表

        Returns:
            是否有 FAILED
        """
        return any(r.status == ValidationStatus.FAILED for r in results)

    def has_warning(self, results: list[ValidationResult]) -> bool:
        """检查是否有 WARNING 状态.

        Args:
            results: 验证结果列表

        Returns:
            是否有 WARNING
        """
        return any(r.status == ValidationStatus.WARNING for r in results)
