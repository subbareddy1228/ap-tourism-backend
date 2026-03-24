import asyncio
import json
import logging
from typing import Optional

from src.core.config import settings
from src.core.elasticsearch import (
    get_es_client,
    INDEX_DESTINATIONS,
    INDEX_HOTELS,
    INDEX_PACKAGES,
    INDEX_TEMPLES,
)
from src.core.redis import get_redis_client
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


def _hit_to_search_hit(hit: dict, entity_type: str) -> SearchHit:
    source: dict = hit.get("_source") or {}
    return SearchHit(
        id=hit["_id"],
        type=entity_type,
        name=source.get("name", ""),
        score=float(hit.get("_score") or 0.0),
        data=source,
    )


def _build_bool_query(must: list, filters: list) -> dict:
    query: dict = {"bool": {}}
    query["bool"]["must"] = must if must else [{"match_all": {}}]
    if filters:
        query["bool"]["filter"] = filters
    return query


async def global_search(q: str, user_id: Optional[int], limit: int = 5) -> GlobalSearchResult:
    es = get_es_client()

    es_query = {
        "multi_match": {
            "query": q,
            "fields": ["name^3", "description", "search_all"],
            "type": "best_fields",
            "fuzziness": "AUTO",
        }
    }

    results = await asyncio.gather(
        es.search(index=INDEX_TEMPLES,      query=es_query, size=limit),
        es.search(index=INDEX_HOTELS,       query=es_query, size=limit),
        es.search(index=INDEX_PACKAGES,     query=es_query, size=limit),
        es.search(index=INDEX_DESTINATIONS, query=es_query, size=limit),
        return_exceptions=True,
    )

    def _extract(res: object, entity_type: str) -> list[SearchHit]:
        if isinstance(res, Exception):
            logger.error("Global search error for %s: %s", entity_type, res)
            return []
        return [_hit_to_search_hit(h, entity_type) for h in res["hits"]["hits"]]  # type: ignore[index]

    temples      = _extract(results[0], "temple")
    hotels       = _extract(results[1], "hotel")
    packages     = _extract(results[2], "package")
    destinations = _extract(results[3], "destination")

    if user_id is not None:
        await _save_recent_search(user_id, q)

    return GlobalSearchResult(
        query=q,
        total=len(temples) + len(hotels) + len(packages) + len(destinations),
        temples=temples,
        hotels=hotels,
        packages=packages,
        destinations=destinations,
    )


async def get_suggestions(q: str) -> list[SuggestionItem]:
    redis = get_redis_client()

    if redis is not None:
        try:
            cached = await redis.get(f"suggestions:{q.lower()}")
            if cached:
                return [SuggestionItem(**item) for item in json.loads(cached)]
        except Exception as exc:
            logger.warning("Redis get failed for suggestions: %s", exc)

    es = get_es_client()
    es_query = {
        "multi_match": {
            "query": q,
            "fields": ["name^3", "search_all"],
            "type": "best_fields",
            "fuzziness": "AUTO",
        }
    }

    results = await asyncio.gather(
        es.search(index=INDEX_TEMPLES,      query=es_query, size=2, source=["name"]),
        es.search(index=INDEX_HOTELS,       query=es_query, size=2, source=["name"]),
        es.search(index=INDEX_PACKAGES,     query=es_query, size=1, source=["name"]),
        es.search(index=INDEX_DESTINATIONS, query=es_query, size=1, source=["name"]),
        return_exceptions=True,
    )

    type_map = ["temple", "hotel", "package", "destination"]
    suggestions: list[SuggestionItem] = []

    for i, res in enumerate(results):
        if isinstance(res, Exception):
            continue
        for hit in res["hits"]["hits"]:  # type: ignore[index]
            name = (hit.get("_source") or {}).get("name", "")
            if name:
                suggestions.append(SuggestionItem(text=name, type=type_map[i], id=hit["_id"]))
            if len(suggestions) >= 5:
                break
        if len(suggestions) >= 5:
            break

    suggestions = suggestions[:5]

    if redis is not None:
        try:
            await redis.setex(
                f"suggestions:{q.lower()}",
                settings.REDIS_SUGGESTIONS_TTL,
                json.dumps([s.model_dump() for s in suggestions]),
            )
        except Exception as exc:
            logger.warning("Redis setex failed: %s", exc)

    return suggestions


