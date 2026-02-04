"""指标向量化器.

使用 m3e-base 模型将指标元数据转换为向量表示.
"""

from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from src.recall.vector.models import MetricMetadata


class MetricVectorizer:
    """指标向量化器.

    使用 m3e-base 模型将指标元数据的多个字段拼接后生成向量.
    支持单条和批量向量化，模型延迟加载以避免导入时初始化.

    Attributes:
        model_name: 使用的 embedding 模型名称
        _model: SentenceTransformer 模型实例（延迟加载）
    """

    def __init__(self, model_name: str = "m3e-base") -> None:
        """初始化向量化器.

        Args:
            model_name: 预训练模型名称，默认为 m3e-base
        """
        self.model_name = model_name
        self._model: Optional[SentenceTransformer] = None

    @property
    def model(self) -> SentenceTransformer:
        """获取模型实例（延迟加载）.

        Returns:
            SentenceTransformer 模型实例

        Raises:
            RuntimeError: 如果模型加载失败
        """
        if self._model is None:
            try:
                self._model = SentenceTransformer(self.model_name)
            except Exception as e:
                msg = f"Failed to load model {self.model_name}: {e}"
                raise RuntimeError(msg) from e
        return self._model

    def _build_text_template(self, metadata: MetricMetadata) -> str:
        """构建向量化文本模板.

        Args:
            metadata: 指标元数据

        Returns:
            拼接后的文本字符串
        """
        synonyms_str = "、".join(metadata.synonyms) if metadata.synonyms else "无"
        formula_str = metadata.formula if metadata.formula else "无"

        template = f"""指标名称: {metadata.name}
指标编码: {metadata.code}
业务含义: {metadata.description}
同义词: {synonyms_str}
业务域: {metadata.domain}
计算公式: {formula_str}"""

        return template.strip()

    def vectorize(self, metadata: MetricMetadata) -> np.ndarray:
        """单条指标向量化.

        Args:
            metadata: 指标元数据

        Returns:
            768维向量

        Example:
            >>> vectorizer = MetricVectorizer()
            >>> metric = MetricMetadata(
            ...     name="GMV",
            ...     code="gmv",
            ...     description="成交总额",
            ...     synonyms=["成交金额", "交易额"],
            ...     domain="电商"
            ... )
            >>> vec = vectorizer.vectorize(metric)
            >>> vec.shape
            (768,)
        """
        text = self._build_text_template(metadata)
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding

    def vectorize_batch(
        self,
        metrics: list[MetricMetadata],
        show_progress: bool = True,
    ) -> np.ndarray:
        """批量指标向量化.

        Args:
            metrics: 指标元数据列表
            show_progress: 是否显示进度条

        Returns:
            shape为 (n, 768) 的向量矩阵，n为指标数量

        Example:
            >>> vectorizer = MetricVectorizer()
            >>> metrics = [metric1, metric2, metric3]
            >>> embeddings = vectorizer.vectorize_batch(metrics)
            >>> embeddings.shape
            (3, 768)
        """
        if not metrics:
            return np.array([]).reshape(0, 768)

        texts = [self._build_text_template(metric) for metric in metrics]

        if show_progress:
            # 使用 sentence_transformers 的批量编码，手动添加进度条
            embeddings = self.model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=show_progress,
                batch_size=32,
            )
        else:
            embeddings = self.model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False,
                batch_size=32,
            )

        return embeddings

    @property
    def embedding_dim(self) -> int:
        """获取向量维度.

        Returns:
            向量维度（m3e-base 为 768）
        """
        return self.model.get_sentence_embedding_dimension()
