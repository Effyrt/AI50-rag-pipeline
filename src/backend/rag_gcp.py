"""
Cloud Run script for RAG pipeline indexing
Downloads raw data from GCS, builds vector database, uploads back to GCS
"""
import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from google.cloud import storage
from rag_pipeline import RAGPipeline
import json
from datetime import datetime


def download_from_gcs(bucket_name: str, local_dir: Path):
    """Download raw data from GCS bucket"""
    print(f"📥 Downloading data from GCS bucket: {bucket_name}")

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    downloaded_files = 0
    downloaded_dirs = set()

    # Download all files from company folders (exclude root-level files like forbes_ai50_seed.json)
    blobs = bucket.list_blobs()
    for blob in blobs:
        # Skip root-level files and directories
        if '/' not in blob.name or blob.name.endswith('/') or blob.name == 'forbes_ai50_seed.json':
            continue

        # Create local directory structure
        local_path = local_dir / blob.name
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Download file
        blob.download_to_filename(local_path)
        downloaded_files += 1
        downloaded_dirs.add(local_path.parent)

        if downloaded_files % 10 == 0:
            print(f"   Downloaded {downloaded_files} files...")

    print(f"✅ Downloaded {downloaded_files} files from {len(downloaded_dirs)} company directories")
    return downloaded_files


def upload_to_gcs(local_path: Path, bucket_name: str, gcs_prefix: str):
    """Upload vector database to GCS"""
    print(f"📤 Uploading vector database to GCS: {bucket_name}/{gcs_prefix}")

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    uploaded_files = 0

    # Upload all files in the vector database directory
    for file_path in local_path.rglob('*'):
        if file_path.is_file():
            gcs_path = f"{gcs_prefix}/{file_path.relative_to(local_path)}"
            blob = bucket.blob(gcs_path)
            blob.upload_from_filename(file_path)
            uploaded_files += 1

    print(f"✅ Uploaded {uploaded_files} vector database files")
    return uploaded_files


def main():
    """Main function for Cloud Run RAG indexing"""
    print("\n" + "="*60)
    print("CLOUD RUN RAG PIPELINE")
    print("="*60)

    # Get environment variables
    gcs_bucket = os.getenv("GCS_BUCKET", "gen-lang-client-0653324487-raw-data")

    print(f"GCS Bucket: {gcs_bucket}")

    # Create temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        data_dir = temp_path / "data"
        data_dir.mkdir()

        # Note: We override the data directory by setting the raw_data_dir variable in the indexing code above

        try:
            # Step 1: Download raw data from GCS
            print("\n1. Downloading raw data from GCS...")
            downloaded_files = download_from_gcs(gcs_bucket, data_dir)

            if downloaded_files == 0:
                print("❌ No raw data found in GCS bucket")
                return 1

            # Step 2: Run indexing
            print("\n2. Running RAG indexing...")

            # Initialize RAG pipeline
            rag = RAGPipeline()
            print(f"   Current DB stats: {rag.get_stats()}")

            # Find all company folders (they are directly in data_dir, not in a raw subdirectory)
            company_folders = [f for f in data_dir.iterdir() if f.is_dir() and f.name != 'vector_db']

            print(f"\n   Found {len(company_folders)} company folders")

            # Index each company
            print("   Indexing companies...")

            results = []
            successful = 0
            failed = 0

            for i, company_folder in enumerate(company_folders, 1):
                company_name = company_folder.name.replace('_', ' ').title()

                print(f"   [{i}/{len(company_folders)}] {company_name}")

                # Check if company has any text files
                txt_files = list(company_folder.glob("*.txt"))

                if not txt_files:
                    print("     ⚠ No text files found, skipping")
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
                        print(f"     ✓ Indexed: {stats['chunks_created']} chunks from {stats['files_processed']} files")
                        results.append({
                            'company': company_name,
                            'status': 'success',
                            'chunks': stats['chunks_created'],
                            'files': stats['files_processed']
                        })
                        successful += 1
                    else:
                        print("     ⚠ No chunks created")
                        results.append({
                            'company': company_name,
                            'status': 'failed',
                            'reason': 'no_chunks'
                        })
                        failed += 1

                except Exception as e:
                    print(f"     ✗ Error: {str(e)}")
                    results.append({
                        'company': company_name,
                        'status': 'error',
                        'error': str(e)
                    })
                    failed += 1

            # Save results
            print("\n   Saving indexing results...")
            results_file = temp_path / "data" / "indexing_results.json"
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

            print("\n   " + "="*50)
            print("   INDEXING SUMMARY")
            print("   " + "="*50)
            print(f"   Total companies processed: {len(company_folders)}")
            print(f"   ✓ Successfully indexed: {successful}")
            print(f"   ✗ Failed/Skipped: {failed}")
            print(f"   Final Vector DB Stats: {final_stats['total_documents']} documents")

            # Step 3: Upload vector database back to GCS
            vector_db_path = temp_path / "data" / "vector_db"
            if vector_db_path.exists():
                print("\n3. Uploading vector database to GCS...")
                upload_to_gcs(vector_db_path, gcs_bucket, "vector_index")
            else:
                print("❌ Vector database not found after indexing")
                return 1

            print("\n" + "="*60)
            print("✅ CLOUD RUN RAG PIPELINE COMPLETE")
            print("="*60)

            return 0

        except Exception as e:
            print(f"❌ Error in RAG pipeline: {e}")
            import traceback
            traceback.print_exc()
            return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
