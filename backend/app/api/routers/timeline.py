from fastapi import APIRouter, HTTPException, Query, status

from app.api.mappers.timeline_mapper import timeline_event_to_out
from app.base_models.timeline_base_models import (
    TimelineDeleteResponse,
    TimelineEventListResponse,
    TimelineEventOut,
    TimelineGenerateRequest,
    TimelineGenerateResponse,
)
from app.domain.timeline_store import timeline_store
from app.functions.embedding.embedding_model import get_all_transcription_documents
from app.functions.llm.event_extractor import extract_events_from_transcriptions

router = APIRouter()


@router.get('/events', response_model=TimelineEventListResponse)
async def list_events(session_id: str = Query('default', description='Session identifier')):
    events = await timeline_store.get_session_events(session_id)
    return TimelineEventListResponse(
        session_id=session_id, events=[timeline_event_to_out(e) for e in events], total=len(events)
    )


@router.get('/events/{event_id}', response_model=TimelineEventOut)
async def get_event(event_id: str):
    event = await timeline_store.get_event(event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Event not found')
    return timeline_event_to_out(event)


@router.delete('/events/{event_id}', response_model=TimelineDeleteResponse)
async def delete_event(event_id: str):
    deleted = await timeline_store.delete_event(event_id)
    return TimelineDeleteResponse(deleted=deleted, event_id=event_id)


@router.delete('/events', response_model=TimelineDeleteResponse)
async def clear_session_events(
    session_id: str = Query('default', description='Session identifier'),
):
    await timeline_store.clear_session(session_id)
    return TimelineDeleteResponse(deleted=True, event_id=None)


@router.post('/generate', response_model=TimelineGenerateResponse)
async def generate_events(req: TimelineGenerateRequest):
    docs = get_all_transcription_documents()
    if not docs:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail='No transcription documents found. Record and transcribe audio first.',
        )

    texts = [doc.page_content for doc in docs]
    speakers = [doc.metadata.get('player_id', 'unknown') for doc in docs]

    events = extract_events_from_transcriptions(
        texts=texts, speakers=speakers, session_id=req.session_id
    )

    added = await timeline_store.add_events(events)

    return TimelineGenerateResponse(
        session_id=req.session_id,
        events_generated=len(added),
        events=[timeline_event_to_out(e) for e in added],
    )
