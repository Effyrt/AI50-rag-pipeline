"""
Prompt templates for LLM extraction and generation.
"""
from typing import Dict, Any


class ExtractionPrompts:
    """Prompts for structured data extraction using instructor."""
    
    COMPANY_PROFILE = """Extract company profile information from the provided website content.

Rules:
- Extract ONLY information explicitly stated in the content
- If a field is not mentioned, leave it as None/empty
- Do not infer or guess values (especially funding amounts, valuations, headcount)
- For location, extract city, state, and country separately
- For categories, choose from the predefined enum values
- Include provenance: note the source URL and relevant text snippet

Website content:
{content}
"""

    FUNDING_EVENTS = """Extract all funding events mentioned in the provided content.

Rules:
- Extract each funding round as a separate event
- Include: date, round type, amount, investors, valuation (if disclosed)
- If valuation is not explicitly stated, leave it as None
- Lead investors should be in the lead_investors list
- All investors should be in the investors list
- Extract event description with relevant details

Content:
{content}
"""

    TEAM_EXTRACTION = """Extract leadership team information from the provided content.

Rules:
- Extract each leader as a separate entry
- Include: full name, role, whether they're a founder
- Extract background: previous companies, education
- Include LinkedIn URLs if present
- Do not invent or guess information not present in the content

Content:
{content}
"""

    PRODUCT_EXTRACTION = """Extract product/service information from the provided content.

Rules:
- Extract each product as a separate entry
- Include: name, description, pricing model, pricing tiers
- For pricing: only extract if explicitly stated
- If pricing is "Contact us" or "Contact sales", set pricing_model to "enterprise_only"
- Extract features, integrations, and customer logos if mentioned
- Include product URLs and API documentation links

Content:
{content}
"""

    SNAPSHOT_EXTRACTION = """Extract current company metrics from the provided content.

Rules:
- This is a point-in-time snapshot, so use the as_of date provided
- Extract: headcount, job openings (by department), hiring focus
- Only extract numbers if explicitly stated (don't estimate)
- For job openings, categorize by: engineering, sales, product, operations
- Extract hiring signals: "We're hiring", "Join our team", etc.

Content:
{content}

As of date: {as_of_date}
"""

    VISIBILITY_EXTRACTION = """Extract visibility and sentiment metrics from the provided content.

Rules:
- Extract: recent news coverage, social media metrics, developer activity
- For sentiment: analyze tone of recent news (positive, neutral, negative)
- Extract: GitHub stars, Glassdoor rating, news mentions
- Only use numbers that are explicitly stated
- Note source and confidence for each metric

Content:
{content}
"""


class DashboardPrompts:
    """Prompts for investor dashboard generation."""
    
    SYSTEM_PROMPT = """You are an expert financial analyst generating investor diligence dashboards for AI startups.

Your output MUST follow these rules:
1. Use ONLY data provided in the payload - never invent numbers
2. If information is not disclosed, literally write "Not disclosed."
3. For marketing claims (e.g., "We're the #1 platform"), attribute them: "The company states..."
4. Never include personal emails or phone numbers
5. Always include a "Disclosure Gaps" section at the end
6. Output must be valid GitHub-flavored Markdown

Required sections (in order):
1. Company Overview
2. Business Model and GTM
3. Funding & Investor Profile
4. Growth Momentum
5. Visibility & Market Sentiment
6. Risks and Challenges
7. Outlook
8. Disclosure Gaps

Use factual, neutral tone. Focus on data-driven insights for PE/VC investors."""

    STRUCTURED_DASHBOARD = """Generate an investor diligence dashboard for {company_name}.

Use the structured payload below to generate a comprehensive 8-section dashboard.

Payload:
{payload}

Remember:
- Use ONLY the provided data
- Write "Not disclosed." for missing information
- Include "Disclosure Gaps" section
- Output in Markdown format"""

    RAG_DASHBOARD = """Generate an investor diligence dashboard for {company_name}.

Use the retrieved context below to generate a comprehensive 8-section dashboard.

Retrieved Context:
{context}

Remember:
- Use ONLY the provided context
- Write "Not disclosed." for missing information
- Include "Disclosure Gaps" section
- Output in Markdown format"""


def format_extraction_prompt(
    template: str,
    **kwargs: Any
) -> str:
    """
    Format extraction prompt with provided variables.
    
    Args:
        template: Prompt template string
        **kwargs: Variables to inject into template
        
    Returns:
        Formatted prompt string
    """
    return template.format(**kwargs)


def create_messages(
    system_prompt: str,
    user_prompt: str
) -> list[Dict[str, str]]:
    """
    Create chat messages for LLM.
    
    Args:
        system_prompt: System message
        user_prompt: User message
        
    Returns:
        List of message dictionaries
    """
    messages = []
    
    if system_prompt:
        messages.append({
            "role": "system",
            "content": system_prompt
        })
    
    messages.append({
        "role": "user",
        "content": user_prompt
    })
    
    return messages