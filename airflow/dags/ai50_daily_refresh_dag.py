"""
AI50 Daily Refresh DAG - Fixed Version
Refreshes key pages (About, Careers, Blog) daily at 3 AM UTC
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
    print(f"✓ Loaded {len(companies)} companies for daily refresh")
    
    context['ti'].xcom_push(key='companies', value=companies)
    return len(companies)


def refresh_all_companies(**context):
    """Refresh key pages for all companies"""
    from scraper import CompanyScraper
    
    companies = context['ti'].xcom_pull(key='companies', task_ids='load_company_list')
    today = datetime.now().strftime("%Y-%m-%d")
    
    print(f"\n{'='*60}")
    print(f"DAILY REFRESH - {today}")
    print(f"{'='*60}\n")
    
    results = []
    
    for company in companies:
        company_name = company['name']
        base_url = company['url'].rstrip('/')
        
        # Create daily subfolder
        company_folder = company_name.lower().replace(' ', '_').replace('.', '').replace('&', 'and')
        daily_dir = DATA_DIR / "raw" / company_folder / f"daily_{today}"
        
        print(f"→ Refreshing {company_name}...")
        
        try:
            # Initialize scraper with daily directory
            scraper = CompanyScraper(base_data_dir=str(daily_dir.parent))
            
            # Note: This assumes your scraper has a method to scrape specific pages
            # If not, it will scrape all pages, which is fine for daily refresh
            metadata = scraper.scrape_company(
                company_name=company_name,
                base_url=base_url,
                run_id=f"daily_{today}"
            )
            
            results.append({
                'company': company_name,
                'status': 'success',
                'date': today
            })
            print(f"  ✓ Success")
            
        except Exception as e:
            results.append({
                'company': company_name,
                'status': 'failed',
                'error': str(e),
                'date': today
            })
            print(f"  ✗ Failed: {str(e)}")
    
    # Summary
    success_count = len([r for r in results if r['status'] == 'success'])
    failed_count = len([r for r in results if r['status'] == 'failed'])
    
    print(f"\n{'='*60}")
    print("REFRESH COMPLETE")
    print(f"{'='*60}")
    print(f"✓ Successful: {success_count}/{len(companies)}")
    print(f"✗ Failed: {failed_count}/{len(companies)}")
    
    # Push results
    context['ti'].xcom_push(key='refresh_results', value=results)
    return results


def update_vector_db(**context):
    """Update vector database with refreshed data"""
    from rag_pipeline import RAGPipeline
    
    print(f"\n{'='*60}")
    print("UPDATING VECTOR DB")
    print(f"{'='*60}\n")
    
    results = context['ti'].xcom_pull(key='refresh_results', task_ids='refresh_all_companies')
    today = datetime.now().strftime("%Y-%m-%d")
    
    rag = RAGPipeline()
    updated_count = 0
    
    for result in results:
        if result['status'] == 'success':
            company_name = result['company']
            
            # Find daily data folder
            company_folder = company_name.lower().replace(' ', '_').replace('.', '').replace('&', 'and')
            daily_folder = DATA_DIR / "raw" / company_folder / f"daily_{today}"
            
            if daily_folder.exists():
                try:
                    print(f"→ Updating {company_name}...")
                    stats = rag.index_company(company_name, daily_folder)
                    updated_count += 1
                    print(f"  ✓ Updated")
                    
                except Exception as e:
                    print(f"  ✗ Error: {str(e)}")
    
    # Get final stats
    db_stats = rag.get_stats()
    
    print(f"\n{'='*60}")
    print("UPDATE COMPLETE")
    print(f"{'='*60}")
    print(f"Companies updated: {updated_count}")
    print(f"Total documents in vector DB: {db_stats.get('total_documents', 0)}")
    
    return updated_count


def log_completion(**context):
    """Log completion and save daily report"""
    refresh_results = context['ti'].xcom_pull(key='refresh_results', task_ids='refresh_all_companies')
    updated_count = context['ti'].xcom_pull(task_ids='update_vector_db')
    today = datetime.now().strftime("%Y-%m-%d")
    
    report = {
        "pipeline": "Daily Refresh",
        "date": today,
        "completed_at": datetime.now().isoformat(),
        "companies_refreshed": len([r for r in refresh_results if r['status'] == 'success']),
        "companies_failed": len([r for r in refresh_results if r['status'] == 'failed']),
        "vector_db_updated": updated_count,
        "status": "completed",
        "failed_companies": [r['company'] for r in refresh_results if r['status'] == 'failed']
    }
    
    # Save daily report
    reports_dir = DATA_DIR / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    report_path = reports_dir / f"daily_refresh_{today}.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n{'='*60}")
    print("DAILY REFRESH REPORT")
    print(f"{'='*60}")
    print(json.dumps(report, indent=2))
    
    # Alert if failures
    if report['companies_failed'] > 0:
        print(f"\n⚠️  WARNING: {report['companies_failed']} companies failed")
        print(f"Failed: {', '.join(report['failed_companies'])}")
    
    print(f"\nReport saved: {report_path}")
    
    return report


# ============================================================
# DAG Definition
# ============================================================

with DAG(
    dag_id="ai50_daily_refresh_dag",
    start_date=datetime(2025, 10, 31),
    schedule="0 3 * * *",  # Daily at 3 AM UTC
    catchup=False,
    tags=["ai50", "orbit", "daily"],
    description="Daily refresh of Forbes AI 50 companies (About, Careers, Blog)"
) as dag:

    # Task 1: Load company list
    t1_load = PythonOperator(
        task_id="load_company_list",
        python_callable=load_company_list,
    )

    # Task 2: Refresh all companies
    t2_refresh = PythonOperator(
        task_id="refresh_all_companies",
        python_callable=refresh_all_companies,
    )

    # Task 3: Update vector DB
    t3_update = PythonOperator(
        task_id="update_vector_db",
        python_callable=update_vector_db,
    )

    # Task 4: Log completion
    t4_log = PythonOperator(
        task_id="log_completion",
        python_callable=log_completion,
    )

    # Task dependencies
    t1_load >> t2_refresh >> t3_update >> t4_log