"""
Smart text preprocessor - Extract only relevant information from scraped pages
"""
import re
from typing import Dict, List, Optional


class TextPreprocessor:
    """Intelligently filter and extract relevant text from scraped pages"""
    
    # Keywords for different data elements
    FUNDING_KEYWORDS = [
        'raised', 'funding', 'series', 'round', 'million', 'billion', 
        'investment', 'valuation', 'investors', 'led by', 'participated',
        'announced', 'closed', 'capital', 'venture'
    ]
    
    HEADCOUNT_KEYWORDS = [
        'employees', 'team members', 'people', 'staff', 'workforce',
        'headcount', 'joined', 'growing team', 'hiring'
    ]
    
    LOCATION_KEYWORDS = [
        'headquarters', 'hq', 'based in', 'located in', 'offices in',
        'presence in', 'operates in', 'founded in', 'city', 'country'
    ]
    
    PRODUCT_KEYWORDS = [
        'product', 'platform', 'solution', 'service', 'offering',
        'technology', 'features', 'capabilities', 'tools'
    ]
    
    CUSTOMER_KEYWORDS = [
        'customer', 'client', 'used by', 'trusted by', 'partner',
        'case study', 'success story', 'enterprise'
    ]
    
    LEADERSHIP_KEYWORDS = [
        'ceo', 'founder', 'co-founder', 'chief', 'president', 'vp',
        'vice president', 'director', 'head of', 'leadership', 'executive'
    ]
    
    def __init__(self):
        """Initialize preprocessor"""
        pass
    
    def extract_sentences_with_keywords(
        self, 
        text: str, 
        keywords: List[str], 
        max_sentences: int = 10
    ) -> str:
        """
        Extract sentences containing specific keywords
        
        Args:
            text: Full text to search
            keywords: List of keywords to match
            max_sentences: Maximum sentences to return
            
        Returns:
            Filtered text with only relevant sentences
        """
        if not text:
            return ""
        
        # Split into sentences (simple approach)
        sentences = re.split(r'[.!?]+', text)
        
        relevant = []
        keywords_lower = [k.lower() for k in keywords]
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if any keyword is in this sentence
            sentence_lower = sentence.lower()
            if any(keyword in sentence_lower for keyword in keywords_lower):
                relevant.append(sentence)
                
                if len(relevant) >= max_sentences:
                    break
        
        return '. '.join(relevant) + '.' if relevant else ""
    
    def extract_first_n_chars(self, text: str, n: int = 2000) -> str:
        """Extract first N characters, ending at sentence boundary"""
        if not text or len(text) <= n:
            return text
        
        # Find last sentence boundary within limit
        truncated = text[:n]
        last_period = truncated.rfind('.')
        
        if last_period > 0:
            return truncated[:last_period + 1]
        
        return truncated + "..."
    
    def filter_homepage(self, text: str) -> str:
        """
        Extract relevant info from homepage
        - Company description, tagline, core offering
        """
        # Take first 2500 chars (usually has the main description)
        return self.extract_first_n_chars(text, 2500)
    
    def filter_about(self, text: str) -> str:
        """
        Extract relevant info from about page
        - Company history, founding story, mission, location, LEADERSHIP
        """
        # Get location mentions
        location_text = self.extract_sentences_with_keywords(
            text, self.LOCATION_KEYWORDS, max_sentences=5
        )
        
        # Get leadership mentions (CRITICAL!)
        leadership_text = self.extract_sentences_with_keywords(
            text, self.LEADERSHIP_KEYWORDS, max_sentences=10
        )
        
        # Get first section (usually has main story)
        main_text = self.extract_first_n_chars(text, 3500)
        
        result = main_text
        if location_text:
            result += f"\n\nLocations: {location_text}"
        if leadership_text:
            result += f"\n\nLeadership: {leadership_text}"
        
        return result
    
    def filter_blog(self, text: str) -> str:
        """
        Extract relevant info from blog
        - Funding announcements, major partnerships, product launches
        """
        # Focus on funding-related content
        funding_text = self.extract_sentences_with_keywords(
            text, self.FUNDING_KEYWORDS, max_sentences=8
        )
        
        if funding_text:
            return funding_text
        
        # If no funding mentions, take first 2000 chars
        return self.extract_first_n_chars(text, 2000)
    
    def filter_press(self, text: str) -> str:
        """
        Extract relevant info from press/newsroom
        - Press releases about funding, partnerships, milestones
        """
        # Similar to blog - focus on funding
        funding_text = self.extract_sentences_with_keywords(
            text, self.FUNDING_KEYWORDS, max_sentences=10
        )
        
        return funding_text if funding_text else self.extract_first_n_chars(text, 2000)
    
    def filter_careers(self, text: str) -> str:
        """
        Extract relevant info from careers page
        - Headcount, office locations, hiring focus
        """
        # Get headcount mentions
        headcount_text = self.extract_sentences_with_keywords(
            text, self.HEADCOUNT_KEYWORDS, max_sentences=5
        )
        
        # Get location mentions
        location_text = self.extract_sentences_with_keywords(
            text, self.LOCATION_KEYWORDS, max_sentences=5
        )
        
        # Combine
        filtered = []
        if headcount_text:
            filtered.append(f"Headcount info: {headcount_text}")
        if location_text:
            filtered.append(f"Locations: {location_text}")
        
        return '\n\n'.join(filtered) if filtered else self.extract_first_n_chars(text, 1500)
    
    def filter_product(self, text: str) -> str:
        """
        Extract relevant info from product page
        - Product offerings, features, pricing tiers
        """
        # Product pages are CRITICAL - keep more content
        # Get product-related sentences
        product_text = self.extract_sentences_with_keywords(
            text, self.PRODUCT_KEYWORDS, max_sentences=15
        )
        
        return product_text if product_text else self.extract_first_n_chars(text, 4000)
    
    def filter_pricing(self, text: str) -> str:
        """
        Extract relevant info from pricing page
        - Pricing tiers, plans, product editions
        """
        # Pricing is CRITICAL - keep more content
        return self.extract_first_n_chars(text, 4000)
    
    def filter_customers(self, text: str) -> str:
        """
        Extract relevant info from customers page
        - Customer names, case studies, testimonials
        """
        # Get customer mentions
        customer_text = self.extract_sentences_with_keywords(
            text, self.CUSTOMER_KEYWORDS, max_sentences=10
        )
        
        return customer_text if customer_text else self.extract_first_n_chars(text, 2000)
    
    def filter_partners(self, text: str) -> str:
        """
        Extract relevant info from partners page
        - Partner names, integrations, ecosystem
        """
        return self.extract_first_n_chars(text, 2000)
    
    def filter_team(self, text: str) -> str:
        """
        Extract relevant info from team/leadership page
        - Executive names, titles, backgrounds
        """
        # Leadership is CRITICAL - keep more content
        leadership_text = self.extract_sentences_with_keywords(
            text, self.LEADERSHIP_KEYWORDS, max_sentences=20
        )
        
        return leadership_text if leadership_text else self.extract_first_n_chars(text, 4000)
    
    def preprocess_scraped_data(self, scraped_data: Dict[str, Dict]) -> Dict[str, str]:
        """
        Preprocess all scraped data with smart filtering
        
        Args:
            scraped_data: Dictionary with page_type -> {text, source_url, crawled_at}
            
        Returns:
            Filtered data dictionary with page_type -> filtered_text
        """
        filtered = {}
        
        for page_type, page_info in scraped_data.items():
            text = page_info.get('text', '')
            
            if not text:
                continue
            
            # Apply appropriate filter based on page type
            if page_type == 'homepage':
                filtered_text = self.filter_homepage(text)
            elif page_type == 'about':
                filtered_text = self.filter_about(text)
            elif page_type == 'blog':
                filtered_text = self.filter_blog(text)
            elif page_type == 'press':
                filtered_text = self.filter_press(text)
            elif page_type == 'careers':
                filtered_text = self.filter_careers(text)
            elif page_type == 'product':
                filtered_text = self.filter_product(text)
            elif page_type == 'pricing':
                filtered_text = self.filter_pricing(text)
            elif page_type == 'customers':
                filtered_text = self.filter_customers(text)
            elif page_type == 'partners':
                filtered_text = self.filter_partners(text)
            elif page_type == 'team':
                filtered_text = self.filter_team(text)
            else:
                # Default: first 2000 chars
                filtered_text = self.extract_first_n_chars(text, 2000)
            
            if filtered_text:
                filtered[page_type] = filtered_text
        
        return filtered
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate (1 token ≈ 4 chars)"""
        return len(text) // 4
    
    def get_filtered_stats(self, original_data: Dict, filtered_data: Dict) -> Dict:
        """Get statistics about filtering"""
        original_chars = sum(len(v.get('text', '')) for v in original_data.values())
        filtered_chars = sum(len(v) for v in filtered_data.values())
        
        return {
            'original_chars': original_chars,
            'filtered_chars': filtered_chars,
            'reduction_pct': (1 - filtered_chars / original_chars) * 100 if original_chars > 0 else 0,
            'original_tokens_est': self.estimate_tokens(str(original_chars)),
            'filtered_tokens_est': self.estimate_tokens(str(filtered_chars))
        }

