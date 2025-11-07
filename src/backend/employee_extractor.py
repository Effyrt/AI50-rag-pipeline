"""
Extract employee count and job opening information from scraped content.
"""
import re
from typing import Dict, Optional, List
from datetime import date


class EmployeeDataExtractor:
    """Extract employee and hiring data from website content."""
    
    # Patterns for employee count mentions
    EMPLOYEE_PATTERNS = [
        r'team of (\d+)[\+\s]*(?:people|employees|members)?',
        r'(\d+)[\+\s]*(?:employee|people|team member|staff|person team)',
        r'staff of (\d+)',
        r'workforce of (\d+)',
        r'we are (\d+)[\+\s]*(?:people|employees)',
        r'grown to (\d+)[\+\s]*(?:people|employees)',
        r'(\d+)[\+\s]*person (?:team|company)',
    ]
    
    # Patterns for employee ranges (e.g., "50-100 employees")
    EMPLOYEE_RANGE_PATTERNS = [
        r'(\d+)\s*[-–to]\s*(\d+)\s*(?:employee|people|team member)',
        r'between (\d+) and (\d+) (?:employee|people)',
    ]
    
    # Patterns for job counts (e.g., "15 open positions")
    JOB_COUNT_PATTERNS = [
        r'(\d+)\s*(?:open|available|current)?\s*(?:position|role|job|opening|career)',
        r'(\d+)\s*jobs?\s*(?:available|open)?',
        r'hiring for (\d+)\s*(?:position|role)',
        r'(\d+)\s*vacancies',
    ]
    
    # Keywords for office locations
    LOCATION_KEYWORDS = [
        'office', 'headquarters', 'location', 'based in', 'hq'
    ]
    
    # Common cities (for location extraction)
    MAJOR_CITIES = [
        'san francisco', 'new york', 'london', 'paris', 'tokyo', 'singapore',
        'seattle', 'austin', 'boston', 'chicago', 'los angeles', 'toronto',
        'berlin', 'amsterdam', 'bangalore', 'mumbai', 'sydney', 'dublin'
    ]
    
    def extract_employee_count(self, text: str) -> Dict[str, any]:
        """
        Extract employee count from text.
        
        Returns dict with:
        - headcount_total: int or None
        - headcount_estimate: str or None (e.g., "50-100", "100+")
        - confidence: float (0-1)
        """
        text_lower = text.lower()
        
        result = {
            'headcount_total': None,
            'headcount_estimate': None,
            'confidence': 0.0
        }
        
        # Try to find exact numbers first
        for pattern in self.EMPLOYEE_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                # Get the highest number found (usually most recent/accurate)
                numbers = [int(m) for m in matches if m.isdigit()]
                if numbers:
                    max_count = max(numbers)
                    # Sanity check: reasonable range for startups/companies
                    if 5 <= max_count <= 100000:
                        result['headcount_total'] = max_count
                        result['confidence'] = 0.8
                        
                        # Also set estimate
                        if '+' in text_lower:
                            result['headcount_estimate'] = f"{max_count}+"
                        else:
                            result['headcount_estimate'] = str(max_count)
                        
                        return result
        
        # Try to find ranges (e.g., "50-100 employees")
        for pattern in self.EMPLOYEE_RANGE_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                for match in matches:
                    if len(match) == 2:
                        low, high = int(match[0]), int(match[1])
                        if 5 <= low < high <= 100000:
                            result['headcount_estimate'] = f"{low}-{high}"
                            result['headcount_total'] = (low + high) // 2  # Midpoint
                            result['confidence'] = 0.6
                            return result
        
        return result
    
    def extract_job_openings(self, careers_text: str) -> Dict[str, any]:
        """
        Extract job opening count from careers page.
        
        Returns dict with:
        - job_openings_count: int or None
        - hiring_focus: List[str] (departments hiring)
        - confidence: float
        """
        result = {
            'job_openings_count': None,
            'hiring_focus': [],
            'confidence': 0.0
        }
        
        if not careers_text:
            return result
        
        text_lower = careers_text.lower()
        
        # Try to find explicit job counts
        for pattern in self.JOB_COUNT_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                numbers = [int(m) for m in matches if m.isdigit()]
                if numbers:
                    # Use the highest count found
                    max_count = max(numbers)
                    if 1 <= max_count <= 500:  # Reasonable range
                        result['job_openings_count'] = max_count
                        result['confidence'] = 0.7
                        break
        
        # If no explicit count, try to count job listings more intelligently
        if result['job_openings_count'] is None:
            # Method 1: Count job titles/headings (more reliable)
            # Look for common job title patterns
            job_title_patterns = [
                r'(?:senior|junior|lead|principal|staff)?\s*(?:software|backend|frontend|full.?stack|ml|ai|data|product|sales|marketing|design|engineer|developer|manager|director|analyst|scientist)',
                r'(?:engineer|developer|manager|designer|analyst|scientist|specialist|coordinator|executive|associate)',
            ]
            
            job_titles_found = set()
            for pattern in job_title_patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                job_titles_found.update(matches)
            
            # Method 2: Count job listing indicators
            job_indicators = [
                'apply now', 'view job', 'see position', 'learn more',
                'apply for', 'job description', 'role:', 'position:',
                'open role', 'we\'re hiring', 'join our team', 'open position',
                'job opening', 'career opportunity', 'work with us'
            ]
            
            indicator_count = sum(text_lower.count(indicator) for indicator in job_indicators)
            
            # Method 3: Count list items that look like jobs (common pattern)
            # Look for numbered lists or bullet points with job-like content
            list_item_pattern = r'(?:^|\n)\s*[•\-\d+\.]\s+.*?(?:engineer|developer|manager|designer|analyst|scientist|specialist)'
            list_items = len(re.findall(list_item_pattern, text_lower, re.MULTILINE | re.IGNORECASE))
            
            # Use the most reliable method
            if len(job_titles_found) > 0:
                # Count unique job titles found
                result['job_openings_count'] = min(len(job_titles_found), 200)  # Cap at 200
                result['confidence'] = 0.6  # Medium confidence
            elif list_items > 0:
                # Use list item count
                result['job_openings_count'] = min(list_items, 200)
                result['confidence'] = 0.5
            elif indicator_count > 0:
                # Fallback to indicator count (less reliable)
                estimated_jobs = max(indicator_count // 2, indicator_count // 3)  # More conservative
                if estimated_jobs >= 1:
                    result['job_openings_count'] = min(estimated_jobs, 200)
                    result['confidence'] = 0.4  # Lower confidence
        
        # Extract hiring focus (departments)
        departments = {
            'engineering': ['engineer', 'developer', 'software', 'technical', 'backend', 'frontend'],
            'sales': ['sales', 'account executive', 'business development'],
            'marketing': ['marketing', 'growth', 'content', 'brand'],
            'product': ['product manager', 'product designer'],
            'operations': ['operations', 'ops', 'support'],
            'data': ['data scientist', 'data engineer', 'analyst', 'ml engineer'],
            'design': ['designer', 'ux', 'ui'],
        }
        
        for dept, keywords in departments.items():
            if any(keyword in text_lower for keyword in keywords):
                result['hiring_focus'].append(dept)
        
        return result
    
    def extract_office_locations(self, text: str) -> List[str]:
        """Extract office locations from text."""
        text_lower = text.lower()
        locations = []
        
        # Look for major cities
        for city in self.MAJOR_CITIES:
            if city in text_lower:
                # Capitalize properly
                locations.append(city.title())
        
        # Look for location patterns
        location_patterns = [
            r'(?:office|located|based) (?:in|at) ([A-Z][a-z]+(?:,?\s+[A-Z][a-z]+)*)',
            r'headquarters in ([A-Z][a-z]+(?:,?\s+[A-Z][a-z]+)*)',
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if match and len(match) > 2:
                    locations.append(match.strip())
        
        # Deduplicate
        return list(set(locations))
    
    def extract_remote_policy(self, text: str) -> Optional[str]:
        """Extract remote work policy from text."""
        text_lower = text.lower()
        
        if any(keyword in text_lower for keyword in ['remote-first', 'fully remote', 'remote only']):
            return 'Remote-first'
        elif any(keyword in text_lower for keyword in ['hybrid', 'flexible', 'remote and office']):
            return 'Hybrid'
        elif any(keyword in text_lower for keyword in ['in-office', 'on-site', 'office-based']):
            return 'In-office'
        
        return None
    
    def create_snapshot(
        self,
        company_id: str,
        about_text: str = '',
        careers_text: str = '',
        homepage_text: str = '',
        team_text: str = ''
    ) -> Optional[Dict]:
        """
        Create a snapshot from various page texts.
        
        Args:
            company_id: Company identifier
            about_text: Content from about page
            careers_text: Content from careers page
            homepage_text: Content from homepage
            team_text: Content from team page
            
        Returns:
            Snapshot dict or None if no meaningful data found
        """
        # Combine relevant texts
        employee_text = ' '.join([about_text, homepage_text, team_text])
        
        # Extract employee data
        employee_data = self.extract_employee_count(employee_text)
        
        # Extract job data
        job_data = self.extract_job_openings(careers_text)
        
        # Extract locations
        locations = self.extract_office_locations(employee_text + ' ' + careers_text)
        
        # Extract remote policy
        remote_policy = self.extract_remote_policy(careers_text)
        
        # Only create snapshot if we found meaningful data
        if (employee_data['headcount_total'] or 
            employee_data['headcount_estimate'] or 
            job_data['job_openings_count']):
            
            return {
                'company_id': company_id,
                'as_of': date.today(),
                'headcount_total': employee_data['headcount_total'],
                'headcount_estimate': employee_data['headcount_estimate'],
                'job_openings_count': job_data['job_openings_count'],
                'hiring_focus': job_data['hiring_focus'],
                'office_locations': locations,
                'remote_policy': remote_policy,
                'confidence': max(employee_data['confidence'], job_data['confidence']),
                'schema_version': '2.0.0',
                'provenance': []
            }
        
        return None

