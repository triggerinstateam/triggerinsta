"""Port of /api/webhook — the comment-automation engine. Public (Meta calls it).

GET  : Meta webhook verification handshake.
POST : process incoming Instagram comment events → reply + DM + dedup + stats.
"""

import json
import logging

from django.conf import settings
from django.db import IntegrityError
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from core.models import AutomationRule, ProcessedComment, User
from core.services import graph_api

logger = logging.getLogger(__name__)


@csrf_exempt
def webhook(request):
    if request.method == "GET":
        return _verify(request)
    if request.method == "POST":
        return _handle_event(request)
    return HttpResponse(status=405)


def _verify(request):
    mode = request.GET.get("hub.mode")
    token = request.GET.get("hub.verify_token")
    challenge = request.GET.get("hub.challenge")
    if mode == "subscribe" and token == settings.VERIFY_TOKEN:
        return HttpResponse(challenge or "", status=200)
    return HttpResponse("Verification failed", status=403)


def _handle_event(request):
    try:
        body = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return HttpResponse("EVENT_RECEIVED", status=200)

    if body.get("object") != "instagram":
        return HttpResponse("EVENT_RECEIVED", status=200)

    for entry in body.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            if change.get("field") != "comments":
                continue
            _process_comment(change.get("value", {}))

    return HttpResponse("EVENT_RECEIVED", status=200)


def _process_comment(comment: dict):
    media_id = (comment.get("media") or {}).get("id")
    comment_text = (comment.get("text") or "").lower().strip()
    commenter = comment.get("from") or {}
    commenter_id = commenter.get("id")
    comment_id = comment.get("id")

    if not (media_id and comment_text and commenter_id and comment_id):
        return

    rule = AutomationRule.objects.filter(media_id=media_id, is_active=True).first()
    if not rule:
        return

    # Automation runs on the Facebook-page-linked business account (page token on
    # graph.facebook.com). Exclude Instagram-Login accounts, whose tokens target
    # graph.instagram.com and would not work for these reply/DM calls.
    connected = (
        User.objects.filter(instagram_connected=True)
        .exclude(instagram_account_type="INSTAGRAM")
        .first()
    )
    if not connected or not connected.instagram_access_token:
        return
    token = connected.instagram_access_token
    page_id = connected.instagram_account_id

    if rule.keyword.lower() not in comment_text:
        return

    dedup_key = f"{commenter_id}:{media_id}"
    if ProcessedComment.objects.filter(dedup_key=dedup_key).exists():
        return

    comment_ok = graph_api.reply_to_comment(comment_id, rule.reply_to_comment, token)
    dm_ok = graph_api.send_instagram_dm(commenter_id, rule.reply_to_dm, token, page_id)

    username = commenter.get("username") or commenter.get("name") or "unknown"
    if username == "unknown":
        fetched = graph_api.fetch_username_for_comment(comment_id, token)
        username = fetched or commenter_id

    try:
        ProcessedComment.objects.create(
            dedup_key=dedup_key,
            rule=rule,
            username=username,
            comment_text=comment_text,
        )
    except IntegrityError:
        logger.info("Duplicate dedupKey, skipping stats update")
        return

    rule.triggers += 1
    if comment_ok or dm_ok:
        rule.replies_sent += 1
    rule.last_triggered_at = timezone.now()
    rule.save(update_fields=["triggers", "replies_sent", "last_triggered_at"])

    logger.info("Comment reply: %s", "OK" if comment_ok else "FAILED")
    logger.info("Instagram DM: %s", "OK" if dm_ok else "FAILED (needs approval)")