async def get_autocomplete(q: str) -> list[AutocompleteItem]:
    es = get_es_client()

    suggest_body = {
        "name_suggest": {
            "prefix": q,
            "completion": {
                "field": "suggest",
                "size": 5,
                "skip_duplicates": True,
                "fuzzy": {"fuzziness": 1},
            },
        }
    }

    results = await asyncio.gather(
        es.search(index=INDEX_TEMPLES,      suggest=suggest_body, source=False),
        es.search(index=INDEX_HOTELS,       suggest=suggest_body, source=False),
        es.search(index=INDEX_PACKAGES,     suggest=suggest_body, source=False),
        es.search(index=INDEX_DESTINATIONS, suggest=suggest_body, source=False),
        return_exceptions=True,
    )

    type_map = ["temple", "hotel", "package", "destination"]
    items: list[AutocompleteItem] = []

    for i, res in enumerate(results):
        if isinstance(res, Exception):
            continue
        for bucket in res.get("suggest", {}).get("name_suggest", []):  # type: ignore[union-attr]
            for option in bucket.get("options", []):
                name = option.get("text") or (option.get("_source") or {}).get("name", "")
                if name:
                    items.append(AutocompleteItem(name=name, type=type_map[i], id=option["_id"]))

    return items[:10]


async def _save_recent_search(user_id: str, query: str) -> None:
    redis = get_redis_client()
    if redis is None:
        return
    try:
        key = f"recent_searches:{user_id}"
        await redis.lrem(key, 0, query)
        await redis.lpush(key, query)
        await redis.ltrim(key, 0, settings.REDIS_RECENT_SEARCHES_MAX - 1)
        await redis.expire(key, settings.REDIS_RECENT_SEARCHES_TTL)
    except Exception as exc:
        logger.warning("Could not save recent search: %s", exc)


async def get_recent_searches(user_id: str) -> list[str]:
    redis = get_redis_client()
    if redis is None:
        return []
    try:
        key = f"recent_searches:{user_id}"
        return await redis.lrange(key, 0, settings.REDIS_RECENT_SEARCHES_MAX - 1)
    except Exception as exc:
        logger.warning("Could not get recent searches: %s", exc)
        return []


async def search_temples(params: TempleSearchParams) -> EntitySearchResult:
    es = get_es_client()
    must: list = []
    filters: list = []

    if params.q:
        must.append({"multi_match": {"query": params.q, "fields": ["name^3", "deity^2", "description"], "fuzziness": "AUTO"}})
    if params.name:
        must.append({"match": {"name": {"query": params.name, "fuzziness": "AUTO"}}})
    if params.deity:
        must.append({"match": {"deity": {"query": params.deity, "fuzziness": "AUTO"}}})
    if params.district:
        filters.append({"term": {"district": params.district}})
    if params.darshan_type:
        filters.append({"term": {"darshan_type": params.darshan_type}})

    aggs = {
        "districts":     {"terms": {"field": "district",     "size": 20}},
        "darshan_types": {"terms": {"field": "darshan_type", "size": 10}},
    }

    res = await es.search(
        index=INDEX_TEMPLES,
        query=_build_bool_query(must, filters),
        aggs=aggs,
        from_=(params.page - 1) * params.size,
        size=params.size,
    )

    return EntitySearchResult(
        query=params.q,
        total=res["hits"]["total"]["value"],
        page=params.page,
        size=params.size,
        results=[_hit_to_search_hit(h, "temple") for h in res["hits"]["hits"]],
        facets={
            "districts":     {b["key"]: b["doc_count"] for b in res["aggregations"]["districts"]["buckets"]},
            "darshan_types": {b["key"]: b["doc_count"] for b in res["aggregations"]["darshan_types"]["buckets"]},
        },
    )


