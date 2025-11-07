"""
Free embeddings using sentence-transformers (lazy loading).
"""
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# Lazy import to avoid startup issues
_sentence_transformer_model = None


class EmbeddingGenerator:
    """
    Generate embeddings using FREE sentence transformers.
    No API key required!
    """
    
    def __init__(self, model: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding generator.
        
        Args:
            model: Sentence transformer model name
        """
        self.model_name = model
        self._model = None
        logger.info(f"Embedding generator configured: {model} (100% FREE)")
    
    @property
    def model(self):
        """Lazy load the model only when needed."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading embedding model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
                logger.info(f"✅ Model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                raise
        return self._model
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        embedding = self.model.encode(text, convert_to_tensor=False)
        return embedding.tolist()
    
    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for batch of texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            
        Returns:
            List of embedding vectors
        """
        logger.info(f"Embedding {len(texts)} texts...")
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_tensor=False,
            show_progress_bar=False
        )
        return [e.tolist() for e in embeddings]
    
    @property
    def embedding_dimension(self) -> int:
        """Get embedding dimension for the model."""
        return self.model.get_sentence_embedding_dimension()