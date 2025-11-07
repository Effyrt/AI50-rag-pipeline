"""
GitHub API integration for fetching repository visibility metrics
"""
import re
import requests
from typing import Optional, Dict, List
from urllib.parse import urlparse


class GitHubAPI:
    """Fetch GitHub repository metrics using public API"""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub API client
        
        Args:
            token: Optional GitHub personal access token (for higher rate limits)
                   If None, uses unauthenticated requests (60 req/hour)
        """
        self.token = token
        self.headers = {}
        if token:
            self.headers['Authorization'] = f'token {token}'
        
        # User agent required by GitHub API
        self.headers['User-Agent'] = 'AI50-RAG-Pipeline'
    
    def extract_github_urls(self, text: str) -> List[str]:
        """
        Extract GitHub repository URLs from text
        
        Args:
            text: Text content to search
            
        Returns:
            List of GitHub repo URLs found
        """
        # Pattern to match GitHub URLs (org or repo)
        # Matches: github.com/owner or github.com/owner/repo
        pattern = r'https?://(?:www\.)?github\.com/([a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_.-]+)?)'
        
        matches = re.findall(pattern, text)
        
        # Deduplicate
        unique_matches = list(set(matches))
        urls = [f"https://github.com/{match}" for match in unique_matches]
        
        return urls
    
    def parse_github_url(self, url: str) -> Optional[Dict[str, str]]:
        """
        Parse GitHub URL to extract owner and repo name
        
        Args:
            url: GitHub repository URL
            
        Returns:
            Dict with 'owner' and 'repo' keys (repo may be empty for org URLs), or None if invalid
        """
        try:
            parsed = urlparse(url)
            
            if 'github.com' not in parsed.netloc:
                return None
            
            # Remove leading/trailing slashes and split
            parts = parsed.path.strip('/').split('/')
            
            if len(parts) >= 2:
                return {
                    'owner': parts[0],
                    'repo': parts[1].replace('.git', '')
                }
            elif len(parts) == 1 and parts[0]:
                # Org URL only (no repo)
                return {
                    'owner': parts[0],
                    'repo': ''  # Empty string indicates org-only URL
                }
            
            return None
        except Exception:
            return None
    
    def get_repo_stats(self, owner: str, repo: str) -> Optional[Dict]:
        """
        Fetch repository statistics from GitHub API
        
        Args:
            owner: Repository owner (username or org)
            repo: Repository name
            
        Returns:
            Dict with repo stats or None if failed
        """
        try:
            url = f"{self.BASE_URL}/repos/{owner}/{repo}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                return {
                    'stars': data.get('stargazers_count', 0),
                    'forks': data.get('forks_count', 0),
                    'watchers': data.get('watchers_count', 0),
                    'open_issues': data.get('open_issues_count', 0),
                    'created_at': data.get('created_at'),
                    'updated_at': data.get('updated_at'),
                    'pushed_at': data.get('pushed_at'),
                    'language': data.get('language'),
                    'description': data.get('description'),
                    'homepage': data.get('homepage'),
                    'topics': data.get('topics', []),
                    'license': data.get('license', {}).get('name') if data.get('license') else None,
                    'archived': data.get('archived', False),
                    'disabled': data.get('disabled', False)
                }
            elif response.status_code == 404:
                print(f"      Repository not found: {owner}/{repo}")
                return None
            elif response.status_code == 403:
                print(f"      Rate limit exceeded or access forbidden")
                return None
            else:
                print(f"      GitHub API error: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            print(f"      Error fetching GitHub data: {e}")
            return None
    
    def get_contributors_count(self, owner: str, repo: str) -> Optional[int]:
        """
        Get number of contributors (expensive API call)
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Number of contributors or None
        """
        try:
            url = f"{self.BASE_URL}/repos/{owner}/{repo}/contributors"
            
            # Use per_page=1 and check Link header for total
            response = requests.get(
                url, 
                headers=self.headers, 
                params={'per_page': 1, 'anon': 'true'},
                timeout=10
            )
            
            if response.status_code == 200:
                # Check if Link header exists with pagination
                link_header = response.headers.get('Link', '')
                
                if 'last' in link_header:
                    # Extract last page number from Link header
                    import re
                    match = re.search(r'page=(\d+)>; rel="last"', link_header)
                    if match:
                        return int(match.group(1))
                
                # If no pagination, count the response
                return len(response.json())
            
            return None
            
        except Exception as e:
            print(f"      Error fetching contributors: {e}")
            return None
    
    def get_repo_metrics(self, repo_url: str) -> Optional[Dict]:
        """
        Get comprehensive metrics for a GitHub repository
        
        Args:
            repo_url: Full GitHub repository URL
            
        Returns:
            Dict with all metrics or None if failed
        """
        parsed = self.parse_github_url(repo_url)
        
        if not parsed:
            print(f"      Invalid GitHub URL: {repo_url}")
            return None
        
        owner = parsed['owner']
        repo = parsed['repo']
        
        print(f"      Fetching GitHub metrics for {owner}/{repo}...")
        
        # Get basic stats
        stats = self.get_repo_stats(owner, repo)
        
        if not stats:
            return None
        
        # Get contributors count (optional, can be slow)
        contributors = self.get_contributors_count(owner, repo)
        if contributors:
            stats['contributors'] = contributors
        
        return stats
    
    def find_and_fetch_repos(self, text: str) -> List[Dict]:
        """
        Find GitHub URLs in text and fetch metrics for all
        
        Args:
            text: Text content to search
            
        Returns:
            List of dicts with repo URL and metrics
        """
        urls = self.extract_github_urls(text)
        
        if not urls:
            return []
        
        print(f"   🐙 Found {len(urls)} GitHub URL(s)")
        
        results = []
        
        for url in urls:
            parsed = self.parse_github_url(url)
            if not parsed:
                continue
            
            # Check if it's an org URL (no repo name)
            if not parsed['repo']:  # Empty string means org-only URL
                # Try common repo names for orgs
                print(f"      Found org URL: {url}")
                org = parsed['owner']
                
                # Try common repo naming patterns
                common_names = [
                    org,  # e.g., huggingface/huggingface
                    f"{org}.github.io",  # e.g., huggingface/huggingface.github.io
                    "transformers",  # Common for ML companies
                    "platform",  # Common for platforms
                    "core"  # Common for core libs
                ]
                
                for repo_name in common_names:
                    test_url = f"https://github.com/{org}/{repo_name}"
                    metrics = self.get_repo_metrics(test_url)
                    if metrics:
                        results.append({
                            'repo_url': test_url,
                            'metrics': metrics
                        })
                        print(f"      ✅ Found repo: {org}/{repo_name}")
                        break  # Use first successful match
            else:
                # Full repo URL
                metrics = self.get_repo_metrics(url)
                
                if metrics:
                    results.append({
                        'repo_url': url,
                        'metrics': metrics
                    })
        
        return results


def get_github_visibility(scraped_data: Dict[str, Dict]) -> Optional[Dict]:
    """
    Extract GitHub visibility metrics from scraped company data
    
    Args:
        scraped_data: Dictionary with page_type -> {text, source_url, crawled_at}
        
    Returns:
        Dict with GitHub metrics or None
    """
    github_api = GitHubAPI()
    
    # Combine all text to search for GitHub URLs
    all_text = ""
    for page_data in scraped_data.values():
        all_text += page_data.get('text', '') + "\n"
    
    # Find and fetch repo metrics
    repos = github_api.find_and_fetch_repos(all_text)
    
    if not repos:
        return None
    
    # If multiple repos, use the one with most stars (likely the main repo)
    main_repo = max(repos, key=lambda x: x['metrics'].get('stars', 0))
    
    return {
        'github_url': main_repo['repo_url'],
        'github_stars': main_repo['metrics'].get('stars', 0),
        'github_forks': main_repo['metrics'].get('forks', 0),
        'github_contributors': main_repo['metrics'].get('contributors'),
        'github_language': main_repo['metrics'].get('language'),
        'github_topics': main_repo['metrics'].get('topics', []),
        'github_updated_at': main_repo['metrics'].get('pushed_at')
    }