async def search_hotels(params: HotelSearchParams) -> EntitySearchResult:
    es = get_es_client()
    must: list = []
    filters: list = []

    if params.q:
        must.append({"multi_match": {"query": params.q, "fields": ["name^3", "description"], "fuzziness": "AUTO"}})
    if params.name:
        must.append({"match": {"name": {"query": params.name, "fuzziness": "AUTO"}}})
    if params.city:
        filters.append({"term": {"city": params.city}})
    if params.amenities:
        filters.append({"terms": {"amenities": params.amenities}})
    if params.star_rating is not None:
        filters.append({"term": {"star_rating": params.star_rating}})
    if params.min_price is not None or params.max_price is not None:
        price_range: dict = {}
        if params.min_price is not None:
            price_range["gte"] = params.min_price
        if params.max_price is not None:
            price_range["lte"] = params.max_price
        filters.append({"range": {"price_per_night": price_range}})

    aggs = {
        "cities":       {"terms": {"field": "city",        "size": 20}},
        "star_ratings": {"terms": {"field": "star_rating", "size": 5}},
        "price_ranges": {
            "range": {
                "field": "price_per_night",
                "ranges": [{"to": 1000}, {"from": 1000, "to": 3000}, {"from": 3000, "to": 6000}, {"from": 6000}],
            }
        },
    }

    res = await es.search(
        index=INDEX_HOTELS,
        query=_build_bool_query(must, filters),
        aggs=aggs,
        from_=(params.page - 1) * params.size,
        size=params.size,
    )

    return EntitySearchResult(
        query=params.q,
        total=res["hits"]["total"]["value"],
        page=params.page,
        size=params.size,
        results=[_hit_to_search_hit(h, "hotel") for h in res["hits"]["hits"]],
        facets={
            "cities":       {b["key"]: b["doc_count"] for b in res["aggregations"]["cities"]["buckets"]},
            "star_ratings": {b["key"]: b["doc_count"] for b in res["aggregations"]["star_ratings"]["buckets"]},
            "price_ranges": [
                {"label": f"{b.get('from', 0)}-{b.get('to', '∞')}", "count": b["doc_count"]}
                for b in res["aggregations"]["price_ranges"]["buckets"]
            ],
        },
    )


async def search_packages(params: PackageSearchParams) -> EntitySearchResult:
    es = get_es_client()
    must: list = []
    filters: list = []

    if params.q:
        must.append({"multi_match": {"query": params.q, "fields": ["name^3", "destination^2", "description"], "fuzziness": "AUTO"}})
    if params.name:
        must.append({"match": {"name": {"query": params.name, "fuzziness": "AUTO"}}})
    if params.destination:
        must.append({"match": {"destination": {"query": params.destination, "fuzziness": "AUTO"}}})
    if params.package_type:
        filters.append({"term": {"package_type": params.package_type}})
    if params.min_duration is not None or params.max_duration is not None:
        dur: dict = {}
        if params.min_duration is not None: dur["gte"] = params.min_duration
        if params.max_duration is not None: dur["lte"] = params.max_duration
        filters.append({"range": {"duration_days": dur}})
    if params.min_budget is not None or params.max_budget is not None:
        bud: dict = {}
        if params.min_budget is not None: bud["gte"] = params.min_budget
        if params.max_budget is not None: bud["lte"] = params.max_budget
        filters.append({"range": {"budget": bud}})

    aggs = {
        "package_types": {"terms": {"field": "package_type",        "size": 10}},
        "destinations":  {"terms": {"field": "destination.keyword", "size": 20}},
    }

    res = await es.search(
        index=INDEX_PACKAGES,
        query=_build_bool_query(must, filters),
        aggs=aggs,
        from_=(params.page - 1) * params.size,
        size=params.size,
    )

    return EntitySearchResult(
        query=params.q,
        total=res["hits"]["total"]["value"],
        page=params.page,
        size=params.size,
        results=[_hit_to_search_hit(h, "package") for h in res["hits"]["hits"]],
        facets={
            "package_types": {b["key"]: b["doc_count"] for b in res["aggregations"]["package_types"]["buckets"]},
            "destinations":  {b["key"]: b["doc_count"] for b in res["aggregations"]["destinations"]["buckets"]},
        },
    )


async def search_destinations(params: DestinationSearchParams) -> EntitySearchResult:
    es = get_es_client()
    must: list = []
    filters: list = []

    if params.q:
        must.append({"multi_match": {"query": params.q, "fields": ["name^3", "description"], "fuzziness": "AUTO"}})
    if params.name:
        must.append({"match": {"name": {"query": params.name, "fuzziness": "AUTO"}}})
    if params.destination_type:
        filters.append({"term": {"destination_type": params.destination_type}})
    if params.district:
        filters.append({"term": {"district": params.district}})

    aggs = {
        "types":    {"terms": {"field": "destination_type", "size": 10}},
        "districts":{"terms": {"field": "district",         "size": 20}},
    }

    res = await es.search(
        index=INDEX_DESTINATIONS,
        query=_build_bool_query(must, filters),
        aggs=aggs,
        from_=(params.page - 1) * params.size,
        size=params.size,
    )

    return EntitySearchResult(
        query=params.q,
        total=res["hits"]["total"]["value"],
        page=params.page,
        size=params.size,
        results=[_hit_to_search_hit(h, "destination") for h in res["hits"]["hits"]],
        facets={
            "types":    {b["key"]: b["doc_count"] for b in res["aggregations"]["types"]["buckets"]},
            "districts":{b["key"]: b["doc_count"] for b in res["aggregations"]["districts"]["buckets"]},
        },
    )
