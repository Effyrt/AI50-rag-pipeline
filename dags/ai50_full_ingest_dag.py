"""
AI50 Full Ingestion DAG - Fixed Version
Scrapes all 50 Forbes AI companies and indexes them into vector DB
"""
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from pathlib import Path
import json
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Dynamic path for local and Docker
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"


# ============================================================
# Task Functions
# ============================================================

def load_company_list(**context):
    """Load company list from forbes_ai50_seed.json"""
    seed_path = DATA_DIR / "forbes_ai50_seed.json"
    
    if not seed_path.exists():
        raise FileNotFoundError(f"Seed file not found: {seed_path}")
    
    with open(seed_path, 'r') as f:
        data = json.load(f)
    
    companies = data.get('companies', [])
    print(f"✓ Loaded {len(companies)} companies")
    
    # Push to XCom for next task
    context['ti'].xcom_push(key='companies', value=companies)
    return len(companies)


def scrape_all_companies(**context):
    """Scrape all companies using scraper.py"""
    from scraper import CompanyScraper
    
    # Get companies from previous task
    companies = context['ti'].xcom_pull(key='companies', task_ids='load_company_list')
    
    scraper = CompanyScraper(base_data_dir=str(DATA_DIR / "raw"))
    results = []
    
    print(f"\n{'='*60}")
    print(f"Starting full ingestion for {len(companies)} companies")
    print(f"{'='*60}\n")
    
    for company in companies:
        company_name = company['name']
        base_url = company['url'].rstrip('/')
        
        print(f"\n→ Scraping {company_name}...")
        
        try:
            metadata = scraper.scrape_company(
                company_name=company_name,
                base_url=base_url
            )
            results.append({
                'company': company_name,
                'status': 'success',
                'metadata': metadata
            })
            print(f"  ✓ Success: {company_name}")
            
        except Exception as e:
            results.append({
                'company': company_name,
                'status': 'failed',
                'error': str(e)
            })
            print(f"  ✗ Failed: {company_name} - {str(e)}")
    
    # Summary
    success_count = len([r for r in results if r['status'] == 'success'])
    failed_count = len([r for r in results if r['status'] == 'failed'])
    
    print(f"\n{'='*60}")
    print(f"SCRAPING COMPLETE")
    print(f"{'='*60}")
    print(f"✓ Successful: {success_count}/{len(companies)}")
    print(f"✗ Failed: {failed_count}/{len(companies)}")
    
    # Save log
    log_path = DATA_DIR / "raw" / "ingest_log.json"
    with open(log_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nLog saved: {log_path}")
    
    # Push results to XCom
    context['ti'].xcom_push(key='scrape_results', value=results)
    return results


def index_to_vector_db(**context):
    """Index scraped data into vector database"""
    from rag_pipeline import RAGPipeline
    
    print(f"\n{'='*60}")
    print("INDEXING TO VECTOR DB")
    print(f"{'='*60}\n")
    
    # Get scrape results
    results = context['ti'].xcom_pull(key='scrape_results', task_ids='scrape_all_companies')
    
    # Initialize RAG pipeline
    rag = RAGPipeline()
    indexed_count = 0
    
    for result in results:
        if result['status'] == 'success':
            company_name = result['company']
            
            # Find company data folder
            company_folder = company_name.lower().replace(' ', '_').replace('.', '').replace('&', 'and')
            data_folder = DATA_DIR / "raw" / company_folder
            
            if data_folder.exists():
                try:
                    print(f"→ Indexing {company_name}...")
                    stats = rag.index_company(company_name, data_folder)
                    indexed_count += 1
                    print(f"  ✓ Indexed {company_name}")
                    
                except Exception as e:
                    print(f"  ✗ Error indexing {company_name}: {str(e)}")
    
    # Get final stats
    db_stats = rag.get_stats()
    
    print(f"\n{'='*60}")
    print("INDEXING COMPLETE")
    print(f"{'='*60}")
    print(f"Companies indexed: {indexed_count}")
    print(f"Total documents in vector DB: {db_stats.get('total_documents', 0)}")
    
    return indexed_count


def generate_report(**context):
    """Generate completion report"""
    scrape_results = context['ti'].xcom_pull(key='scrape_results', task_ids='scrape_all_companies')
    indexed_count = context['ti'].xcom_pull(task_ids='index_to_vector_db')
    
    report = {
        "pipeline": "Full Ingestion",
        "completed_at": datetime.now().isoformat(),
        "total_companies": len(scrape_results),
        "scraped_successfully": len([r for r in scrape_results if r['status'] == 'success']),
        "scrape_failures": len([r for r in scrape_results if r['status'] == 'failed']),
        "indexed_to_vector_db": indexed_count,
        "status": "completed"
    }
    
    # Save report
    report_path = DATA_DIR / "full_ingest_report.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n{'='*60}")
    print("FULL INGESTION REPORT")
    print(f"{'='*60}")
    print(json.dumps(report, indent=2))
    print(f"\nReport saved: {report_path}")
    
    return report


# ============================================================
# DAG Definition
# ============================================================

with DAG(
    dag_id="ai50_full_ingest_dag",
    start_date=datetime(2025, 10, 31),
    schedule="@once",
    catchup=False,
    tags=["ai50", "orbit", "full-load"],
    description="Full ingestion of Forbes AI 50 companies with vector DB indexing"
) as dag:

    # Task 1: Load company list
    t1_load = PythonOperator(
        task_id="load_company_list",
        python_callable=load_company_list,
    )

    # Task 2: Scrape all companies
    t2_scrape = PythonOperator(
        task_id="scrape_all_companies",
        python_callable=scrape_all_companies,
    )

    # Task 3: Index to vector DB
    t3_index = PythonOperator(
        task_id="index_to_vector_db",
        python_callable=index_to_vector_db,
    )

    # Task 4: Generate report
    t4_report = PythonOperator(
        task_id="generate_report",
        python_callable=generate_report,
    )

    # Task dependencies
    t1_load >> t2_scrape >> t3_index >> t4_report