"""
Lab 8: Structured Pipeline
Generate dashboards from structured payloads.
"""
import json
import os
import sys
from pathlib import Path
from typing import Optional

from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class StructuredPipeline:
    """Generate dashboards from structured payloads."""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """Initialize structured pipeline."""
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = model
    
    def load_payload(self, payload_path: Path) -> dict:
        """Load a company payload."""
        with open(payload_path) as f:
            return json.load(f)
    
    def format_payload_for_llm(self, payload: dict) -> str:
        """Format payload as readable text for LLM."""
        company = payload['company_record']
        events = payload.get('events', [])
        products = payload.get('products', [])
        leadership = payload.get('leadership', [])
        snapshots = payload.get('snapshots', [])
        visibility = payload.get('visibility', [])
        
        context = []
        
        # Company basics
        context.append("=== COMPANY INFORMATION ===")
        context.append(f"Legal Name: {company.get('legal_name', 'Not disclosed')}")
        if company.get('brand_name'):
            context.append(f"Brand Name: {company.get('brand_name')}")
        context.append(f"Website: {company.get('website', 'Not disclosed')}")
        
        # Headquarters
        hq_parts = []
        if company.get('hq_city'):
            hq_parts.append(company['hq_city'])
        if company.get('hq_state'):
            hq_parts.append(company['hq_state'])
        if company.get('hq_country'):
            hq_parts.append(company['hq_country'])
        if hq_parts:
            context.append(f"Headquarters: {', '.join(hq_parts)}")
        
        if company.get('founded_year'):
            context.append(f"Founded: {company['founded_year']}")
        
        # Categories
        if company.get('categories'):
            context.append(f"Categories: {', '.join(company['categories'])}")
        
        # Competitors
        if company.get('related_companies'):
            context.append(f"Related Companies: {', '.join(company['related_companies'])}")
        
        context.append("")
        
        # Funding
        context.append("=== FUNDING INFORMATION ===")
        if company.get('total_raised_usd'):
            context.append(f"Total Raised: ${company['total_raised_usd']:,.0f}")
        else:
            context.append("Total Raised: Not disclosed")
        
        if company.get('last_disclosed_valuation_usd'):
            context.append(f"Last Valuation: ${company['last_disclosed_valuation_usd']:,.0f}")
        else:
            context.append("Last Valuation: Not disclosed")
        
        if company.get('last_round_name'):
            context.append(f"Last Round: {company['last_round_name']}")
        
        if company.get('last_round_date'):
            context.append(f"Last Round Date: {company['last_round_date']}")
        
        context.append("")
        
        # Events
        if events:
            context.append("=== RECENT EVENTS ===")
            for event in events:
                context.append(f"\nEvent: {event.get('title', 'Untitled')}")
                context.append(f"Date: {event.get('occurred_on', 'Not disclosed')}")
                context.append(f"Type: {event.get('event_type', 'unknown')}")
                if event.get('description'):
                    context.append(f"Description: {event['description']}")
                if event.get('round_name'):
                    context.append(f"Round: {event['round_name']}")
                if event.get('amount_usd'):
                    context.append(f"Amount: ${event['amount_usd']:,.0f}")
                if event.get('valuation_usd'):
                    context.append(f"Valuation: ${event['valuation_usd']:,.0f}")
                if event.get('investors'):
                    context.append(f"Investors: {', '.join(event['investors'])}")
            context.append("")
        
        # Products
        if products:
            context.append("=== PRODUCTS & SERVICES ===")
            for product in products:
                context.append(f"\nProduct: {product.get('product_name', 'Unnamed')}")
                if product.get('description'):
                    context.append(f"Description: {product['description']}")
                if product.get('launched_on'):
                    context.append(f"Launched: {product['launched_on']}")
                if product.get('pricing_model'):
                    context.append(f"Pricing: {product['pricing_model']}")
                if product.get('target_customer'):
                    context.append(f"Target: {product['target_customer']}")
            context.append("")
        
        # Leadership
        if leadership:
            context.append("=== LEADERSHIP TEAM ===")
            for leader in leadership:
                name = leader.get('name', 'Unknown')
                title = leader.get('title', 'Unknown role')
                context.append(f"• {name} - {title}")
                if leader.get('bio'):
                    context.append(f"  {leader['bio']}")
            context.append("")
        
        # Snapshots
        if snapshots:
            context.append("=== BUSINESS METRICS ===")
            for snapshot in snapshots:
                context.append(f"\nAs of: {snapshot.get('as_of', 'Unknown date')}")
                if snapshot.get('arr_usd'):
                    context.append(f"ARR: ${snapshot['arr_usd']:,.0f}")
                if snapshot.get('mrr_usd'):
                    context.append(f"MRR: ${snapshot['mrr_usd']:,.0f}")
                if snapshot.get('employees'):
                    context.append(f"Employees: {snapshot['employees']}")
                if snapshot.get('customers'):
                    context.append(f"Customers: {snapshot['customers']}")
                if snapshot.get('growth_description'):
                    context.append(f"Growth: {snapshot['growth_description']}")
            context.append("")
        
        # Visibility
        if visibility:
            context.append("=== MARKET VISIBILITY ===")
            for v in visibility:
                context.append(f"\n{v.get('event_name', 'Unknown event')}")
                if v.get('occurred_on'):
                    context.append(f"Date: {v['occurred_on']}")
                if v.get('description'):
                    context.append(f"Description: {v['description']}")
            context.append("")
        
        # Provenance
        context.append("=== DATA SOURCES ===")
        if company.get('provenance'):
            sources = set()
            for prov in company['provenance']:
                if prov.get('source_url'):
                    sources.add(prov['source_url'])
            for source in sorted(sources):
                context.append(f"• {source}")
        
        return "\n".join(context)
    
    def generate_dashboard(self, company_id: str, payload_path: Path) -> str:
        """
        Generate markdown dashboard from structured payload.
        
        Args:
            company_id: Company ID
            payload_path: Path to payload JSON file
            
        Returns:
            Markdown dashboard text
        """
        # Load payload
        payload = self.load_payload(payload_path)
        company_name = payload['company_record'].get('legal_name', 'Unknown Company')
        
        print(f"\n📄 Generating structured dashboard for {company_name}...")
        
        # Format for LLM
        context = self.format_payload_for_llm(payload)
        
        # System prompt (matching assignment requirements)
        system_prompt = """You are a PE/VC analyst creating investor dashboards for AI companies.
Generate a comprehensive markdown dashboard with these EXACT 8 sections:

# {Company Name}

## 1. Company Overview
- **Legal Name**: 
- **Brand Name**: 
- **Website**: 
- **Headquarters**: 
- **Founded**: 
- **Categories/Industry**: 
- Brief company description (2-3 sentences)

## 2. Business Model and GTM
- Products and services offered
- Target customers and markets
- Go-to-market strategy
- Pricing model (if disclosed)
- Revenue model and monetization approach

## 3. Funding & Investor Profile
- **Total Capital Raised**: 
- **Last Funding Round**: 
- **Last Round Date**: 
- **Last Disclosed Valuation**: 
- **Key Investors**: List all known investors from funding events
- **Funding History**: List recent funding events with dates and amounts

## 4. Growth Momentum
- Recent business metrics (ARR, MRR, customers, employees if disclosed)
- Growth trajectory and milestones
- Product launches and expansions
- Customer adoption and traction indicators
- Geographic expansion (if applicable)

## 5. Visibility & Market Sentiment
- Awards and recognitions (e.g., Forbes AI 50)
- Media coverage and press mentions
- Partnerships and collaborations
- Industry positioning and analyst coverage
- Conference appearances or speaking engagements

## 6. Risks and Challenges
- Disclosed risk factors
- Market or competitive challenges
- Regulatory or operational risks
- Technology or execution risks
- If no specific risks disclosed, note "Not disclosed - requires deeper due diligence"

## 7. Outlook
- Future plans and roadmap (if disclosed)
- Market opportunity and TAM
- Strategic direction
- Expansion plans
- Based on available data, provide brief forward-looking assessment

## 8. Disclosure Gaps
List specific missing information needed for investment decision:
- Financial metrics (revenue, burn rate, profitability)
- Detailed customer metrics
- Employee headcount trends
- Unit economics
- Competitive positioning details
- Other material information gaps

CRITICAL RULES:
- Use ONLY the structured data provided below
- Write "Not disclosed" for any missing information
- DO NOT invent, infer, or speculate on missing data
- Be factual and analytical
- Include all 8 sections even if some have limited information
- This data was extracted from company websites, Forbes AI 50, and public sources"""

        user_prompt = f"Generate a dashboard for this company:\n\n{context}"
        
        # Call LLM
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=2000
        )
        
        dashboard = response.choices[0].message.content
        
        print(f"✅ Generated {len(dashboard)} characters")
        
        return dashboard


def main():
    """Test structured pipeline with a sample company."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    project_root = Path(__file__).parent.parent
    payloads_dir = project_root / "data" / "payloads"
    
    if not payloads_dir.exists() or not list(payloads_dir.glob("*.json")):
        print(f"❌ No payloads found in {payloads_dir}")
        print("   Run Lab 6 (payload assembly) first.")
        return
    
    # Check for API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        return
    
    # Get first payload
    payload_files = list(payloads_dir.glob("*.json"))
    test_payload = payload_files[0]
    
    print(f"Testing with: {test_payload.name}")
    
    # Generate dashboard
    pipeline = StructuredPipeline()
    dashboard = pipeline.generate_dashboard(test_payload.stem, test_payload)
    
    # Save
    output_dir = project_root / "data" / "dashboards" / "structured"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / f"{test_payload.stem}.md"
    with open(output_path, 'w') as f:
        f.write(dashboard)
    
    print(f"\n✅ Dashboard saved to: {output_path}")
    print("\n" + "="*80)
    print(dashboard)
    print("="*80)


if __name__ == "__main__":
    main()
