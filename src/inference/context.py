"""会话上下文管理模块."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class ConversationTurn:
    """单轮对话."""

    query: str
    intent: "QueryIntent"
    timestamp: datetime


@dataclass
class ConversationContext:
    """会话上下文管理器."""

    conversation_id: str
    turns: list[ConversationTurn] = field(default_factory=list)
    entities: dict[str, str] = field(default_factory=dict)  # {"它": "GMV"}
    max_turns: int = 5  # 最多保留5轮历史

    def add_turn(self, query: str, intent: "QueryIntent") -> None:
        """添加新的对话轮次.

        Args:
            query: 用户查询
            intent: 识别出的意图
        """
        self.turns.append(ConversationTurn(query=query, intent=intent, timestamp=datetime.now()))

        # 只保留最近N轮
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]

    def resolve_reference(self, query: str) -> str:
        """解析指代关系.

        Args:
            query: 原始查询

        Returns:
            解析后的查询（代词被替换为实体）
        """
        resolved_query = query

        # 简单规则：替换代词
        for pronoun, entity in self.entities.items():
            if pronoun in resolved_query:
                resolved_query = resolved_query.replace(pronoun, entity)

        return resolved_query

    def get_last_intent(self) -> Optional["QueryIntent"]:
        """获取上一轮的意图.

        Returns:
            上一轮的QueryIntent，如果没有历史则返回None
        """
        if not self.turns:
            return None
        return self.turns[-1].intent

    def merge_intent(self, current_intent: "QueryIntent", last_intent: "QueryIntent") -> "QueryIntent":
        """合并当前意图与上一轮意图（下钻逻辑）.

        Args:
            current_intent: 当前识别出的意图
            last_intent: 上一轮的意图

        Returns:
            合并后的意图
        """
        # 1. 继承核心指标 (如果当前没有明确的核心指标，或者核心指标是通用疑问词)
        # 简单的启发式：如果 core_query 为空，或者长度很短且没有实际指标名
        # 更严谨的做法是检查 core_query 是否在指标库中，这里简化处理
        if not current_intent.core_query or len(current_intent.core_query) < 2:
            current_intent.core_query = last_intent.core_query
            print(f"🔗 Context Merge: Inherited metric '{last_intent.core_query}'")

        # 2. 继承时间范围 (如果当前没有指定时间)
        if not current_intent.time_range:
            current_intent.time_range = last_intent.time_range
            current_intent.time_granularity = last_intent.time_granularity
            print(f"🔗 Context Merge: Inherited time range")

        # 3. 合并过滤条件 (增量合并)
        if last_intent.filters:
            # 浅拷贝上一轮的过滤器，然后用当前的覆盖（如果有冲突）
            merged_filters = last_intent.filters.copy()
            merged_filters.update(current_intent.filters)
            current_intent.filters = merged_filters
            print(f"🔗 Context Merge: Merged filters {merged_filters}")

        # 4. 维度通常不继承，因为下钻往往是换个维度看
        # 但如果当前完全没有维度，可以考虑继承？暂时不继承，以免混淆

        return current_intent


class ConversationManager:
    """多会话管理器（全局单例）."""

    _instance: Optional["ConversationManager"] = None
    _conversations: dict[str, ConversationContext] = {}

    def __new__(cls) -> "ConversationManager":
        """确保单例模式."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_or_create(self, conversation_id: str) -> ConversationContext:
        """获取或创建会话.

        Args:
            conversation_id: 会话ID

        Returns:
            会话上下文对象
        """
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = ConversationContext(conversation_id=conversation_id)
        return self._conversations[conversation_id]

    def cleanup_old(self, max_age_hours: int = 24) -> None:
        """清理过期会话.

        Args:
            max_age_hours: 会话最大保留时间（小时）
        """
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        self._conversations = {
            cid: ctx for cid, ctx in self._conversations.items() if ctx.turns and ctx.turns[-1].timestamp > cutoff
        }


# 全局单例实例
conversation_manager = ConversationManager()
