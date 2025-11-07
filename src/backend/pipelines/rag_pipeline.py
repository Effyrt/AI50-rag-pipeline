"""
RAG (Retrieval-Augmented Generation) pipeline for dashboard generation.
"""
import logging
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

from ..vector_store.faiss_store import FAISSVectorStore, DocumentChunker
from ..llm.client import get_llm_client
from ..llm.prompts import DashboardPrompts, create_messages
from ..config.settings import settings
from ..core.exceptions import PipelineError
from ..core.telemetry import track_time

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    RAG pipeline for Lab 7 - RAG Dashboard Generation.
    
    Flow:
    1. Index company documents in vector store
    2. Retrieve relevant chunks for query
    3. Generate dashboard using LLM + retrieved context
    """
    
    def __init__(
        self,
        vector_store: Optional[FAISSVectorStore] = None,
        store_name: str = "companies"
    ):
        """
        Initialize RAG pipeline.
        
        Args:
            vector_store: Vector store instance
            store_name: Name for vector store persistence
        """
        self.vector_store = vector_store or FAISSVectorStore()
        self.store_name = store_name
        self.chunker = DocumentChunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap
        )
        self.llm_client = get_llm_client()
        
        # Try to load existing index
        try:
            self.vector_store.load(store_name)
            logger.info(f"Loaded existing vector store: {store_name}")
        except Exception as e:
            logger.info(f"No existing vector store found, will create new one")
    
    @track_time("index_company_documents")
    def index_company_documents(
        self,
        company_id: str,
        company_name: str,
        raw_dir: Optional[Path] = None
    ):
        """
        Index all documents for a company.
        
        Args:
            company_id: Company identifier
            company_name: Company name
            raw_dir: Directory with raw scraped data
        """
        raw_dir = raw_dir or settings.raw_data_dir
        company_dir = raw_dir / company_id
        
        if not company_dir.exists():
            raise PipelineError(
                f"Company directory not found: {company_dir}",
                error_code="COMPANY_DIR_NOT_FOUND"
            )
        
        logger.info(f"Indexing documents for {company_name}")
        
        # Find latest scrape
        run_dirs = sorted([d for d in company_dir.iterdir() if d.is_dir()], reverse=True)
        
        if not run_dirs:
            raise PipelineError(
                f"No scrape data found for {company_id}",
                error_code="NO_SCRAPE_DATA"
            )
        
        latest_run = run_dirs[0]
        
        # Index each page type
        total_chunks = 0
        
        for page_type in ["homepage", "about", "product", "careers", "blog"]:
            page_dir = latest_run / page_type
            
            if not page_dir.exists():
                continue
            
            # Load clean text
            text_file = page_dir / "clean.txt"
            if not text_file.exists():
                continue
            
            with open(text_file, encoding="utf-8") as f:
                text = f.read()
            
            # Load metadata
            meta_file = page_dir / "metadata.json"
            if meta_file.exists():
                with open(meta_file) as f:
                    page_metadata = json.load(f)
            else:
                page_metadata = {}
            
            # Chunk text
            chunks = self.chunker.chunk_text(text, metadata={
                "company_id": company_id,
                "company_name": company_name,
                "page_type": page_type,
                "source_url": page_metadata.get("url", ""),
                "scraped_at": page_metadata.get("scraped_at", "")
            })
            
            # Add to vector store
            if chunks:
                chunk_texts = [chunk[0] for chunk in chunks]
                chunk_metadatas = [chunk[1] for chunk in chunks]
                
                self.vector_store.add_documents(chunk_texts, chunk_metadatas)
                total_chunks += len(chunks)
                
                logger.info(f"  - Indexed {len(chunks)} chunks from {page_type}")
        
        logger.info(f"Indexed {total_chunks} total chunks for {company_name}")
        
        # Save index
        self.vector_store.save(self.store_name)
    
    @track_time("retrieve_context")
    def retrieve_context(
        self,
        company_name: str,
        query: str,
        k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context for query.
        
        Args:
            company_name: Company name
            query: Search query
            k: Number of chunks to retrieve
            
        Returns:
            List of retrieved chunks with metadata
        """
        logger.info(f"Retrieving context for {company_name}: {query[:100]}")
        
        # Search with company filter
        results = self.vector_store.search(
            query=query,
            k=k,
            filter_metadata={"company_name": company_name}
        )
        
        logger.info(f"Retrieved {len(results)} chunks")
        
        return results
    
    @track_time("generate_dashboard_rag")
    def generate_dashboard(
        self,
        company_name: str,
        top_k: int = 15
    ) -> str:
        """
        Generate investor dashboard using RAG.
        
        Args:
            company_name: Company name
            top_k: Number of chunks to retrieve
            
        Returns:
            Generated dashboard in Markdown
        """
        logger.info(f"Generating RAG dashboard for {company_name}")
        
        # Retrieve relevant context for each dashboard section
        sections = [
            "company overview business model",
            "funding investors valuation",
            "team leadership founders",
            "products features pricing",
            "hiring headcount growth",
            "news media sentiment"
        ]
        
        all_context = []
        for section_query in sections:
            query = f"{company_name} {section_query}"
            results = self.retrieve_context(company_name, query, k=3)
            all_context.extend(results)
        
        # Remove duplicates
        seen_ids = set()
        unique_context = []
        for ctx in all_context:
            if ctx["id"] not in seen_ids:
                unique_context.append(ctx)
                seen_ids.add(ctx["id"])
        
        # Format context for LLM
        context_text = self._format_context(unique_context[:top_k])
        
        # Generate dashboard
        user_prompt = DashboardPrompts.RAG_DASHBOARD.format(
            company_name=company_name,
            context=context_text
        )
        
        messages = create_messages(
            system_prompt=DashboardPrompts.SYSTEM_PROMPT,
            user_prompt=user_prompt
        )
        
        dashboard = self.llm_client.complete(
            messages=messages,
            temperature=0.0,
            max_tokens=4096
        )
        
        logger.info(f"Generated {len(dashboard)} character dashboard")
        
        return dashboard
    
    def _format_context(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Format retrieved chunks for LLM context.
        
        Args:
            chunks: Retrieved chunks
            
        Returns:
            Formatted context string
        """
        formatted = []
        
        for i, chunk in enumerate(chunks, 1):
            formatted.append(f"[Source {i}]")
            formatted.append(f"Page: {chunk['metadata'].get('page_type', 'unknown')}")
            formatted.append(f"URL: {chunk['metadata'].get('source_url', 'unknown')}")
            formatted.append(f"Text: {chunk['text']}")
            formatted.append("")
        
        return "\n".join(formatted)