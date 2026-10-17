"""Conversión de las respuestas JSON de YouTube a `TrackMetadata`."""
from __future__ import annotations

import re
from typing import Any

from app.catalog.providers.models import TrackMetadata

_DURATION_RE = re.compile(
    r"^P(?:(?P<d>\d+)D)?(?:T(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+)S)?)?$"
)
_THUMBNAIL_PREFERENCE = ("medium", "high", "default")


def parse_iso8601_duration(value: str) -> int:
    """'PT3M45S' -> 225 segundos. Devuelve 0 si el formato no es válido."""
    match = _DURATION_RE.match(value or "")
    if not match:
        return 0
    parts = {key: int(num or 0) for key, num in match.groupdict().items()}
    return parts["d"] * 86400 + parts["h"] * 3600 + parts["m"] * 60 + parts["s"]


def pick_thumbnail(thumbnails: dict[str, Any]) -> str | None:
    for size in _THUMBNAIL_PREFERENCE:
        if size in thumbnails and thumbnails[size].get("url"):
            return thumbnails[size]["url"]
    return None


def map_video_item(item: dict[str, Any]) -> TrackMetadata:
    """Un elemento de `videos.list` -> `TrackMetadata`."""
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    status = item.get("status", {})
    return TrackMetadata(
        track_id=item["id"],
        title=snippet.get("title", ""),
        channel_title=snippet.get("channelTitle", ""),
        duration_s=parse_iso8601_duration(item.get("contentDetails", {}).get("duration", "")),
        view_count=int(stats.get("viewCount", 0)),
        like_count=int(stats.get("likeCount", 0)),  # puede venir oculto
        thumbnail_url=pick_thumbnail(snippet.get("thumbnails", {})),
        is_embeddable=bool(status.get("embeddable", False)),
    )
