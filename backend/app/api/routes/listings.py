from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.schemas.listing import ListingDetail, ListingMapResponse
from app.services.listing_service import ListingService

router = APIRouter(prefix="/listings", tags=["listings"])
service = ListingService()


@router.get("/map", response_model=ListingMapResponse)
def get_map_listings(
    min_price: int | None = Query(default=None, ge=0),
    max_price: int | None = Query(default=None, ge=0),
    province: str | None = None,
    limit: int | None = Query(default=None, ge=1, le=2000),
) -> ListingMapResponse:
    return service.list_map(min_price=min_price, max_price=max_price, province=province, limit=limit)


@router.get("/{listing_id}", response_model=ListingDetail)
def get_listing_detail(listing_id: UUID) -> ListingDetail:
    listing = service.get_by_id(listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing
