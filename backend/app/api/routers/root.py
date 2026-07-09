"""Root endpoint router."""

from fastapi import APIRouter

router = APIRouter()


@router.get('/')
async def read_root():
    """Root endpoint returning a simple greeting message.

    Returns:
        Dict with a welcome message.
    """
    return {'message': 'Hello I am the root!'}
