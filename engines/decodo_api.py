import os
import httpx
from datetime import datetime
from dotenv import load_dotenv
from .base import Scraper, ScrapeResult

load_dotenv()

class DecodoAPIScraper(Scraper):
    """
    Scraper implementation for Decodo Web Scraping API.
    
    Requires DECODO_AUTH_TOKEN environment variable to be set.
    Set it in your .env file
    """
    def __init__(self):
        self.api_token = os.getenv("DECODO_AUTH_TOKEN")
        if not self.api_token:
            raise RuntimeError("DECODO_AUTH_TOKEN environment variable not set.")
        self.base_url = "https://scraper-api.decodo.com/v2/scrape"
        
        # Ensure the token has "Basic " prefix if not already present
        if not self.api_token.startswith("Basic "):
            self.auth_header = f"Basic {self.api_token}"
        else:
            self.auth_header = self.api_token

    async def scrape(self, url: str, run_id: str) -> ScrapeResult:
        error = None
        status_code = 500
        content = ""  # ← Renamed from html
        content_size = 0
        
        try:
            headers = {
                "Accept": "application/json",
                "Authorization": self.auth_header,
                "Content-Type": "application/json"
            }
            
            payload = {
                "url": url,
                #"headless": "html"
                "markdown": True
            }
            
            async with httpx.AsyncClient() as client:
                try:
                    resp = await client.post(
                        self.base_url,
                        headers=headers,
                        json=payload,
                        timeout=180.0
                    )
                    status_code = resp.status_code

                    if status_code == 200:
                        # Only parse response if status is 200
                        try:
                            if resp.headers.get("Content-Type", "").startswith("application/json"):
                                data = resp.json()
                                
                                # Extract from results array structure with multiple fallbacks
                                if "results" in data and len(data.get("results", [])) > 0:
                                    result = data["results"][0]
                                    # Try multiple field names to get maximum content
                                    content = (
                                        result.get("content") or
                                        result.get("markdown") or
                                        result.get("text") or
                                        result.get("html") or
                                        result.get("body") or
                                        ""
                                    )
                                else:
                                    # Fallback: check top-level fields
                                    content = (
                                        data.get("content") or
                                        data.get("markdown") or
                                        data.get("text") or
                                        data.get("html") or
                                        resp.text or
                                        ""
                                    )
                            else:
                                content = resp.text or ""
                            
                            content_size = len(content.encode("utf-8")) if content else 0
                        except (KeyError, ValueError, IndexError) as e:
                            error = f"Failed to parse response: {str(e)}"
                            content = resp.text or ""
                            content_size = len(content.encode("utf-8")) if content else 0
                    
                except httpx.TimeoutException:
                    error = "Timeout: Request took longer than 180 seconds"
                    status_code = 408
                except httpx.RequestError as e:
                    error = f"RequestError: {str(e)}"
                    status_code = 503
                    
        except Exception as e:
            content = ""
            content_size = 0
            status_code = 500
            error = f"{type(e).__name__}: {str(e)}"
        
        return ScrapeResult(
            run_id=run_id,
            scraper="decodo_api",
            url=url,
            status_code=status_code or 500,
            error=error,
            content_size=content_size,
            format="markdown",
            created_at=datetime.now().isoformat(),
            content=content or None,  # ← Updated variable name
        )