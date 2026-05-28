import os
import logging
import json
import asyncio
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass, asdict, field
from bs4 import BeautifulSoup

# Detect Playwright availability early to provide clear fallbacks
try:
    # Importing the async API confirms Playwright is installed
    import playwright  # type: ignore
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    PLAYWRIGHT_AVAILABLE = False
    logger.info("Playwright not available in this environment; fetch_instagram_profile will return a descriptive error.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class InstagramProfile:
    """Data class for Instagram profile information"""
    username: str
    full_name: str
    bio: str
    followers_count: int
    following_count: int
    media_count: int
    is_private: bool = False
    profile_pic_url: Optional[str] = None
    is_verified: bool = False
    external_url: Optional[str] = None
    followers: List[Dict[str, Any]] = field(default_factory=list)
    following: List[Dict[str, Any]] = field(default_factory=list)
    posts: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary"""
        return asdict(self)




def _extract_profile_from_html(html_content: str) -> Optional[InstagramProfile]:
    """
    Extract Instagram profile data from HTML using BeautifulSoup4
    
    Args:
        html_content: HTML content of Instagram profile page
        
    Returns:
        InstagramProfile or None
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for script tag with window.__INITIAL_STATE__ or similar
        scripts = soup.find_all('script', {'type': 'application/json'})
        
        profile_data = None
        for script in scripts:
            try:
                data = json.loads(script.string)
                if 'user' in data or 'username' in data:
                    profile_data = data
                    break
            except (json.JSONDecodeError, TypeError):
                continue
        
        # Fallback: Extract from meta tags if JSON not found
        if not profile_data:
            username_meta = soup.find('meta', {'property': 'og:title'})
            bio_meta = soup.find('meta', {'property': 'og:description'})
            pic_meta = soup.find('meta', {'property': 'og:image'})
            
            # Extract from title: "username (@username) • Instagram"
            username = username_meta.get('content', '').split(' (')[0] if username_meta else None
            bio = bio_meta.get('content', '') if bio_meta else ''
            profile_pic_url = pic_meta.get('content', '') if pic_meta else None
            
            if username:
                # Try to extract counts from bio
                # Format: "X Followers, Y Following, Z Posts - ..."
                followers_count = 0
                following_count = 0
                media_count = 0
                
                import re
                followers_match = re.search(r'(\d+)\s+Followers?', bio)
                if followers_match:
                    followers_count = int(followers_match.group(1))
                
                following_match = re.search(r'(\d+)\s+Following', bio)
                if following_match:
                    following_count = int(following_match.group(1))
                
                posts_match = re.search(r'(\d+)\s+Posts?', bio)
                if posts_match:
                    media_count = int(posts_match.group(1))
                
                return InstagramProfile(
                    username=username,
                    full_name=username,
                    bio=bio,
                    followers_count=followers_count,
                    following_count=following_count,
                    media_count=media_count,
                    profile_pic_url=profile_pic_url,
                )
        
        # Parse JSON profile data
        if profile_data:
            user_info = profile_data.get('user', profile_data)
            
            return InstagramProfile(
                username=user_info.get('username', ''),
                full_name=user_info.get('full_name', ''),
                bio=user_info.get('biography', ''),
                followers_count=user_info.get('follower_count', 0),
                following_count=user_info.get('following_count', 0),
                media_count=user_info.get('media_count', 0),
                is_private=user_info.get('is_private', False),
                profile_pic_url=user_info.get('profile_pic_url', None),
                is_verified=user_info.get('is_verified', False),
                external_url=user_info.get('external_url') or user_info.get('external_urls') or None,
            )
        
        return None
        
    except Exception as e:
        logger.warning(f"Error extracting profile from HTML: {e}")
        return None


async def _fetch_via_playwright(
    username: str,
    headless: bool = True,
    fetch_details: bool = False,
) -> Tuple[Optional[InstagramProfile], Optional[str]]:
    """
    Fetch Instagram profile using Playwright browser automation
    
    Args:
        username: Instagram username
        headless: Whether to run browser in headless mode
        
    Returns:
        Tuple of (InstagramProfile, error_message)
    """
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            try:
                # Navigate to Instagram profile
                await page.goto(f'https://www.instagram.com/{username}/', 
                              wait_until='domcontentloaded',
                              timeout=12000)
                
                # Wait for content to load
                # Wait for page to be interactive (faster than networkidle)
                try:
                    await asyncio.wait_for(
                        page.wait_for_load_state('networkidle'),
                        timeout=2
                    )
                except asyncio.TimeoutError:
                    logger.debug(f"Network idle timeout for {username}, continuing with current content")
                    pass
                
                # Get page content
                content = await page.content()

                # Extract profile from HTML
                profile = _extract_profile_from_html(content)

                if not profile:
                    return None, "Could not extract profile data from HTML"

                # Optionally fetch followers / following lists (may require interaction)
                if fetch_details and not profile.is_private:
                    # Helper to scrape modal list (followers/following)
                    async def _scrape_modal(selector_button_text: str, limit: int = 200):
                        try:
                            # Click the link that opens the modal (Followers / Following)
                            # Buttons are anchors under header; use text match
                            await page.locator(f"text={selector_button_text}").first.click()
                            # Wait for modal
                            await page.wait_for_selector('div[role="dialog"] ul', timeout=5000)
                            modal = page.locator('div[role="dialog"] ul')

                            # Scroll modal to load items
                            prev_height = 0
                            items = set()
                            for _ in range(30):
                                # collect anchors inside modal
                                anchors = await modal.locator('li a').all()
                                for a in anchors:
                                    try:
                                        href = await a.get_attribute('href')
                                        if href and href.startswith('/'):
                                            uname = href.strip('/').split('/')[0]
                                            if uname:
                                                items.add(uname)
                                    except Exception:
                                        continue

                                # scroll
                                await page.evaluate('el => el.scrollTop = el.scrollHeight', modal.element_handle())
                                await asyncio.sleep(0.2)
                                height = await page.evaluate('el => el.scrollHeight', modal.element_handle())
                                if height == prev_height:
                                    break
                                prev_height = height
                                if len(items) >= limit:
                                    break

                            # Close modal (esc)
                            await page.keyboard.press('Escape')
                            return list(items)[:limit]
                        except Exception as e:
                            logger.debug(f"Error scraping modal {selector_button_text}: {e}")
                            try:
                                await page.keyboard.press('Escape')
                            except Exception:
                                pass
                            return []

                    # Scrape followers and following (best effort)
                    followers = await _scrape_modal('Followers', limit=300)
                    following = await _scrape_modal('Following', limit=300)

                    profile.followers = [{'username': u} for u in followers]
                    profile.following = [{'username': u} for u in following]

                logger.info(f"Successfully fetched profile for {username} via Playwright")
                return profile, None
                    
            finally:
                await context.close()
                await browser.close()
                
    except Exception as e:
        error_msg = f"Playwright error: {str(e)}"
        logger.warning(error_msg)
        return None, error_msg


def _fetch_via_playwright_sync(
    username: str,
    headless: bool = True,
    fetch_details: bool = False,
) -> Tuple[Optional[InstagramProfile], Optional[str]]:
    """
    Synchronous wrapper for Playwright fetching
    
    Args:
        username: Instagram username
        headless: Whether to run browser in headless mode
        
    Returns:
        Tuple of (InstagramProfile, error_message)
    """
    try:
        # Try to get existing event loop, if not, create a new one
        try:
            loop = asyncio.get_running_loop()
            # If we're here, there's a running loop (e.g., in Jupyter)
            import concurrent.futures
            import threading

            # Run in a separate thread to avoid blocking
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _fetch_via_playwright(username, headless, fetch_details))
                return future.result(timeout=120)
        except RuntimeError:
            # No running loop, safe to use asyncio.run()
            return asyncio.run(_fetch_via_playwright(username, headless, fetch_details))
    except Exception as e:
        error_msg = f"Playwright sync wrapper error: {str(e)}"
        logger.warning(error_msg)
        return None, error_msg


