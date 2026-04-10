"""
search_service.py
Search powered by PostgreSQL full-text search (pg_trgm + to_tsvector).
Drop-in replacement for the Elasticsearch-backed search service.
"""

import json
import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import AsyncSessionLocal
from src.core.redis import get_redis
from src.schemas.search import (
    AutocompleteItem,
    GlobalSearchResult,
    SearchHit,
    SuggestionItem,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────

def _make_hit(row: dict, entity_type: str) -> SearchHit:
    return SearchHit(
        id=str(row["id"]),
        type=entity_type,
        name=row.get("name", ""),
        score=float(row.get("rank", 0.0)),
        data={k: v for k, v in row.items() if k not in ("id", "rank")},
    )


async def _pg_search(
    db: AsyncSession,
    table: str,
    fields: list[str],
    q: str,
    limit: int,
    extra_select: str = "",
    where: str = "",
) -> list[dict]:
    """
    Generic PostgreSQL full-text search with trigram similarity fallback.
    Uses ts_rank for relevance scoring.
    """
    ts_vector = " || ' ' || ".join(
        [f"coalesce({f}::text, '')" for f in fields]
    )
    query_str = f"""
        SELECT id, name,
               ts_rank(
                   to_tsvector('english', {ts_vector}),
                   plainto_tsquery('english', :q)
               ) AS rank
               {', ' + extra_select if extra_select else ''}
        FROM {table}
        WHERE
            (
                to_tsvector('english', {ts_vector}) @@ plainto_tsquery('english', :q)
                OR name ILIKE :like_q
            )
            {('AND ' + where) if where else ''}
        ORDER BY rank DESC
        LIMIT :limit
    """
    result = await db.execute(
        text(query_str),
        {"q": q, "like_q": f"%{q}%", "limit": limit},
    )
    return [dict(row._mapping) for row in result]


# ──────────────────────────────────────────────
# Global Search
# ──────────────────────────────────────────────

async def global_search(
    q: str,
    user_id: Optional[str],
    limit: int = 5,
) -> GlobalSearchResult:
    async with AsyncSessionLocal() as db:
        temple_rows = await _pg_search(
            db, "temples", ["name", "description", "deity", "district"], q, limit
        )
        hotel_rows = await _pg_search(
            db, "hotels", ["name", "description", "city"], q, limit
        )
        package_rows = await _pg_search(
            db, "packages", ["name", "slug"], q, limit          # ← fixed: no description/type
        )
        destination_rows = await _pg_search(
            db, "destinations", ["name", "description", "tagline", "district"], q, limit  # ← added tagline/district
        )

    temples = [_make_hit(r, "temple") for r in temple_rows]
    hotels = [_make_hit(r, "hotel") for r in hotel_rows]
    packages = [_make_hit(r, "package") for r in package_rows]
    destinations = [_make_hit(r, "destination") for r in destination_rows]

    if user_id:
        await _save_recent_search(user_id, q)

    return GlobalSearchResult(
        query=q,
        total=len(temples) + len(hotels) + len(packages) + len(destinations),
        temples=temples,
        hotels=hotels,
        packages=packages,
        destinations=destinations,
    )


# ──────────────────────────────────────────────
# Suggestions  (Redis-cached)
# ──────────────────────────────────────────────

async def get_suggestions(q: str) -> list[SuggestionItem]:
    redis = await get_redis()

    if redis:
        try:
            cached = await redis.get(f"suggestions:{q.lower()}")
            if cached:
                return [SuggestionItem(**i) for i in json.loads(cached)]
        except Exception as e:
            logger.warning("Redis read error: %s", e)

    suggestions: list[SuggestionItem] = []

    async with AsyncSessionLocal() as db:
        for table, entity_type in [
            ("temples", "temple"),
            ("hotels", "hotel"),
            ("packages", "package"),
            ("destinations", "destination"),
        ]:
            rows = await _pg_search(db, table, ["name"], q, limit=2)
            for row in rows:
                suggestions.append(
                    SuggestionItem(text=row["name"], type=entity_type, id=str(row["id"]))
                )
            if len(suggestions) >= 5:
                break

    suggestions = suggestions[:5]

    if redis:
        try:
            await redis.setex(
                f"suggestions:{q.lower()}",
                settings.REDIS_SUGGESTIONS_TTL,
                json.dumps([s.model_dump() for s in suggestions]),
            )
        except Exception as e:
            logger.warning("Redis write error: %s", e)

    return suggestions


# ──────────────────────────────────────────────
# Autocomplete  (prefix match)
# ──────────────────────────────────────────────

async def get_autocomplete(q: str) -> list[AutocompleteItem]:
    items: list[AutocompleteItem] = []

    async with AsyncSessionLocal() as db:
        for table, entity_type in [
            ("temples", "temple"),
            ("hotels", "hotel"),
            ("packages", "package"),
            ("destinations", "destination"),
        ]:
            result = await db.execute(
                text(
                    f"SELECT id, name FROM {table} "
                    "WHERE name ILIKE :prefix "
                    "ORDER BY name LIMIT 3"
                ),
                {"prefix": f"{q}%"},
            )
            for row in result:
                items.append(
                    AutocompleteItem(
                        name=row.name, type=entity_type, id=str(row.id)
                    )
                )
            if len(items) >= 10:
                break

    return items[:10]


# ──────────────────────────────────────────────
# Entity-specific Search
# ──────────────────────────────────────────────

async def search_temples(q: str, limit: int = 20) -> list[SearchHit]:
    async with AsyncSessionLocal() as db:
        rows = await _pg_search(
            db, "temples", ["name", "description", "deity", "district"], q, limit
        )
    return [_make_hit(r, "temple") for r in rows]


async def search_hotels(q: str, limit: int = 20) -> list[SearchHit]:
    async with AsyncSessionLocal() as db:
        rows = await _pg_search(
            db, "hotels", ["name", "description", "city"], q, limit
        )
    return [_make_hit(r, "hotel") for r in rows]


async def search_packages(q: str, limit: int = 20) -> list[SearchHit]:
    async with AsyncSessionLocal() as db:
        rows = await _pg_search(
            db, "packages", ["name", "slug"], q, limit          # ← fixed: no description/type
        )
    return [_make_hit(r, "package") for r in rows]


async def search_destinations(q: str, limit: int = 20) -> list[SearchHit]:
    async with AsyncSessionLocal() as db:
        rows = await _pg_search(
            db, "destinations", ["name", "description", "tagline", "district"], q, limit  # ← added tagline/district
        )
    return [_make_hit(r, "destination") for r in rows]


# ──────────────────────────────────────────────
# Recent Searches  (Redis)
# ──────────────────────────────────────────────

async def _save_recent_search(user_id: str, query: str) -> None:
    redis = await get_redis()
    if not redis:
        return
    try:
        key = f"recent_searches:{user_id}"
        await redis.lrem(key, 0, query)
        await redis.lpush(key, query)
        await redis.ltrim(key, 0, settings.REDIS_RECENT_SEARCHES_MAX - 1)
        await redis.expire(key, settings.REDIS_RECENT_SEARCHES_TTL)
    except Exception as e:
        logger.warning("Recent search save failed: %s", e)


async def get_recent_searches(user_id: str) -> list[str]:
    redis = await get_redis()
    if not redis:
        return []
    try:
        key = f"recent_searches:{user_id}"
        return await redis.lrange(key, 0, settings.REDIS_RECENT_SEARCHES_MAX - 1)
    except Exception as e:
        logger.warning("Recent search fetch failed: %s", e)
        return []