"""
RAG Pipeline for PE Dashboard - Unstructured Text Processing
Handles vector database, embeddings, and dashboard generation
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# LangChain imports - updated for new version compatibility
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI

# Environment variables
from dotenv import load_dotenv
load_dotenv()


class RAGPipeline:
    """
    Complete RAG Pipeline for unstructured company data
    - Chunks text into manageable pieces
    - Embeds text using sentence-transformers
    - Stores in ChromaDB vector database
    - Retrieves relevant context
    - Generates dashboards using OpenAI
    """
    
    def __init__(
        self,
        vector_db_path: str = "data/vector_db",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        chunk_size: int = 800,
        chunk_overlap: int = 200
    ):
        """
        Initialize RAG pipeline
        
        Args:
            vector_db_path: Path to store Chroma vector database
            embedding_model: HuggingFace embedding model name
            chunk_size: Size of text chunks (characters)
            chunk_overlap: Overlap between chunks
        """
        self.vector_db_path = Path(vector_db_path)
        self.vector_db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Initialize embeddings (this will download model on first run)
        print(f"Loading embedding model: {embedding_model}")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # Initialize vector store
        self.vectorstore = None
        self._load_or_create_vectorstore()
        
        # Initialize LLM
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("WARNING: OPENAI_API_KEY not found in environment")
        
        self.llm = ChatOpenAI(
            model_name="gpt-4",
            temperature=0.1,
            openai_api_key=api_key
        )
    
    def _load_or_create_vectorstore(self):
        """Load existing vectorstore or create new one"""
        try:
            self.vectorstore = Chroma(
                persist_directory=str(self.vector_db_path),
                embedding_function=self.embeddings
            )
            count = self.vectorstore._collection.count()
            print(f"Loaded existing vector store with {count} documents")
        except Exception as e:
            print(f"Creating new vector store: {e}")
            self.vectorstore = Chroma(
                persist_directory=str(self.vector_db_path),
                embedding_function=self.embeddings
            )
    
    def index_company(self, company_name: str, data_folder: Path) -> Dict:
        """
        Index all text files for a company into vector database
            
        Returns:
            Indexing statistics
        """
        print(f"\n=== Indexing {company_name} ===")
        
        documents = []
        stats = {
            'company_name': company_name,
            'files_processed': 0,
            'chunks_created': 0,
            'timestamp': datetime.now().isoformat()
        }
        
        # Read all .txt files in the folder
        txt_files = list(data_folder.glob("*.txt"))
        
        if not txt_files:
            print(f"WARNING: No .txt files found in {data_folder}")
            return stats
        
        for txt_file in txt_files:
            try:
                print(f"Processing: {txt_file.name}")
                
                # Read file content
                content = txt_file.read_text(encoding='utf-8')
                
                # Skip if empty or too short
                if len(content.strip()) < 100:
                    print(f"  Skipping {txt_file.name} - too short")
                    continue
                
                # Create chunks
                chunks = self.text_splitter.split_text(content)
                print(f"  Created {len(chunks)} chunks")
                
                # Create Document objects with metadata
                for i, chunk in enumerate(chunks):
                    doc = Document(
                        page_content=chunk,
                        metadata={
                            'company': company_name,
                            'source': txt_file.name,
                            'chunk_id': i,
                            'file_path': str(txt_file)
                        }
                    )
                    documents.append(doc)
                
                stats['files_processed'] += 1
                stats['chunks_created'] += len(chunks)
                
            except Exception as e:
                print(f"Error processing {txt_file}: {str(e)}")
        
        # Add to vector store
        if documents:
            print(f"\nAdding {len(documents)} documents to vector store...")
            self.vectorstore.add_documents(documents)
            self.vectorstore.persist()
            print("✓ Vector store updated and persisted")
        else:
            print("No documents to add")
        
        return stats
    
    def search(self, query: str, company_name: Optional[str] = None, k: int = 5) -> List[Dict]:
        """
        Search for relevant documents
        
        Args:
            query: Search query
            company_name: Optional company filter
            k: Number of results to return
            
        Returns:
            List of relevant documents with metadata
        """
        # Build filter
        filter_dict = {}
        if company_name:
            filter_dict['company'] = company_name
        
        # Search
        try:
            if filter_dict:
                results = self.vectorstore.similarity_search(
                    query,
                    k=k,
                    filter=filter_dict
                )
            else:
                results = self.vectorstore.similarity_search(query, k=k)
        except Exception as e:
            print(f"Search error: {e}")
            return []
        
        # Format results
        formatted_results = []
        for doc in results:
            formatted_results.append({
                'content': doc.page_content,
                'metadata': doc.metadata,
                'source': doc.metadata.get('source', 'unknown'),
                'company': doc.metadata.get('company', 'unknown')
            })
        
        return formatted_results
    
    def generate_dashboard(self, company_name: str, top_k: int = 15) -> str:
        """
        Generate PE dashboard using RAG
        
        Args:
            company_name: Company name
            top_k: Number of context chunks to retrieve
            
        Returns:
            Markdown dashboard
        """
        print(f"\n=== Generating RAG Dashboard for {company_name} ===")
        
        # Load dashboard prompt
        prompt_path = Path("src/prompts/dashboard_system.md")
        if not prompt_path.exists():
            # Use default prompt if file doesn't exist
            dashboard_template = self._get_default_prompt()
        else:
            dashboard_template = prompt_path.read_text()
        
        # Retrieve relevant context using multiple queries
        queries = [
            f"{company_name} company overview business model mission",
            f"{company_name} funding investors valuation capital",
            f"{company_name} growth hiring team employees",
            f"{company_name} product technology AI platform",
            f"{company_name} customers market visibility news"
        ]
        
        all_context = []
        for query in queries:
            results = self.search(query, company_name=company_name, k=3)
            all_context.extend(results)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_context = []
        for item in all_context:
            content = item['content']
            if content not in seen:
                seen.add(content)
                unique_context.append(item)
        
        # Format context for prompt
        context_text = "\n\n---\n\n".join([
            f"Source: {item['metadata']['source']}\n{item['content']}"
            for item in unique_context[:top_k]
        ])
        
        if not context_text.strip():
            context_text = "No context available. Use 'Not disclosed.' for all fields."
        
        # Build final prompt
        prompt = f"""You are a private equity analyst creating an investment dashboard.

