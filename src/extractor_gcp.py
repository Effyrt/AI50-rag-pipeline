"""
GCP-compatible extractor using instructor + pydantic.
Reads from raw GCS bucket, extracts structured data, writes to structured GCS bucket.
"""
import os
import json
import shutil
from pathlib import Path
from google.cloud import storage
from src.extractor_v4_bi import EnhancedExtractor

def main():
    """Main entry point for GCP Cloud Run extraction job."""

    project_id = os.getenv("GCP_PROJECT_ID", "gen-lang-client-0653324487")
    raw_bucket_name = f"{project_id}-raw-data"
    structured_bucket_name = f"{project_id}-structured-data"
    company_id = os.getenv("COMPANY_ID")
    company_ids_env = os.getenv("COMPANY_IDS")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not openai_api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        return

    os.environ["OPENAI_API_KEY"] = openai_api_key

    storage_client = storage.Client(project=project_id)
    raw_bucket = storage_client.bucket(raw_bucket_name)
    structured_bucket = storage_client.bucket(structured_bucket_name)

    seed_blob = raw_bucket.blob("forbes_ai50_seed.json")
    forbes_seed = json.loads(seed_blob.download_as_text())

    if company_id:
        target_company_ids = [company_id]
    elif company_ids_env:
        target_company_ids = [cid.strip() for cid in company_ids_env.split(",") if cid.strip()]
    else:
        target_company_ids = [company["company_id"] for company in forbes_seed]

    if not target_company_ids:
        print("❌ No company IDs provided for extraction")
        return

    total = len(target_company_ids)
    print(f"🚀 Starting extraction for {total} compan{'y' if total == 1 else 'ies'}")

    extractor = EnhancedExtractor()
    temp_output_dir = Path("/tmp/structured")
    temp_output_dir.mkdir(parents=True, exist_ok=True)

    for index, target_id in enumerate(target_company_ids, start=1):
        print("")
        print(f"📊 [{index}/{total}] Extracting: {target_id}")

        temp_raw_dir = Path(f"/tmp/raw/{target_id}")
        if temp_raw_dir.exists():
            shutil.rmtree(temp_raw_dir)
        temp_raw_dir.mkdir(parents=True, exist_ok=True)

        blobs = list(raw_bucket.list_blobs(prefix=f"{target_id}/"))

        if not blobs:
            print(f"❌ No scraped data found for {target_id}")
            continue

        print(f"   📥 Downloading {len(blobs)} files from GCS...")
        for blob in blobs:
            relative_name = blob.name.replace(f"{target_id}/", "")
            local_path = temp_raw_dir / relative_name
            local_path.parent.mkdir(parents=True, exist_ok=True)
            blob.download_to_filename(str(local_path))

        try:
            output_path = extractor.extract_company(
                company_dir=temp_raw_dir,
                output_dir=temp_output_dir,
                forbes_seed=forbes_seed
            )

            structured_blob = structured_bucket.blob(f"{target_id}.json")
            structured_blob.upload_from_filename(str(output_path))
            print(f"   📤 Uploaded: {target_id}.json")
            print(f"✅ Finished {target_id}")

        except Exception as exc:
            print(f"❌ Error extracting {target_id}: {exc}")
            raise

    print("")
    print("🎉 Extraction run complete!")

if __name__ == "__main__":
    main()