def fetch_instagram_profile(
    username: str,
    *,
    session_id: Optional[str] = None,
    fetch_details: bool = False,
    headless: bool = True,
) -> Tuple[Optional[InstagramProfile], Optional[str]]:
    """
    Fetch Instagram profile using Playwright browser automation
    
    Args:
        username: Instagram username to fetch
        session_id: Session ID (for future use)
        fetch_details: Whether to fetch followers, following, and posts (not yet implemented)
        headless: Whether to run Playwright in headless mode
        
    Returns:
        Tuple of (InstagramProfile object, error message)
        - Returns profile if successful, error message otherwise
    """
    if not username:
        return None, "Username is required"
    
    username = username.strip()
    logger.info(f"Fetching Instagram profile for {username} using Playwright")
    if not PLAYWRIGHT_AVAILABLE:
        return None, (
            "Playwright is not installed in this environment. "
            "This host cannot run browser-based scraping. "
            "To enable scraping, deploy to a host with Playwright installed or run a separate scraping service."
        )

    try:
        result = _fetch_via_playwright_sync(username, headless, fetch_details=fetch_details)
        if isinstance(result, tuple):
            return result
        # Handle case where result is future/promise
        import concurrent.futures
        if isinstance(result, concurrent.futures.Future):
            return result.result(timeout=30)
    except Exception as e:
        logger.warning(f"Playwright method failed: {e}")
        return None, str(e)

    return None, "Unable to fetch Instagram profile"


# Legacy function for backward compatibility
def get_instagram_data(username: str) -> Dict[str, Any]:
    """
    Legacy function for backward compatibility
    
    Args:
        username: Instagram username
        
    Returns:
        Dictionary with profile data or error
    """
    profile, error = fetch_instagram_profile(username)
    
    if error:
        return {"error": error}
    
    return profile.to_dict()


# Test
if __name__ == "__main__":
    username = input("Enter username: ")
    result = fetch_instagram_profile(username)
    if result[0]:
        print(json.dumps(result[0].to_dict(), indent=2))
    else:
        print(f"Error: {result[1]}")
