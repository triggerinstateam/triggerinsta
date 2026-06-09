from django.http import JsonResponse
from django.urls import path

from core.views import (
    activity,
    ai,
    analytics,
    dashboard,
    instagram,
    internal,
    media,
    oauth,
    proxy_image,
    rules,
    webhook,
)


def health(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health/", health),
    path("rules", rules.rules),
    path("instagram/media", instagram.media),
    path("instagram/status", instagram.status),
    path("instagram/disconnect", instagram.disconnect),
    path("instagram/oauth/exchange", oauth.exchange),
    path("instagram/login/exchange", oauth.instagram_login_exchange),
    path("media/verify", media.verify),
    path("proxy-image", proxy_image.proxy_image),
    path("dashboard", dashboard.dashboard),
    path("analytics", analytics.analytics),
    path("activity", activity.activity),
    path("ai/suggestions", ai.suggestions),
    path("webhook", webhook.webhook),
    path("internal/users/upsert", internal.upsert_user),
]
