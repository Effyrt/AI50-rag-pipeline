"""
Fallback handler for blocked websites
Uses alternative sources when direct scraping fails
"""
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Fallback data for commonly blocked sites
FALLBACK_DATA = {
    "openai": {
        "company_name": "OpenAI",
        "description": "OpenAI is an AI research and deployment company. Their mission is to ensure artificial general intelligence benefits all of humanity. They are known for ChatGPT and GPT models.",
        "products": ["ChatGPT", "GPT-4", "DALL-E", "API Platform"],
        "founded": 2015,
        "hq": "San Francisco, CA",
        "note": "Direct scraping blocked - using public knowledge"
    },
    "midjourney": {
        "company_name": "Midjourney",
        "description": "Midjourney is an AI-powered image generation platform that creates art from text descriptions.",
        "products": ["Midjourney Bot", "Image Generation"],
        "founded": 2021,
        "note": "Direct scraping blocked - using public knowledge"
    }
}


def get_fallback_content(company_id: str) -> Dict:
    """Get fallback content for blocked websites"""
    
    # Normalize company_id
    company_id = company_id.lower().replace(' ', '-')
    
    if company_id in FALLBACK_DATA:
        data = FALLBACK_DATA[company_id]
        
        # Create formatted text version
        content = f"""
=== FALLBACK DATA (Website blocks automated access) ===

Company: {data['company_name']}
Description: {data['description']}
Products: {', '.join(data['products'])}
Founded: {data.get('founded', 'Not disclosed')}
Headquarters: {data.get('hq', 'Not disclosed')}

Note: {data['note']}
This data is based on publicly available information as the company website 
blocks automated scraping tools.
        """.strip()
        
        logger.info(f"✓ Using fallback data for {company_id}")
        
        return {
            'success': True,
            'content': content,
            'is_fallback': True,
            'pages_found': ['fallback']
        }
    
    return {
        'success': False,
        'error': f'Website blocked and no fallback available for {company_id}'
    }
