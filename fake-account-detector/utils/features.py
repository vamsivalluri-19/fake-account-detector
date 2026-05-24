from __future__ import annotations

from typing import Dict, List


FEATURE_COLUMNS = [
    "followers_count",
    "following_count",
    "media_count",
    "has_profile_pic",
    "bio_length",
    "username_length",
    "digit_count_in_username",
    "followers_following_ratio",
]


def extract_features(
    *,
    username: str,
    bio: str,
    followers_count: int,
    following_count: int,
    media_count: int,
    has_profile_pic: int,
    # Optional enrichment fields (best-effort)
    is_verified: bool = False,
    external_url: str | None = None,
    followers_list: list | None = None,
    following_list: list | None = None,
    posts: list | None = None,
) -> Dict[str, float]:
    cleaned_username = (username or "").strip()
    cleaned_bio = (bio or "").strip()

    username_length = len(cleaned_username)
    digit_count = sum(char.isdigit() for char in cleaned_username)
    bio_length = len(cleaned_bio)
    ratio = float(followers_count) / (float(following_count) + 1.0)

    # --- Account verification / external links ---
    import re

    has_verified_link = 1.0 if external_url else 0.0

    # Detect email or phone in bio (simple heuristic)
    email_in_bio = 1.0 if re.search(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", cleaned_bio) else 0.0
    phone_in_bio = 1.0 if re.search(r"\+?\d[\d\-\s]{6,}\d", cleaned_bio) else 0.0
    email_or_phone = 1.0 if (email_in_bio or phone_in_bio) else 0.0

    # Count external links mentioned in bio (http/https) + provided external_url
    links_in_bio = re.findall(r"https?://[^\s]+", cleaned_bio)
    linked_external_profiles_count = float(len(links_in_bio) + (1 if external_url else 0))

    # Reciprocal follow ratio (mutuals / following)
    mutuals = 0
    if followers_list and following_list:
        try:
            follower_usernames = {x.get('username') for x in followers_list if isinstance(x, dict)}
            following_usernames = {x.get('username') for x in following_list if isinstance(x, dict)}
            mutuals = len(follower_usernames.intersection(following_usernames))
        except Exception:
            mutuals = 0

    reciprocal_follow_ratio = float(mutuals) / (float(following_count) + 1.0)

    # Posting frequency and engagement ratios (best-effort if posts include timestamps/engagement)
    posts = posts or []
    avg_posts_per_day = 0.0
    avg_likes = 0.0
    avg_comments = 0.0
    if posts and isinstance(posts, list):
        # posts may contain dicts with 'timestamp', 'likes', 'comments'
        timestamps = []
        likes = []
        comments = []
        for p in posts:
            if isinstance(p, dict):
                ts = p.get('timestamp') or p.get('created_at')
                if ts:
                    timestamps.append(ts)
                if isinstance(p.get('likes'), (int, float)):
                    likes.append(p.get('likes'))
                if isinstance(p.get('comments'), (int, float)):
                    comments.append(p.get('comments'))

        try:
            if timestamps:
                from dateutil import parser as dateparser
                dates = [dateparser.parse(t) for t in timestamps]
                span_days = max(1.0, (max(dates) - min(dates)).days or 1.0)
                avg_posts_per_day = float(len(dates)) / span_days
        except Exception:
            avg_posts_per_day = float(len(posts)) / max(1.0, 365.0)

        if likes:
            avg_likes = float(sum(likes)) / len(likes)
        if comments:
            avg_comments = float(sum(comments)) / len(comments)

    else:
        # Fallback: normalize by year to get coarse posting frequency
        avg_posts_per_day = float(media_count) / 365.0

    likes_to_followers_ratio = float(avg_likes) / (float(followers_count) + 1.0)
    comments_to_followers_ratio = float(avg_comments) / (float(followers_count) + 1.0)

    return {
        "followers_count": float(followers_count),
        "following_count": float(following_count),
        "media_count": float(media_count),
        "has_profile_pic": float(has_profile_pic),
        "bio_length": float(bio_length),
        "username_length": float(username_length),
        "digit_count_in_username": float(digit_count),
        "followers_following_ratio": float(ratio),
        # Extra heuristic features (not part of model by default)
        "is_verified_flag": float(1.0 if is_verified else 0.0),
        "has_verified_link": float(has_verified_link),
        "email_or_phone": float(email_or_phone),
        "linked_external_profiles_count": float(linked_external_profiles_count),
        "reciprocal_follow_ratio": float(reciprocal_follow_ratio),
        "avg_posts_per_day": float(avg_posts_per_day),
        "likes_to_followers_ratio": float(likes_to_followers_ratio),
        "comments_to_followers_ratio": float(comments_to_followers_ratio),
    }


def features_to_vector(features: Dict[str, float]) -> List[float]:
    return [features[column] for column in FEATURE_COLUMNS]
