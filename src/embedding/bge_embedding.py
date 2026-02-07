"""BGE-M3嵌入模型升级模块."""

import os
from typing import List, Union

import numpy as np


class BGEEmbeddingModel:
    """BGE-M3多语言嵌入模型.

    优势:
    - 支持中文优化
    - 8192维向量（高精度）
    - 支持长文本（8192 tokens）
    - 多功能（检索、重排序、分类）

    模型: BAAI/bge-m3
    """

    def __init__(self, model_name: str = "BAAI/bge-m3", device: str = "cpu"):
        """初始化BGE嵌入模型.

        Args:
            model_name: 模型名称
            device: 运行设备（cpu/cuda/mps）
        """
        self.model_name = model_name
        self.device = device
        self.model = None
        self.dimension = 1024  # BGE-M3默认1024维

        # 延迟加载，避免启动时间过长
        self._lazy_loaded = False

    def _load_model(self):
        """延迟加载模型."""
        if self._lazy_loaded:
            return

        try:
            from sentence_transformers import SentenceTransformer

            print(f"📦 加载BGE-M3模型 ({self.model_name})...")

            # 检测MPS（Apple Silicon GPU）
            if self.device == "auto":
                import torch
                if torch.backends.mps.is_available():
                    self.device = "mps"
                elif torch.cuda.is_available():
                    self.device = "cuda"
                else:
                    self.device = "cpu"

            # 加载模型
            self.model = SentenceTransformer(
                self.model_name,
                device=self.device
            )

            self._lazy_loaded = True
            print(f"✅ BGE-M3模型加载成功 (设备: {self.device})")

        except ImportError:
            print("❌ sentence-transformers未安装")
            print("   安装: pip install sentence-transformers")
            raise
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            raise

    def encode(
        self,
        texts: Union[str, list[str]],
        normalize: bool = True,
        show_progress: bool = False
    ) -> Union[list[float], list[list[float]]]:
        """编码文本为向量.

        Args:
            texts: 单个文本或文本列表
            normalize: 是否归一化
            show_progress: 是否显示进度

        Returns:
            向量或向量列表
        """
        self._load_model()

        # 单个文本转换为列表
        single_input = isinstance(texts, str)
        if single_input:
            texts = [texts]

        # 编码
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=normalize,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )

        # 转换为列表
        if single_input:
            return embeddings[0].tolist()
        else:
            return [emb.tolist() for emb in embeddings]

    def encode_query(self, query: str) -> List[float]:
        """编码查询文本（添加指令前缀）.

        Args:
            query: 查询文本

        Returns:
            向量表示
        """
        # BGE-M3为查询添加指令前缀
        instruction = "为这个句子生成表示以用于检索相关文章："
        query_with_instruction = f"{instruction}{query}"

        return self.encode(query_with_instruction)

    def compute_similarity(
        self,
        query_embedding: List[float],
        document_embeddings: List[List[float]]
    ) -> List[float]:
        """计算查询与文档的相似度.

        Args:
            query_embedding: 查询向量
            document_embeddings: 文档向量列表

        Returns:
            相似度分数列表
        """
        query_vec = np.array(query_embedding)
        doc_vecs = np.array(document_embeddings)

        # 点积（向量已归一化，等价于cosine相似度）
        similarities = np.dot(doc_vecs, query_vec)

        return similarities.tolist()

    def get_dimension(self) -> int:
        """获取向量维度."""
        return self.dimension

    def is_available(self) -> bool:
        """检查模型是否可用."""
        try:
            self._load_model()
            return True
        except Exception:
            return False


class OpenAIEmbeddingModel:
    """OpenAI嵌入模型（云端方案）.

    优势:
    - 最高精度（3072维）
    - 无需本地资源
    - API稳定可靠

    劣势:
    - 需要付费
    - 数据需上传云端
    """

    def __init__(self, api_key: str = None, model: str = "text-embedding-3-large"):
        """初始化OpenAI嵌入模型.

        Args:
            api_key: OpenAI API密钥
            model: 模型名称
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.dimension = 3072 if "large" in model else 1536

    def encode(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """编码文本为向量."""
        if not self.api_key:
            raise ValueError("OpenAI API密钥未设置")

        import openai

        client = openai.OpenAI(api_key=self.api_key)

        single_input = isinstance(texts, str)
        if single_input:
            texts = [texts]

        response = client.embeddings.create(
            model=self.model,
            input=texts
        )

        embeddings = [item.embedding for item in response.data]

        if single_input:
            return embeddings[0]
        else:
            return embeddings

    def is_available(self) -> bool:
        """检查模型是否可用."""
        return bool(self.api_key)


# 全局模型实例
_bge_model = None

def get_bge_model() -> BGEEmbeddingModel:
    """获取BGE模型单例."""
    global _bge_model
    if _bge_model is None:
        _bge_model = BGEEmbeddingModel(device="auto")
    return _bge_model


# 测试函数
def test_bge_embedding():
    """测试BGE嵌入模型."""
    print("\n🧪 测试BGE-M3嵌入模型")
    print("=" * 50)

    try:
        model = BGEEmbeddingModel(device="auto")

        # 测试文本
        texts = [
            "GMV是什么",
            "最近7天的成交金额",
            "本月营收总和"
        ]

        print(f"\n编码 {len(texts)} 个文本...")
        embeddings = model.encode(texts, show_progress=True)

        print(f"✅ 编码成功")
        print(f"   向量维度: {len(embeddings[0])}")
        print(f"   向量数量: {len(embeddings)}")

        # 测试相似度计算
        query = "GMV"
        query_emb = model.encode_query(query)

        similarities = model.compute_similarity(query_emb, embeddings)

        print(f"\n查询: {query}")
        print("-" * 50)
        for text, sim in zip(texts, similarities):
            print(f"   {text}: {sim:.4f}")

        print("\n" + "=" * 50)

    except Exception as e:
        print(f"❌ 测试失败: {e}")


if __name__ == "__main__":
    test_bge_embedding()