COMPANY: {company_name}

RETRIEVED CONTEXT:
{context_text}

{dashboard_template}

Generate a complete dashboard following the exact 8-section structure.
Use ONLY information from the provided context.
When information is missing, write "Not disclosed."
"""
        
        # Generate dashboard
        try:
            print("Calling LLM...")
            response = self.llm.invoke(prompt).content
            return response
        except Exception as e:
            print(f"Error generating dashboard: {e}")
            return f"# Error\n\nFailed to generate dashboard: {str(e)}"
    
    def _get_default_prompt(self) -> str:
        """Default dashboard prompt if file not found"""
        return """
Generate an investor-style dashboard with these 8 sections:

## Company Overview
- Founding year, headquarters, mission
- Core AI/ML focus
- Target market

## Business Model and GTM  
- Revenue model
- Go-to-market strategy
- Key partnerships

## Funding & Investor Profile
- Total funding raised
- Latest round details
- Key investors

## Growth Momentum
- Recent customer wins
- Hiring trends
- Product launches

## Visibility & Market Sentiment
- Media coverage
- Industry recognition
- Market presence

## Risks and Challenges
- Competitive threats
- Market risks
- Execution challenges

## Outlook
- Growth trajectory
- Market opportunity
- Investment thesis

## Disclosure Gaps
- List ALL information that was not found
- Use bullet points
"""
    
    def get_stats(self) -> Dict:
        """Get vector database statistics"""
        try:
            count = self.vectorstore._collection.count()
            return {
                'total_documents': count,
                'vector_db_path': str(self.vector_db_path)
            }
        except Exception as e:
            return {
                'total_documents': 0,
                'vector_db_path': str(self.vector_db_path),
                'error': str(e)
            }


# Legacy function for backward compatibility
def retrieve_context(company_name: str) -> List[Dict]:
    """
    Legacy function - retrieves context from text files
    Kept for backward compatibility with existing code
    """
    folder_path = f"data/raw/{company_name.lower()}"
    file_path = os.path.join(folder_path, "about.txt")

    if not os.path.exists(file_path):
        return [{
            "source_url": f"https://example.com/{company_name}",
            "text": f"No data available for {company_name}"
        }]

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    return [{
        "source_url": f"https://{company_name.lower()}.com/about",
        "text": text
    }]


def generate_rag_dashboard(company_name: str) -> Dict:
    """
    Legacy function - generates dashboard using RAG pipeline
    Kept for backward compatibility with api.py
    """
    try:
        rag = RAGPipeline()
        markdown = rag.generate_dashboard(company_name)
        context = retrieve_context(company_name)
        
        return {
            "markdown": markdown,
            "retrieved": context
        }
    except Exception as e:
        print(f"Error in generate_rag_dashboard: {e}")
        return {
            "markdown": f"# Error\n\nFailed to generate dashboard: {str(e)}",
            "retrieved": []
        }

