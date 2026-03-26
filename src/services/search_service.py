import asyncio
import json
import logging
from typing import Optional

from src.core.config import settings

try:
    from src.core.elasticsearch import (
        get_es_client,
        INDEX_DESTINATIONS,
        INDEX_HOTELS,
        INDEX_PACKAGES,
        INDEX_TEMPLES,
    )
    ES_AVAILABLE = True
except Exception:
    ES_AVAILABLE = False
    get_es_client = None
    INDEX_DESTINATIONS = INDEX_HOTELS = INDEX_PACKAGES = INDEX_TEMPLES = None

from src.core.redis import get_redis
from src.schemas.search import (
    AutocompleteItem,
    DestinationSearchParams,
    EntitySearchResult,
    GlobalSearchResult,
    HotelSearchParams,
    PackageSearchParams,
    SearchHit,
    SuggestionItem,
    TempleSearchParams,
)

logger = logging.getLogger(__name__)


# ---------------- HELPER FUNCTIONS ----------------

def _hit_to_search_hit(hit: dict, entity_type: str) -> SearchHit:
    source = hit.get("_source") or {}

    return SearchHit(
        id=hit["_id"],
        type=entity_type,
        name=source.get("name", ""),
        score=float(hit.get("_score") or 0.0),
        data=source,
    )


def _build_bool_query(must: list, filters: list) -> dict:
    query = {"bool": {}}

    query["bool"]["must"] = must if must else [{"match_all": {}}]

    if filters:
        query["bool"]["filter"] = filters

    return query


# ---------------- GLOBAL SEARCH ----------------

async def global_search(q: str, user_id: Optional[str], limit: int = 5) -> GlobalSearchResult:

    if not ES_AVAILABLE:
        raise RuntimeError("Elasticsearch not available")

    es = get_es_client()

    es_query = {
        "multi_match": {
            "query": q,
            "fields": ["name^3", "description", "search_all"],
            "fuzziness": "AUTO",
        }
    }

    results = await asyncio.gather(
        es.search(index=INDEX_TEMPLES, query=es_query, size=limit),
        es.search(index=INDEX_HOTELS, query=es_query, size=limit),
        es.search(index=INDEX_PACKAGES, query=es_query, size=limit),
        es.search(index=INDEX_DESTINATIONS, query=es_query, size=limit),
        return_exceptions=True,
    )

    def _extract(res, entity_type):
        if isinstance(res, Exception):
            logger.error("Search error for %s: %s", entity_type, res)
            return []

        return [_hit_to_search_hit(h, entity_type) for h in res["hits"]["hits"]]

    temples = _extract(results[0], "temple")
    hotels = _extract(results[1], "hotel")
    packages = _extract(results[2], "package")
    destinations = _extract(results[3], "destination")

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


# ---------------- SUGGESTIONS ----------------

async def get_suggestions(q: str) -> list[SuggestionItem]:
 
    redis = await get_redis()
 
    if redis:
        try:
            cached = await redis.get(f"suggestions:{q.lower()}")
            if cached:
                return [SuggestionItem(**i) for i in json.loads(cached)]
        except Exception as e:
            logger.warning("Redis error: %s", e)
 
    if not ES_AVAILABLE:          # ← ADD THIS
        return []                 # ← return empty list gracefully
 
    es = get_es_client()

    es_query = {
        "multi_match": {
            "query": q,
            "fields": ["name^3", "search_all"],
            "fuzziness": "AUTO",
        }
    }

    results = await asyncio.gather(
        es.search(index=INDEX_TEMPLES, query=es_query, size=2, source=["name"]),
        es.search(index=INDEX_HOTELS, query=es_query, size=2, source=["name"]),
        es.search(index=INDEX_PACKAGES, query=es_query, size=1, source=["name"]),
        es.search(index=INDEX_DESTINATIONS, query=es_query, size=1, source=["name"]),
        return_exceptions=True,
    )

    type_map = ["temple", "hotel", "package", "destination"]

    suggestions = []

    for i, res in enumerate(results):

        if isinstance(res, Exception):
            continue

        for hit in res["hits"]["hits"]:

            name = (hit.get("_source") or {}).get("name")

            if name:
                suggestions.append(
                    SuggestionItem(
                        text=name,
                        type=type_map[i],
                        id=hit["_id"],
                    )
                )

            if len(suggestions) >= 5:
                break

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
            logger.warning("Redis cache error: %s", e)

    return suggestions


# ---------------- RECENT SEARCH ----------------

async def _save_recent_search(user_id: str, query: str):

    redis = await get_redis()

    if not redis:
        return

    try:
        key = f"recent_searches:{user_id}"

        await redis.lrem(key, 0, query)
        await redis.lpush(key, query)

        await redis.ltrim(
            key,
            0,
            settings.REDIS_RECENT_SEARCHES_MAX - 1
        )

        await redis.expire(
            key,
            settings.REDIS_RECENT_SEARCHES_TTL
        )

    except Exception as e:
        logger.warning("Recent search save failed: %s", e)


async def get_recent_searches(user_id: str) -> list[str]:

    redis = await get_redis()

    if not redis:
        return []

    try:
        key = f"recent_searches:{user_id}"

        return await redis.lrange(
            key,
            0,
            settings.REDIS_RECENT_SEARCHES_MAX - 1
        )

    except Exception as e:
        logger.warning("Recent search fetch failed: %s", e)

        return []

async def get_autocomplete(q: str):

    if not ES_AVAILABLE:
        return []

    es = get_es_client()

    suggest_body = {
        "name_suggest": {
            "prefix": q,
            "completion": {
                "field": "suggest",
                "size": 5,
                "skip_duplicates": True
            }
        }
    }

    results = await asyncio.gather(
        es.search(index=INDEX_TEMPLES, suggest=suggest_body, source=False),
        es.search(index=INDEX_HOTELS, suggest=suggest_body, source=False),
        es.search(index=INDEX_PACKAGES, suggest=suggest_body, source=False),
        es.search(index=INDEX_DESTINATIONS, suggest=suggest_body, source=False),
        return_exceptions=True,
    )

    type_map = ["temple", "hotel", "package", "destination"]

    items = []

    for i, res in enumerate(results):
        if isinstance(res, Exception):
            continue

        for bucket in res.get("suggest", {}).get("name_suggest", []):
            for option in bucket.get("options", []):

                name = option.get("text")

                if name:
                    items.append({
                        "name": name,
                        "type": type_map[i],
                        "id": option["_id"]
                    })

    return items[:10]