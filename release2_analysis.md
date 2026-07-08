# Release 2 Analysis: Interactive Timeline

> **Release 2 Deadline:** July 31, 2026
> **Scope:** "Implement the Interactive Timeline"

---

## What Release 2 Requires (from Project Description)

The core feature for Release 2 is the **Interactive Timeline**:

> *"The transcribed data will be analyzed in the backend to identify significant events. These will be assigned timestamps and short titles and displayed on an interactive timeline in the frontend."*

This breaks down into:

| # | Sub-task | Layer | Description |
|---|----------|-------|-------------|
| 1 | **Event Extraction from Transcriptions** | Backend/LLM | Analyze transcribed text to identify significant events (battles, discoveries, NPC encounters, etc.) |
| 2 | **Timestamp Assignment** | Backend | Assign timestamps (or relative time markers) to each extracted event |
| 3 | **Short Title Generation** | Backend/LLM | Generate concise titles/summaries for each event |
| 4 | **Event Storage & API** | Backend | Store events and expose them via REST API endpoints |
| 5 | **Interactive Timeline UI** | Frontend | Build a visual, interactive timeline component to display events |
| 6 | **Timeline ↔ Transcription Linking** | Full-stack | Allow clicking a timeline event to navigate to the relevant transcription |

---

## What's Already Done ✅

### 1. Entity Extraction Foundation (Release 1 — Prototype)
The current branch `Prototype-Entity-Extraction` has substantial work on **temporal and location entity extraction**:

