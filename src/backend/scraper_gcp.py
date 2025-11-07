"""
GCP-compatible scraper that reads from and writes to GCS buckets.
"""
import os
import json
import shutil
from pathlib import Path
from google.cloud import storage
from .playwright_scraper import PlaywrightScraper

def main():
    """Main entry point for GCP Cloud Run scraping job."""

    project_id = os.getenv("GCP_PROJECT_ID", "gen-lang-client-0653324487")
    raw_bucket_name = f"{project_id}-raw-data"
    company_id = os.getenv("COMPANY_ID")
    company_ids_env = os.getenv("COMPANY_IDS")

    # Initialize GCS client
    storage_client = storage.Client(project=project_id)
    raw_bucket = storage_client.bucket(raw_bucket_name)

    # Load Forbes seed data from local copy (if present) or GCS
    seed_file_path = "data/forbes_ai50_seed.json"
    if os.path.exists(seed_file_path):
        with open(seed_file_path) as f:
            forbes_seed = json.load(f)
    else:
        blob = raw_bucket.blob("forbes_ai50_seed.json")
        forbes_seed = json.loads(blob.download_as_text())

    if company_id:
        target_company_ids = [company_id]
    elif company_ids_env:
        target_company_ids = [cid.strip() for cid in company_ids_env.split(",") if cid.strip()]
    else:
        target_company_ids = [company["company_id"] for company in forbes_seed]

    # Distribute companies across parallel tasks (if parallelism is enabled)
    task_index = int(os.getenv("CLOUD_RUN_TASK_INDEX", "0"))
    task_count = int(os.getenv("CLOUD_RUN_TASK_COUNT", "1"))
    
    if task_count > 1 and len(target_company_ids) > 1:
        # Split companies across tasks for parallel processing
        companies_per_task = len(target_company_ids) // task_count
        start_idx = task_index * companies_per_task
        end_idx = start_idx + companies_per_task if task_index < task_count - 1 else len(target_company_ids)
        target_company_ids = target_company_ids[start_idx:end_idx]
        print(f"📊 Task {task_index + 1}/{task_count}: Processing companies {start_idx + 1}-{end_idx} ({len(target_company_ids)} companies)")

    if not target_company_ids:
        print("❌ No company IDs provided for scraping")
        return

    total = len(target_company_ids)
    print(f"🚀 Starting scrape for {total} compan{'y' if total == 1 else 'ies'}")

    for index, target_id in enumerate(target_company_ids, start=1):
        company_info = next((c for c in forbes_seed if c["company_id"] == target_id), None)

        if not company_info:
            print(f"❌ Company {target_id} not found in seed data")
            continue

        company_name = company_info.get("legal_name", company_info.get("company_name", "Unknown"))
        website = company_info.get("website")

        if not website:
            print(f"❌ No website for {company_name} ({target_id})")
            continue

        print("")
        print(f"🌐 [{index}/{total}] Scraping: {company_name}")
        print(f"   Website: {website}")
        print(f"   Company ID: {target_id}")

        temp_dir = Path(f"/tmp/raw/{target_id}")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            with PlaywrightScraper(headless=True) as scraper:
                result = scraper.scrape_company(
                    company_id=target_id,
                    company_name=company_name,
                    website=website,
                    output_dir=Path("/tmp/raw"),
                    forbes_data=forbes_seed
                )

            if result.get("pages_scraped", 0) > 0:
                print(f"   ✅ Scraped {result['pages_scraped']} pages")

                for file_path in temp_dir.rglob("*"):
                    if not file_path.is_file():
                        continue
                    relative_path = file_path.relative_to(Path("/tmp/raw"))
                    blob = raw_bucket.blob(str(relative_path))
                    blob.upload_from_filename(str(file_path))
                    print(f"   📤 Uploaded: {relative_path}")

                print(f"✅ Finished {company_name}")
            else:
                print(f"❌ No pages scraped for {company_name}")

        except Exception as exc:
            print(f"❌ Error scraping {company_name}: {exc}")
            raise

    print("")
    print("🎉 Scraping run complete!")

if __name__ == "__main__":
    main()

