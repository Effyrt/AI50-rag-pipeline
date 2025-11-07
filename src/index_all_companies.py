"""
Batch indexer for all scraped companies
Builds vector database for RAG pipeline
"""
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from rag_pipeline import RAGPipeline


def index_all_companies():
    """Index all scraped companies into vector database"""
    
    print("\n" + "="*60)
    print("BATCH VECTOR DB INDEXING")
    print("="*60)
    
    # Initialize RAG pipeline
    print("\n1. Initializing RAG pipeline...")
    rag = RAGPipeline()
    print(f"   Current DB stats: {rag.get_stats()}")
    
    # Find all company folders 
    project_root = Path(__file__).parent.parent
    raw_data_dir = project_root / "data" / "raw"
    company_folders = [f for f in raw_data_dir.iterdir() if f.is_dir()]
    
    print(f"\n2. Found {len(company_folders)} company folders")
    
    # Index each company
    print(f"\n3. Indexing companies...")
    
    results = []
    successful = 0
    failed = 0
    
    for i, company_folder in enumerate(company_folders, 1):
        company_name = company_folder.name.replace('_', ' ').title()
        
        print(f"\n[{i}/{len(company_folders)}] {company_name}")
        
        # Check if company has any text files
        txt_files = list(company_folder.glob("*.txt"))
        
        if not txt_files:
            print(f"   ⚠ No text files found, skipping")
            results.append({
                'company': company_name,
                'status': 'skipped',
                'reason': 'no_text_files'
            })
            failed += 1
            continue
        
        try:
            # Index the company
            stats = rag.index_company(company_name, company_folder)
            
            if stats['chunks_created'] > 0:
                print(f"   ✓ Indexed: {stats['chunks_created']} chunks from {stats['files_processed']} files")
                results.append({
                    'company': company_name,
                    'status': 'success',
                    'chunks': stats['chunks_created'],
                    'files': stats['files_processed']
                })
                successful += 1
            else:
                print(f"   ⚠ No chunks created")
                results.append({
                    'company': company_name,
                    'status': 'failed',
                    'reason': 'no_chunks'
                })
                failed += 1
                
        except Exception as e:
            print(f"   ✗ Error: {str(e)}")
            results.append({
                'company': company_name,
                'status': 'error',
                'error': str(e)
            })
            failed += 1
    
    # Save results
    print("\n4. Saving indexing results...")
    results_file = project_root / "data" / "indexing_results.json"
    with open(results_file, 'w') as f:
        json.dump({
            'indexed_at': datetime.now().isoformat(),
            'total_companies': len(company_folders),
            'successful': successful,
            'failed': failed,
            'results': results
        }, f, indent=2)
    
    # Final stats
    final_stats = rag.get_stats()
    
    print("\n" + "="*60)
    print("INDEXING SUMMARY")
    print("="*60)
    print(f"\nTotal companies processed: {len(company_folders)}")
    print(f"  ✓ Successfully indexed: {successful}")
    print(f"  ✗ Failed/Skipped: {failed}")
    print(f"\nFinal Vector DB Stats:")
    print(f"  Total documents: {final_stats['total_documents']}")
    print(f"  DB location: {final_stats['vector_db_path']}")
    print(f"\nResults saved to: {results_file}")
    
    print("\n" + "="*60)
    print("✓ INDEXING COMPLETE!")
    print("="*60)
    print("\nNext steps:")
    print("1. Test RAG search functionality")
    print("2. Generate company dashboards")


if __name__ == "__main__":
    index_all_companies()