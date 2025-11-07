"""
FAISS-based vector store for RAG pipeline.
"""
import logging
import json
import pickle
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

try:
    import faiss
    import numpy as np
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

from .embeddings import EmbeddingGenerator
from ..config.settings import settings
from ..core.exceptions import VectorStoreError
from ..core.telemetry import track_time

logger = logging.getLogger(__name__)


class FAISSVectorStore:
    """
    FAISS-based vector store for semantic search.
    
    This is part of Lab 4 - Vector DB & RAG index.
    """
    
    def __init__(
        self,
        store_path: Optional[Path] = None,
        embedding_generator: Optional[EmbeddingGenerator] = None
    ):
        """
        Initialize FAISS vector store.
        
        Args:
            store_path: Path to store index files
            embedding_generator: Embedding generator instance
        """
        if not FAISS_AVAILABLE:
            raise VectorStoreError(
                "FAISS not available. Install with: pip install faiss-cpu",
                error_code="FAISS_NOT_INSTALLED"
            )
        
        self.store_path = store_path or settings.vector_store_dir / "faiss"
        self.store_path.mkdir(parents=True, exist_ok=True)
        
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        self.dimension = self.embedding_generator.embedding_dimension
        
        # FAISS index
        self.index: Optional[faiss.Index] = None
        
        # Metadata storage (maps index ID to document metadata)
        self.metadata: Dict[int, Dict[str, Any]] = {}
        
        # Document chunks (maps index ID to text)
        self.documents: Dict[int, str] = {}
        
        self.next_id = 0
        
        logger.info(f"Initialized FAISS vector store at {self.store_path}")
    
    def create_index(self, index_type: str = "flat"):
        """
        Create new FAISS index.
        
        Args:
            index_type: Type of index ('flat', 'ivf', 'hnsw')
        """
        if index_type == "flat":
            # Simple flat L2 index (exact search)
            self.index = faiss.IndexFlatL2(self.dimension)
        
        elif index_type == "ivf":
            # IVF (Inverted File) index for faster search
            quantizer = faiss.IndexFlatL2(self.dimension)
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, 100)
            
            # IVF requires training
            logger.info("IVF index created (requires training before use)")
        
        elif index_type == "hnsw":
            # HNSW (Hierarchical Navigable Small World) for very fast search
            self.index = faiss.IndexHNSWFlat(self.dimension, 32)
        
        else:
            raise VectorStoreError(
                f"Unsupported index type: {index_type}",
                error_code="INVALID_INDEX_TYPE"
            )
        
        logger.info(f"Created {index_type} index with dimension {self.dimension}")
    
    @track_time("add_documents")
    def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> List[int]:
        """
        Add documents to vector store.
        
        Args:
            texts: List of text chunks
            metadatas: Optional metadata for each chunk
            
        Returns:
            List of document IDs
        """
        if not self.index:
            self.create_index()
        
        logger.info(f"Adding {len(texts)} documents to vector store")
        
        # Generate embeddings
        embeddings = self.embedding_generator.embed_batch(texts)
        
        # Convert to numpy array
        embeddings_array = np.array(embeddings, dtype=np.float32)
        
        # Add to index
        self.index.add(embeddings_array)
        
        # Store metadata and documents
        ids = []
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            doc_id = self.next_id
            self.next_id += 1
            
            self.documents[doc_id] = text
            
            if metadatas and i < len(metadatas):
                self.metadata[doc_id] = metadatas[i]
            else:
                self.metadata[doc_id] = {}
            
            # Add timestamp
            self.metadata[doc_id]["indexed_at"] = datetime.utcnow().isoformat() + "Z"
            
            ids.append(doc_id)
        
        logger.info(f"Successfully added {len(ids)} documents")
        
        return ids
    
    @track_time("search")
    def search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents.
        
        Args:
            query: Search query text
            k: Number of results to return
            filter_metadata: Optional metadata filters
            
        Returns:
            List of search results with scores and metadata
        """
        if not self.index or self.index.ntotal == 0:
            logger.warning("Vector store is empty")
            return []
        
        logger.info(f"Searching for: {query[:100]}...")
        
        # Generate query embedding
        query_embedding = self.embedding_generator.embed_text(query)
        query_array = np.array([query_embedding], dtype=np.float32)
        
        # Search
        distances, indices = self.index.search(query_array, k)
        
        # Format results
        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue
            
            doc_id = int(idx)
            
            # Apply metadata filters
            if filter_metadata:
                metadata = self.metadata.get(doc_id, {})
                if not self._matches_filter(metadata, filter_metadata):
                    continue
            
            result = {
                "id": doc_id,
                "text": self.documents.get(doc_id, ""),
                "score": float(distance),
                "similarity": 1.0 / (1.0 + float(distance)),  # Convert distance to similarity
                "metadata": self.metadata.get(doc_id, {}),
                "rank": i + 1
            }
            
            results.append(result)
        
        logger.info(f"Found {len(results)} results")
        
        return results
    
    @staticmethod
    def _matches_filter(metadata: Dict[str, Any], filter_dict: Dict[str, Any]) -> bool:
        """Check if metadata matches filter criteria."""
        for key, value in filter_dict.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True
    
    def save(self, name: str = "default"):
        """
        Save index and metadata to disk.
        
        Args:
            name: Name for this index
        """
        if not self.index:
            logger.warning("No index to save")
            return
        
        index_path = self.store_path / f"{name}.index"
        metadata_path = self.store_path / f"{name}_metadata.pkl"
        documents_path = self.store_path / f"{name}_documents.pkl"
        
        # Save FAISS index
        faiss.write_index(self.index, str(index_path))
        
        # Save metadata
        with open(metadata_path, "wb") as f:
            pickle.dump({
                "metadata": self.metadata,
                "next_id": self.next_id
            }, f)
        
        # Save documents
        with open(documents_path, "wb") as f:
            pickle.dump(self.documents, f)
        
        logger.info(f"Saved vector store to {self.store_path}")
    
    def load(self, name: str = "default"):
        """
        Load index and metadata from disk.
        
        Args:
            name: Name of index to load
        """
        index_path = self.store_path / f"{name}.index"
        metadata_path = self.store_path / f"{name}_metadata.pkl"
        documents_path = self.store_path / f"{name}_documents.pkl"
        
        if not index_path.exists():
            raise VectorStoreError(
                f"Index not found: {index_path}",
                error_code="INDEX_NOT_FOUND"
            )
        
        # Load FAISS index
        self.index = faiss.read_index(str(index_path))
        
        # Load metadata
        with open(metadata_path, "rb") as f:
            data = pickle.load(f)
            self.metadata = data["metadata"]
            self.next_id = data["next_id"]
        
        # Load documents
        with open(documents_path, "rb") as f:
            self.documents = pickle.load(f)
        
        logger.info(f"Loaded vector store from {self.store_path}")
        logger.info(f"  - Documents: {len(self.documents)}")
        logger.info(f"  - Index size: {self.index.ntotal}")
    
    @property
    def size(self) -> int:
        """Get number of documents in store."""
        return len(self.documents)
    
    def clear(self):
        """Clear all data from vector store."""
        self.index = None
        self.metadata.clear()
        self.documents.clear()
        self.next_id = 0
        
        logger.info("Cleared vector store")


class DocumentChunker:
    """
    Chunk documents for vector store ingestion.
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separator: str = "\n\n"
    ):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks
            separator: Text separator for splitting
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator
    
    def chunk_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Chunk text into smaller pieces.
        
        Args:
            text: Text to chunk
            metadata: Metadata to attach to each chunk
            
        Returns:
            List of (chunk_text, chunk_metadata) tuples
        """
        # Split by separator first
        sections = text.split(self.separator)
        
        chunks = []
        current_chunk = ""
        
        for section in sections:
            # If adding this section exceeds chunk size
            if len(current_chunk) + len(section) > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_metadata = metadata.copy() if metadata else {}
                chunk_metadata["chunk_index"] = len(chunks)
                chunks.append((current_chunk.strip(), chunk_metadata))
                
                # Start new chunk with overlap
                overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                current_chunk = overlap_text + self.separator + section
            else:
                # Add to current chunk
                if current_chunk:
                    current_chunk += self.separator + section
                else:
                    current_chunk = section
        
        # Add final chunk
        if current_chunk:
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata["chunk_index"] = len(chunks)
            chunks.append((current_chunk.strip(), chunk_metadata))
        
        return chunks