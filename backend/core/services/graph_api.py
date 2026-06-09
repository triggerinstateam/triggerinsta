"""Meta Graph API helpers (ports of the axios/fetch calls from the Next.js routes).

Graph API version is centralized via settings.GRAPH_API_VERSION (the original
codebase mixed v18/v19; we standardize on v19.0).
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TIMEOUT = 30


def _base() -> str:
    return f"https://graph.facebook.com/{settings.GRAPH_API_VERSION}"


def reply_to_comment(comment_id: str, message: str, token: str) -> bool:
    try:
        resp = requests.post(
            f"{_base()}/{comment_id}/replies",
            params={"access_token": token},
            json={"message": message},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException as err:
        logger.error("Comment reply failed: %s", _err_detail(err))
        return False


def send_instagram_dm(user_id: str, message: str, token: str, page_id: str) -> bool:
    try:
        resp = requests.post(
            f"{_base()}/{page_id}/messages",
            params={"access_token": token},
            json={
                "recipient": {"id": user_id},
                "message": {"text": message},
                "messaging_type": "RESPONSE",
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException as err:
        logger.error("Instagram DM failed: %s", _err_detail(err))
        return False


def fetch_media_details(media_id: str, token: str) -> dict:
    """Return media metadata + a resolved `thumbnail` field. Raises on error."""
    resp = requests.get(
        f"{_base()}/{media_id}",
        params={
            "fields": "media_type,media_url,thumbnail_url,caption",
            "access_token": token,
        },
        timeout=TIMEOUT,
    )
    data = resp.json()
    if not resp.ok:
        raise RuntimeError(data.get("error", {}).get("message", "Failed to fetch media details"))
    thumbnail = data.get("thumbnail_url") if data.get("media_type") == "VIDEO" else data.get("media_url")
    return {**data, "thumbnail": thumbnail}


def fetch_fresh_thumbnail_url(media_id: str, token: str) -> str | None:
    resp = requests.get(
        f"{_base()}/{media_id}",
        params={"fields": "media_type,media_url,thumbnail_url", "access_token": token},
        timeout=TIMEOUT,
    )
    if not resp.ok:
        return None
    data = resp.json()
    return data.get("thumbnail_url") if data.get("media_type") == "VIDEO" else data.get("media_url")


def fetch_username_for_comment(comment_id: str, token: str) -> str | None:
    try:
        resp = requests.get(
            f"{_base()}/{comment_id}",
            params={"fields": "from{username}", "access_token": token},
            timeout=TIMEOUT,
        )
        data = resp.json()
        return (data.get("from") or {}).get("username")
    except requests.RequestException:
        return None


def fetch_user_media(account_id: str, token: str) -> list[dict]:
    """Paginate the full list of an account's media (dashboard/media view)."""
    fields = (
        "id,media_type,media_url,thumbnail_url,permalink,caption,"
        "timestamp,like_count,comments_count"
    )
    endpoint = (
        f"{_base()}/{account_id}/media?fields={fields}&limit=50&access_token={token}"
    )
    media: list[dict] = []
    while endpoint:
        resp = requests.get(endpoint, timeout=TIMEOUT)
        if not resp.ok:
            err = resp.json().get("error", {})
            raise GraphAPIError(
                err.get("message", resp.reason),
                code=err.get("code"),
            )
        data = resp.json()
        media.extend(data.get("data", []))
        endpoint = (data.get("paging") or {}).get("next")
    return media


def fetch_user_media_instagram(token: str) -> list[dict]:
    """Paginate media for an account authenticated via Instagram Login
    (Instagram User access token → graph.instagram.com/me/media)."""
    fields = (
        "id,media_type,media_url,thumbnail_url,permalink,caption,"
        "timestamp,like_count,comments_count"
    )
    endpoint = (
        f"https://graph.instagram.com/me/media?fields={fields}&limit=50&access_token={token}"
    )
    media: list[dict] = []
    while endpoint:
        resp = requests.get(endpoint, timeout=TIMEOUT)
        if not resp.ok:
            err = resp.json().get("error", {})
            raise GraphAPIError(err.get("message", resp.reason), code=err.get("code"))
        data = resp.json()
        media.extend(data.get("data", []))
        endpoint = (data.get("paging") or {}).get("next")
    return media


def fetch_media_for_verify(account_id: str, token: str) -> list[dict]:
    """Paginate id/shortcode/permalink/caption used to resolve a pasted reel URL."""
    endpoint = (
        f"{_base()}/{account_id}/media"
        f"?fields=id,shortcode,permalink,caption&limit=100&access_token={token}"
    )
    media: list[dict] = []
    while endpoint:
        resp = requests.get(endpoint, timeout=TIMEOUT)
        if not resp.ok:
            err = resp.json().get("error", {})
            raise GraphAPIError(err.get("message", resp.reason), code=err.get("code"))
        data = resp.json()
        media.extend(data.get("data", []))
        endpoint = (data.get("paging") or {}).get("next")
    return media


class GraphAPIError(Exception):
    def __init__(self, message: str, code=None):
        super().__init__(message)
        self.code = code


def _err_detail(err: requests.RequestException):
    resp = getattr(err, "response", None)
    if resp is not None:
        try:
            return resp.json()
        except ValueError:
            return resp.text
    return str(err)
