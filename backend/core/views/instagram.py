"""Ports of /api/instagram/{media,status,disconnect}. Scoped to X-User-Email."""

import logging

from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.models import User
from core.services import graph_api

logger = logging.getLogger(__name__)


def _current_user(request):
    email = getattr(request.user, "email", None)
    if not email:
        return None
    return User.objects.filter(email=email).first()


@api_view(["GET"])
def media(request):
    user = _current_user(request)
    if user is None:
        return Response({"error": "Not authenticated"}, status=401)
    if not user.instagram_connected:
        return Response({"error": "Instagram not connected"}, status=400)

    try:
        if user.instagram_account_type == "INSTAGRAM":
            # Authenticated via Instagram Login → Instagram Graph (graph.instagram.com).
            items = graph_api.fetch_user_media_instagram(user.instagram_access_token)
        else:
            # Facebook-page-linked business account → Facebook Graph.
            items = graph_api.fetch_user_media(user.instagram_account_id, user.instagram_access_token)
    except graph_api.GraphAPIError as err:
        if err.code == 190:
            user.instagram_connected = False
            user.save(update_fields=["instagram_connected"])
        logger.error("Error fetching Instagram media: %s", err)
        return Response({"error": f"Instagram API error: {err}"}, status=500)

    items.sort(key=lambda m: m.get("timestamp", ""), reverse=True)
    return Response({
        "success": True,
        "media": items,
        "total": len(items),
        "account": {
            "username": user.instagram_username,
            "accountType": user.instagram_account_type,
        },
    })


@api_view(["GET"])
def status(request):
    user = _current_user(request)
    if user is None:
        return Response({"isConnected": False, "error": "Not authenticated"})
    if not user.instagram_connected or not user.instagram_access_token:
        return Response({"isConnected": False})
    return Response({
        "isConnected": True,
        "account": {
            "id": user.instagram_account_id,
            "username": user.instagram_username,
            "accountType": user.instagram_account_type,
            "connectedAt": user.instagram_connected_at.isoformat() if user.instagram_connected_at else None,
        },
    })


@api_view(["POST"])
def disconnect(request):
    user = _current_user(request)
    if user is None:
        return Response({"error": "Not authenticated"}, status=401)
    user.instagram_connected = False
    user.instagram_access_token = None
    user.instagram_account_id = None
    user.instagram_username = None
    user.instagram_account_type = None
    user.instagram_connected_at = None
    user.save()
    return Response({"success": True})