- [entity_extractor.py](file:///home/kunj/dungeonmaind/backend/app/functions/embedding/entity_extractor.py) — **~1,050 lines** of mature extraction logic
  - ✅ Rule-based temporal entity extraction (dates, relative times, clock times, weekdays, etc.)
  - ✅ Rule-based location entity extraction (place names, fantasy locations, preposition-based, known gazetteer)
  - ✅ Hybrid mode combining rule-based + LLM-based extraction
  - ✅ Extracted entities are stored as ChromaDB metadata during embedding (see [embedding_model.py:109-118](file:///home/kunj/dungeonmaind/backend/app/functions/embedding/embedding_model.py#L109-L118))
  - ✅ LLM router already passes temporal/location entities to context for Q&A (see [llm.py:66-73](file:///home/kunj/dungeonmaind/backend/app/api/routers/llm.py#L66-L73))

- [test_entity_extractor.py](file:///home/kunj/dungeonmaind/backend/tests/test_entity_extractor.py) — **238 lines** of comprehensive unit tests
  - ✅ 4 detailed D&D scenario test cases
  - ✅ Tests for hybrid extraction, LLM fallback sanitization

### 2. Existing Infrastructure That Timeline Can Build On
- ✅ Audio recording, transcription (WhisperX), and embedding pipeline fully operational
- ✅ ChromaDB vector store with transcription + entity metadata
- ✅ LLM integration (Ollama) for intelligent text analysis
- ✅ WebSocket infrastructure (`PresenceBus`) for real-time updates
- ✅ Vue.js frontend with router, views, stores (Pinia)
- ✅ Docker support and deployment scripts

---

## What's Pending ❌

### Backend — Event Processing & API

| # | Task | Status | Effort | Notes |
|---|------|--------|--------|-------|
| 1 | **Event/Significant-Moment extraction** | ❌ Not started | Medium | Entity extraction exists, but no logic to identify *events* (e.g., "Party defeated the dragon at Dragon Hill"). Need LLM-based event identification from transcriptions |
| 2 | **Event data model** | ❌ Not started | Small | No `TimelineEvent` model exists. Need: `id`, `title`, `description`, `timestamp/order`, `session_id`, `linked_transcription_chunk`, `temporal_entities`, `location_entities` |
| 3 | **Event storage** | ❌ Not started | Small | No persistence for timeline events (neither in-memory store nor database) |
| 4 | **Timeline API endpoints** | ❌ Not started | Medium | No router for timeline. Need: `GET /timeline/events` (list), `GET /timeline/events/{id}`, `POST /timeline/generate` (trigger extraction), possibly filter/search endpoints |
| 5 | **Event title generation** | ❌ Not started | Small-Medium | Use LLM to generate concise titles for events. The LLM infrastructure exists but this specific prompting/logic is missing |
| 6 | **Link events to transcription chunks** | ❌ Not started | Medium | Associate each event with the specific transcription segment it came from |

### Frontend — Timeline UI

| # | Task | Status | Effort | Notes |
|---|------|--------|--------|-------|
| 7 | **Timeline View/Component** | ❌ Not started | Large | No `TimelineView.vue` or timeline component exists. No route `/timeline`. Need an interactive, visual timeline (time axis, event cards, scrollable) |
| 8 | **Timeline Route** | ❌ Not started | Small | Need to add `/timeline` route to [router/index.ts](file:///home/kunj/dungeonmaind/frontend/src/router/index.ts) |
| 9 | **Timeline API integration** | ❌ Not started | Small | No `timelineAPI.ts` in [frontend/src/api/](file:///home/kunj/dungeonmaind/frontend/src/api) |
| 10 | **Timeline Store** | ❌ Not started | Small | No Pinia store for timeline state |
| 11 | **Event detail view / transcription link** | ❌ Not started | Medium | Click an event → see related transcription text |
| 12 | **Responsive / interactive design** | ❌ Not started | Medium | Scrollable, zoomable, or filterable timeline with animations |

### Documentation (Required per Release Structure)

| # | Task | Status | Notes |
|---|------|--------|-------|
| 13 | **UI Mockups** | ❓ Unknown | Required before implementation ("mockups of the new features and UI should be created first") |
| 14 | **User Stories / Feature List** | ❓ Unknown | Required ("a list of individual functions required to implement the features") |
| 15 | **Sprint Meeting Docs** | ❓ Unknown | Weekly meeting notes required |
| 16 | **API Documentation** | ❌ Not started | New timeline API needs docs |
| 17 | **README update** | ❌ Not started | Timeline feature not mentioned in README |

---

## Summary

```
┌─────────────────────────────────────────────┐
│           RELEASE 2 PROGRESS                │
├─────────────────────────────────────────────┤
│                                             │
│  Foundation / Infrastructure    ██████████  │  100% — transcription, embedding, LLM, entity extraction
│  Event Extraction Logic         ░░░░░░░░░░  │    0% — extracting EVENTS (not just entities)
│  Event Data Model + Storage     ░░░░░░░░░░  │    0%
│  Timeline API Endpoints         ░░░░░░░░░░  │    0%
│  Timeline Frontend UI           ░░░░░░░░░░  │    0%
│  Integration & Linking          ░░░░░░░░░░  │    0%
│  Documentation                  ░░░░░░░░░░  │    0%
│                                             │
│  Overall Release 2:             ██░░░░░░░░  │  ~15-20%
│                                             │
│  ⏰ Time remaining: ~24 days               │
└─────────────────────────────────────────────┘
```

> [!IMPORTANT]
> The entity extraction prototype (Release 1 deliverable) provides a solid foundation — temporal and location entities are already being extracted and stored. However, the core Release 2 feature (**Interactive Timeline**) has essentially **zero implementation** yet. The entity extractor identifies *when* and *where* things are mentioned, but does **not** identify *what happened* (events). The entire timeline pipeline — from event extraction, through the API, to the interactive frontend — still needs to be built.

> [!WARNING]
> With ~24 days remaining until the July 31 deadline, the following items are **critical path**:
> 1. Define the `TimelineEvent` data model
> 2. Build LLM-based event extraction from transcriptions
> 3. Create timeline API endpoints
> 4. Build the timeline frontend component
> 5. Documentation artifacts (mockups, user stories, sprint notes)
