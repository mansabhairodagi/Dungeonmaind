"""Mapper for converting domain MapLocation models to MapLocationOut schemas."""

from app.base_models.map_base_models import MapLocationOut
from app.domain.map_location import MapLocation


def map_location_to_out(location: MapLocation) -> MapLocationOut:
    """Map a domain MapLocation to a MapLocationOut Pydantic schema.

    Args:
        location: The domain MapLocation instance.

    Returns:
        A MapLocationOut schema instance.
    """
    return MapLocationOut(
        id=location.id,
        session_id=location.session_id,
        canonical_name=location.canonical_name,
        aliases=list(location.aliases),
        event_ids=list(location.event_ids),
        mention_count=location.mention_count,
        first_order=location.first_order,
    )
