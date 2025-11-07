"""
Lab 6: Payload Assembly
Combines structured data (Company, Events, Products, Leadership, Snapshots) into final payloads.
"""
import json
import sys
from datetime import date
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from .models import Payload, Company, Event, Product, Leadership, Snapshot, Visibility


class PayloadAssembler:
    """Assembles structured data into final dashboard-ready payloads."""
    
    def __init__(self, structured_dir: Path, output_dir: Path):
        self.structured_dir = structured_dir
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def load_structured_data(self, company_id: str) -> Optional[dict]:
        """Load structured data for a company."""
        file_path = self.structured_dir / f"{company_id}.json"
        
        if not file_path.exists():
            print(f"  ⚠️  Structured data not found: {company_id}")
            return None
        
        with open(file_path) as f:
            return json.load(f)
    
    def assemble_payload(self, company_id: str) -> Optional[Payload]:
        """Assemble a complete payload for a company."""
        # Load structured data
        data = self.load_structured_data(company_id)
        if not data:
            return None
        
        # Parse into Pydantic models
        try:
            company = Company(**data['company'])
            events = [Event(**e) for e in data.get('events', [])]
            products = [Product(**p) for p in data.get('products', [])]
            leadership = [Leadership(**l) for l in data.get('leadership', [])]
            snapshots = [Snapshot(**s) for s in data.get('snapshots', [])]
            visibility = [Visibility(**v) for v in data.get('visibility', [])]
            
            # Create payload with provenance policy
            payload = Payload(
                company_record=company,
                events=events,
                products=products,
                leadership=leadership,
                snapshots=snapshots,
                visibility=visibility,
                notes="",
                provenance_policy=(
                    "Use only the sources you scraped (Forbes AI 50 list and company websites). "
                    "If a field is missing, write 'Not disclosed.' "
                    "Do not infer valuation, revenue, or other financial metrics not explicitly stated."
                )
            )
            
            return payload
            
        except Exception as e:
            print(f"  ❌ Failed to parse data for {company_id}: {e}")
            return None
    
    def save_payload(self, payload: Payload, company_id: str):
        """Save payload to JSON file."""
        output_path = self.output_dir / f"{company_id}.json"
        
        # Convert to dict and save
        with open(output_path, 'w') as f:
            json.dump(payload.model_dump(mode='json'), f, indent=2, default=str)
        
        print(f"  💾 Saved: {output_path.name}")
    
    def assemble_all(self):
        """Assemble payloads for all companies with structured data."""
        # Find all structured data files
        structured_files = list(self.structured_dir.glob("*.json"))
        
        print(f"\n{'='*80}")
        print(f"PAYLOAD ASSEMBLY - Lab 6")
        print(f"{'='*80}")
        print(f"Structured files found: {len(structured_files)}")
        print(f"Output directory: {self.output_dir}")
        print(f"{'='*80}\n")
        
        success_count = 0
        failed = []
        
        for i, file_path in enumerate(structured_files, 1):
            company_id = file_path.stem
            
            print(f"[{i}/{len(structured_files)}] {company_id}")
            
            try:
                payload = self.assemble_payload(company_id)
                if payload:
                    self.save_payload(payload, company_id)
                    success_count += 1
                else:
                    failed.append(company_id)
            except Exception as e:
                print(f"  ❌ Error: {e}")
                failed.append(company_id)
        
        # Summary
        print(f"\n{'='*80}")
        print(f"ASSEMBLY COMPLETE")
        print(f"{'='*80}")
        print(f"✅ Successful: {success_count}/{len(structured_files)}")
        print(f"❌ Failed: {len(failed)}")
        
        if failed:
            print(f"\nFailed companies:")
            for company_id in failed:
                print(f"  - {company_id}")
        
        print(f"\n📁 Payloads saved to: {self.output_dir}")
        print(f"{'='*80}\n")
        
        return success_count, len(failed)


def main():
    """Assemble payloads for all companies."""
    project_root = Path(__file__).parent.parent
    structured_dir = project_root / "data" / "structured"
    output_dir = project_root / "data" / "payloads"
    
    if not structured_dir.exists():
        print(f"❌ Structured data directory not found: {structured_dir}")
        print("   Run Lab 5 (structured extraction) first.")
        return
    
    assembler = PayloadAssembler(structured_dir, output_dir)
    assembler.assemble_all()


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    main()

