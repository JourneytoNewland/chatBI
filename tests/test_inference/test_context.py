"""会话上下文测试."""

from datetime import datetime, timedelta


class TestConversationContext:
    """会话上下文测试."""

    def setup_method(self):
        """测试前准备."""
        from src.inference.context import ConversationManager
        from src.inference.intent import IntentRecognizer

        self.manager = ConversationManager()
        self.recognizer = IntentRecognizer()
        # 清理之前的测试数据
        self.manager._conversations.clear()

    def test_single_turn_context(self):
        """测试单轮对话."""
        ctx = self.manager.get_or_create("test_conv")
        intent1 = self.recognizer.recognize("GMV")
        ctx.add_turn("GMV", intent1)

        # 检查上下文
        assert len(ctx.turns) == 1
        assert ctx.get_last_intent().core_query == "GMV"

    def test_pronoun_resolution(self):
        """测试代词解析."""
        ctx = self.manager.get_or_create("test_conv")

        # 第一轮：定义实体（将"GMV"映射到代词"它"）
        intent1 = self.recognizer.recognize("GMV")
        ctx.entities["它"] = "GMV"  # 将代词"它"映射到实体"GMV"
        ctx.add_turn("GMV", intent1)

        # 第二轮：引用实体
        resolved = ctx.resolve_reference("它的增长率")
        assert "GMV" in resolved

    def test_multi_turn_context(self):
        """测试多轮对话."""
        ctx = self.manager.get_or_create("test_conv")

        # 添加3轮对话
        for i in range(3):
            intent = self.recognizer.recognize(f"查询{i}")
            ctx.add_turn(f"查询{i}", intent)

        assert len(ctx.turns) == 3

    def test_context_max_turns(self):
        """测试最大轮数限制."""
        ctx = self.manager.get_or_create("test_conv")

        # 添加7轮对话
        for i in range(7):
            intent = self.recognizer.recognize(f"查询{i}")
            ctx.add_turn(f"查询{i}", intent)

        # 应该只保留最近5轮
        assert len(ctx.turns) == 5

    def test_conversation_isolation(self):
        """测试会话隔离."""
        ctx1 = self.manager.get_or_create("conv1")
        ctx2 = self.manager.get_or_create("conv2")

        intent = self.recognizer.recognize("query1")
        ctx1.add_turn("query1", intent)

        intent2 = self.recognizer.recognize("query2")
        ctx2.add_turn("query2", intent2)

        assert len(ctx1.turns) == 1
        assert len(ctx2.turns) == 1

    def test_empty_context(self):
        """测试空上下文."""
        ctx = self.manager.get_or_create("empty_conv")
        last = ctx.get_last_intent()
        assert last is None

    def test_unknown_pronoun(self):
        """测试未知代词."""
        ctx = self.manager.get_or_create("test_conv")
        resolved = ctx.resolve_reference("它的增长率")
        # 没有定义"它"，应该保持原样
        assert "它" in resolved

    def test_cleanup_old_conversations(self):
        """测试上下文清理."""
        # 创建一个过期会话
        ctx = self.manager.get_or_create("old_conv")

        # 手动添加一个旧的对话轮次
        from src.inference.context import ConversationTurn

        old_intent = self.recognizer.recognize("old")
        ctx.turns.append(ConversationTurn(query="old", intent=old_intent, timestamp=datetime.now() - timedelta(hours=25)))

        # 清理过期会话
        self.manager.cleanup_old(max_age_hours=24)

        # 旧会话应该被清理
        assert "old_conv" not in self.manager._conversations
