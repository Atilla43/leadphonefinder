"""Эндпоинты скраппера (кеш)."""

from fastapi import APIRouter, Depends, HTTPException, Query

from core.deps import get_data_reader
from services.data_reader import DataReader

router = APIRouter(prefix="/api/scraper", tags=["scraper"])


@router.get("/cache")
async def list_cache(
    reader: DataReader = Depends(get_data_reader),
) -> dict:
    """Список кешированных запросов скраппера."""
    queries = reader.get_scraper_cache_list()
    return {"queries": queries}


@router.get("/cache/{file_name}")
async def get_cache(
    file_name: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    reader: DataReader = Depends(get_data_reader),
) -> dict:
    """Компании из кеша скраппера."""
    data = reader.get_scraper_cache(file_name)
    if not data:
        raise HTTPException(status_code=404, detail="Cache entry not found")

    companies = data.get("companies", [])
    total = len(companies)
    page = companies[offset: offset + limit]

    # Убираем тяжёлые поля для списка
    items = []
    for c in page:
        items.append({
            "name": c.get("name", ""),
            "address": c.get("address", ""),
            "source": c.get("source", ""),
            "phone": c.get("phone"),
            "category": c.get("category"),
            "rating": c.get("rating"),
            "reviews_count": c.get("reviews_count"),
            "inn": c.get("inn"),
            "website": c.get("website"),
        })

    return {
        "query": data.get("query", ""),
        "companies": items,
        "total": total,
        "offset": offset,
        "limit": limit,
    }
