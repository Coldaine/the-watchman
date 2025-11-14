# TheWatchman: Prioritized Action Plan

**Date:** 2025-11-14
**Based on:** WATCHMAN_VS_MIRIX_ANALYSIS.md evaluation

---

## Executive Summary

**Critical Path:** Complete Phase 2 (`/ask` API) before anything else.

**Timeline:**
- **Weeks 1-2:** Phase 2 `/ask` implementation (CRITICAL)
- **Weeks 3-4:** Visual Timeline smart features (MIRIX-inspired)
- **Weeks 5-6:** File Ingest domain completion
- **Weeks 7-10:** MCP Registry + GUI Collector
- **Months 3-4:** Distributed architecture + System management

---

## Phase 2: `/ask` API Implementation

**Priority: CRITICAL**
**Duration: 2-4 weeks**
**Blocks: All other work**

### Why This is Critical

From the analysis:
> "The `/ask` API is the most critical component of the system, serving as the bridge between the raw knowledge graph and the user. If this natural language interface is not powerful and intuitive, the entire system risks becoming a write-only database."

**Current State:** Stub only
```python
return AskResponse(
    answer=f"Query '{request.query}' received. Full implementation coming in Phase 2.",
    ...
)
```

### Implementation Tasks

#### Task 1: Intent Classification (Week 1, Days 1-2)

**File:** `domains/agent_interface/intent_classifier.py`

```python
class IntentClassifier:
    """Classify user query intent."""

    INTENT_PATTERNS = {
        'locate': [
            r'where is',
            r'find (the )?path',
            r'locate',
            r'which (file|directory|folder)',
        ],
        'changed': [
            r'what changed',
            r'recent changes',
            r'modified (in|since)',
            r'updates? (in|to)',
        ],
        'find_text': [
            r'find (ocr|text|screenshot)',
            r'saw (on|about)',
            r'screen (showed|had)',
        ],
        'status': [
            r'(which|what) .* (running|up|down)',
            r'status of',
            r'list .* (containers|mcps|services)',
        ]
    }

    def classify(self, query: str) -> tuple[str, float]:
        """
        Classify query intent using pattern matching.

        Returns:
            Tuple of (intent, confidence)
        """
        query_lower = query.lower()
        scores = {}

        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    scores[intent] = scores.get(intent, 0) + 1

        if not scores:
            return 'unknown', 0.0

        best_intent = max(scores, key=scores.get)
        confidence = scores[best_intent] / len(self.INTENT_PATTERNS[best_intent])

        return best_intent, confidence
```

**Tests:**
```python
def test_intent_classification():
    classifier = IntentClassifier()

    assert classifier.classify("Where is my docker-compose.yml?")[0] == "locate"
    assert classifier.classify("What changed in /etc today?")[0] == "changed"
    assert classifier.classify("Find OCR text about TLS")[0] == "find_text"
    assert classifier.classify("Which containers are running?")[0] == "status"
```

#### Task 2: Query Builder (Week 1, Days 3-4)

**File:** `domains/agent_interface/query_builder.py`

```python
class QueryBuilder:
    """Build Cypher queries from intent + parameters."""

    def build_locate_query(self, search_term: str) -> str:
        """Build query to locate files/projects."""
        return f"""
        // Search files
        MATCH (f:File)
        WHERE f.path CONTAINS $search_term
        RETURN 'File' as type, f.path as path, null as details
        LIMIT 10

        UNION

        // Search projects
        MATCH (p:Project)
        WHERE p.name CONTAINS $search_term OR p.path CONTAINS $search_term
        RETURN 'Project' as type, p.path as path, p.name as details
        LIMIT 10

        UNION

        // Search directories
        MATCH (d:Directory)
        WHERE d.path CONTAINS $search_term
        RETURN 'Directory' as type, d.path as path, null as details
        LIMIT 10
        """

    def build_changed_query(self, path: str, since: datetime) -> str:
        """Build query for change timeline."""
        return f"""
        MATCH (e:Event)
        WHERE e.ts >= datetime($since)
          AND (e.path STARTS WITH $path OR $path IS NULL)
        OPTIONAL MATCH (e)-[:ACTED_ON]->(entity)
        RETURN e.ts as timestamp,
               e.type as event_type,
               e.path as path,
               labels(entity) as entity_types
        ORDER BY e.ts DESC
        LIMIT 50
        """

    def build_find_text_query(self, search_text: str, since: datetime = None) -> str:
        """Build vector search query for OCR."""
        return f"""
        // Full-text search on OCR chunks
        CALL db.index.fulltext.queryNodes('chunk_text', $search_text)
        YIELD node as chunk, score as textScore

        // Get related snapshot
        MATCH (chunk)<-[:HAS_OCR]-(s:Snapshot)
        WHERE $since IS NULL OR s.ts >= datetime($since)

        RETURN s.id as snapshot_id,
               s.ts as timestamp,
               s.app as app,
               s.window as window,
               s.path as screenshot_path,
               chunk.text as ocr_text,
               textScore
        ORDER BY textScore DESC, s.ts DESC
        LIMIT 20
        """

    def build_status_query(self, resource_type: str) -> str:
        """Build query for status checks."""
        queries = {
            'containers': """
                MATCH (c:Container)
                OPTIONAL MATCH (c)-[:EXPOSES]->(port:NetworkEndpoint)
                RETURN c.name as name,
                       c.state as state,
                       c.image as image,
                       collect(port.host + ':' + port.port) as ports
                ORDER BY c.name
            """,
            'mcps': """
                MATCH (m:MCPServer)
                OPTIONAL MATCH (m)-[:PROVIDES_TOOL]->(t:Tool)
                RETURN m.name as name,
                       m.status as status,
                       m.url as url,
                       count(t) as tool_count
                ORDER BY m.name
            """,
            'services': """
                MATCH (s:Service)
                RETURN s.name as name,
                       s.state as state,
                       s.type as type
                ORDER BY s.name
            """
        }
        return queries.get(resource_type, queries['containers'])
```

#### Task 3: LLM Integration (Week 1, Days 5-7)

**File:** `domains/agent_interface/llm_client.py`

```python
import httpx
from typing import Optional

class LLMClient:
    """LLM client with Ollama primary + OpenRouter fallback."""

    def __init__(self):
        self.ollama_url = "http://192.168.1.69:11434"
        self.openrouter_url = "https://openrouter.ai/api/v1"
        self.openrouter_key = self._load_openrouter_key()

    def _load_openrouter_key(self) -> Optional[str]:
        """Load OpenRouter API key from ~/.secrets."""
        try:
            with open(Path.home() / ".secrets" / "openrouter.key") as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.warning("OpenRouter key not found, fallback unavailable")
            return None

    async def generate(self, prompt: str, context: str = None) -> str:
        """Generate response using Ollama (with OpenRouter fallback)."""

        # Try Ollama first
        try:
            return await self._generate_ollama(prompt, context)
        except Exception as e:
            logger.warning(f"Ollama failed: {e}, trying OpenRouter")

        # Fallback to OpenRouter
        if self.openrouter_key:
            try:
                return await self._generate_openrouter(prompt, context)
            except Exception as e:
                logger.error(f"OpenRouter failed: {e}")

        raise Exception("Both Ollama and OpenRouter failed")

    async def _generate_ollama(self, prompt: str, context: str) -> str:
        """Generate using Ollama."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "llama2",
                    "prompt": self._format_prompt(prompt, context),
                    "stream": False
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()['response']

    async def _generate_openrouter(self, prompt: str, context: str) -> str:
        """Generate using OpenRouter."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.openrouter_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "anthropic/claude-3-haiku",
                    "messages": [{
                        "role": "user",
                        "content": self._format_prompt(prompt, context)
                    }]
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']

    def _format_prompt(self, query: str, context: str) -> str:
        """Format prompt with context."""
        return f"""You are The Watchman, a system knowledge assistant.

User query: {query}

System context:
{context}

Provide a concise, accurate answer based on the context. Include specific paths, timestamps, and entity references when available.
"""
```

#### Task 4: Response Formatter (Week 2, Days 1-2)

**File:** `domains/agent_interface/response_formatter.py`

```python
class ResponseFormatter:
    """Format query responses for user consumption."""

    def format_response(
        self,
        query: str,
        query_type: str,
        cypher_query: str,
        results: List[Dict],
        llm_answer: str
    ) -> AskResponse:
        """Format complete response."""

        sources = self._extract_sources(results, query_type)

        return AskResponse(
            answer=llm_answer,
            sources=sources,
            query_type=query_type,
            cypher_query=cypher_query if len(cypher_query) < 500 else None
        )

    def _extract_sources(self, results: List[Dict], query_type: str) -> List[Source]:
        """Extract source references from results."""
        sources = []

        for result in results:
            source_type = result.get('type', query_type)
            path = result.get('path')
            timestamp = result.get('timestamp')
            entity_id = result.get('id') or result.get('snapshot_id')

            sources.append(Source(
                type=source_type,
                path=path,
                timestamp=timestamp.isoformat() if timestamp else None,
                entity_id=entity_id
            ))

        return sources
```

#### Task 5: Main `/ask` Endpoint (Week 2, Days 3-5)

**File:** `app/api/ask.py` (replace stub)

```python
from domains.agent_interface.intent_classifier import IntentClassifier
from domains.agent_interface.query_builder import QueryBuilder
from domains.agent_interface.llm_client import LLMClient
from domains.agent_interface.response_formatter import ResponseFormatter

# Initialize components
intent_classifier = IntentClassifier()
query_builder = QueryBuilder()
llm_client = LLMClient()
response_formatter = ResponseFormatter()

@router.post("/", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """
    Ask a natural language question.

    Full implementation with:
    1. Intent classification
    2. Query building
    3. Neo4j execution
    4. LLM answer generation
    5. Response formatting
    """
    logger.info(f"Received question: {request.query}")

    try:
        # Step 1: Classify intent
        intent, confidence = intent_classifier.classify(request.query)
        logger.info(f"Intent: {intent} (confidence: {confidence:.2f})")

        # Step 2: Extract parameters
        params = extract_parameters(request.query, intent)

        # Step 3: Build query
        if intent == 'locate':
            cypher = query_builder.build_locate_query(params['search_term'])
        elif intent == 'changed':
            cypher = query_builder.build_changed_query(params.get('path'), params.get('since'))
        elif intent == 'find_text':
            cypher = query_builder.build_find_text_query(params['search_text'], params.get('since'))
        elif intent == 'status':
            cypher = query_builder.build_status_query(params.get('resource_type', 'containers'))
        else:
            raise ValueError(f"Unknown intent: {intent}")

        # Step 4: Execute query
        neo4j = get_neo4j_client()
        results = neo4j.execute_read(cypher, params)

        logger.info(f"Query returned {len(results)} results")

        # Step 5: Generate LLM answer
        context = format_results_for_llm(results)
        answer = await llm_client.generate(request.query, context)

        # Step 6: Format response
        response = response_formatter.format_response(
            query=request.query,
            query_type=intent,
            cypher_query=cypher,
            results=results,
            llm_answer=answer
        )

        return response

    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def extract_parameters(query: str, intent: str) -> Dict[str, Any]:
    """Extract parameters from query based on intent."""
    params = {}

    if intent == 'locate':
        # Extract search term
        match = re.search(r'(?:where is|find|locate)\s+(?:my\s+)?(.+?)(?:\?|$)', query, re.I)
        params['search_term'] = match.group(1).strip() if match else query

    elif intent == 'changed':
        # Extract path
        path_match = re.search(r'in\s+(/[^\s?]+)', query)
        params['path'] = path_match.group(1) if path_match else None

        # Extract time
        time_match = re.search(r'since\s+(\d+:\d+|\d+\s*(?:am|pm))', query, re.I)
        if time_match:
            params['since'] = parse_time(time_match.group(1))
        else:
            # Default to today
            params['since'] = datetime.now().replace(hour=0, minute=0, second=0)

    elif intent == 'find_text':
        # Extract search text
        match = re.search(r'(?:about|for|containing)\s+(.+?)(?:\?|$)', query, re.I)
        params['search_text'] = match.group(1).strip() if match else query

        # Extract time
        time_match = re.search(r'(?:from|since)\s+(this\s+morning|today|yesterday)', query, re.I)
        if time_match:
            params['since'] = parse_relative_time(time_match.group(1))

    elif intent == 'status':
        # Extract resource type
        if 'mcp' in query.lower():
            params['resource_type'] = 'mcps'
        elif 'service' in query.lower():
            params['resource_type'] = 'services'
        else:
            params['resource_type'] = 'containers'

    return params


def format_results_for_llm(results: List[Dict]) -> str:
    """Format query results as context for LLM."""
    if not results:
        return "No results found."

    context_lines = []
    for i, result in enumerate(results[:10], 1):  # Limit to top 10
        context_lines.append(f"{i}. {format_single_result(result)}")

    return "\n".join(context_lines)


def format_single_result(result: Dict) -> str:
    """Format single result for LLM context."""
    parts = []

    if 'type' in result:
        parts.append(f"Type: {result['type']}")
    if 'path' in result:
        parts.append(f"Path: {result['path']}")
    if 'name' in result:
        parts.append(f"Name: {result['name']}")
    if 'state' in result:
        parts.append(f"State: {result['state']}")
    if 'timestamp' in result:
        parts.append(f"Time: {result['timestamp']}")

    return " | ".join(parts)
```

### Testing Phase 2

**File:** `tests/integration/test_ask_api.py`

```python
import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_ask_locate():
    """Test locate intent."""
    response = client.post("/ask/", json={
        "query": "Where is my docker-compose.yml for the dashboard?"
    })
    assert response.status_code == 200
    data = response.json()
    assert data['query_type'] == 'locate'
    assert len(data['sources']) > 0
    assert 'docker-compose.yml' in data['answer'].lower()

def test_ask_changed():
    """Test changed intent."""
    response = client.post("/ask/", json={
        "query": "What changed in /etc since 10:00?"
    })
    assert response.status_code == 200
    data = response.json()
    assert data['query_type'] == 'changed'
    # Should have event sources
    assert any(s['type'] == 'Event' for s in data['sources'])

def test_ask_find_text():
    """Test find_text intent."""
    response = client.post("/ask/", json={
        "query": "Find OCR text about TLS certificates from this morning"
    })
    assert response.status_code == 200
    data = response.json()
    assert data['query_type'] == 'find_text'
    # Should have snapshot sources
    assert any(s['type'] == 'Snapshot' for s in data['sources'])

def test_ask_status():
    """Test status intent."""
    response = client.post("/ask/", json={
        "query": "Which MCP servers are running?"
    })
    assert response.status_code == 200
    data = response.json()
    assert data['query_type'] == 'status'
    # Should mention server status
    assert 'mcp' in data['answer'].lower() or 'server' in data['answer'].lower()
```

### Acceptance Criteria

- [ ] All 4 intent types classify correctly
- [ ] Cypher queries execute without errors
- [ ] LLM generates coherent answers
- [ ] Sources include paths, timestamps, entity IDs
- [ ] Integration tests pass
- [ ] Manual testing with real queries works

**Documentation:** Update `README.md` with working query examples.

---

## Visual Timeline: Smart Features

**Priority: HIGH**
**Duration: 2-3 weeks**
**Dependencies: None (can start immediately)**

### MIRIX-Inspired Optimizations

#### Task 1: Screenshot Diffing (Week 3, Days 1-3)

**File:** `domains/visual_timeline/smart_capture.py`

```python
import imagehash
from PIL import Image
from pathlib import Path

class SmartScreenshotCapture:
    """Smart screenshot capture with diffing and batching."""

    def __init__(self):
        self.settings = get_settings()
        self.frame_buffer = []
        self.last_hash = None
        self.batch_size = 20  # Process after 20 unique frames

    def compute_hash(self, image_path: Path) -> str:
        """Compute perceptual hash of image."""
        img = Image.open(image_path)
        return str(imagehash.dhash(img))

    def is_similar(self, hash1: str, hash2: str, threshold: int = 5) -> bool:
        """Check if two hashes are similar (Hamming distance)."""
        if not hash1 or not hash2:
            return False

        h1 = imagehash.hex_to_hash(hash1)
        h2 = imagehash.hex_to_hash(hash2)

        return (h1 - h2) <= threshold

    def should_capture(self, current_hash: str) -> bool:
        """Determine if screenshot should be kept."""
        if not self.last_hash:
            return True

        # Check if different enough from last
        diff_threshold = self.settings.screenshot_diff_threshold
        hamming_distance = imagehash.hex_to_hash(current_hash) - imagehash.hex_to_hash(self.last_hash)

        return hamming_distance > diff_threshold

    def add_to_buffer(self, filepath: str, hash_val: str):
        """Add screenshot to buffer for batch processing."""
        self.frame_buffer.append({
            'path': filepath,
            'hash': hash_val,
            'timestamp': datetime.now(timezone.utc)
        })

        self.last_hash = hash_val

        # Trigger batch processing if buffer full
        if len(self.frame_buffer) >= self.batch_size:
            self.process_batch()

    def process_batch(self):
        """Process accumulated screenshots in batch."""
        logger.info(f"Processing batch of {len(self.frame_buffer)} screenshots")

        # Run OCR on all frames in parallel
        from domains.visual_timeline.ocr import OCRProcessor
        ocr = OCRProcessor()

        for frame in self.frame_buffer:
            try:
                ocr.process_image(frame['path'])
            except Exception as e:
                logger.error(f"OCR failed for {frame['path']}: {e}")

        # Clear buffer
        self.frame_buffer = []
        logger.success("Batch processing complete")
```

#### Task 2: Smart Capture Triggers (Week 3, Days 4-5)

**File:** `domains/visual_timeline/triggers.py`

```python
class CaptureTriggersManager:
    """Manage smart screenshot triggers."""

    def __init__(self):
        self.last_app = None
        self.last_activity = datetime.now()
        self.idle_threshold = 300  # 5 minutes

    def check_app_switch(self, current_app: str) -> bool:
        """Check if app has switched."""
        if current_app != self.last_app:
            logger.info(f"App switch detected: {self.last_app} → {current_app}")
            self.last_app = current_app
            return True
        return False

    def check_idle_return(self) -> bool:
        """Check if user returned from idle."""
        # Get idle time from X11
        try:
            result = subprocess.run(
                ["xprintidle"],
                capture_output=True,
                text=True,
                timeout=1
            )
            idle_ms = int(result.stdout.strip())
            idle_sec = idle_ms / 1000

            # Was idle, now active
            was_idle = (datetime.now() - self.last_activity).total_seconds() > self.idle_threshold

            if was_idle and idle_sec < 10:
                logger.info("User returned from idle")
                self.last_activity = datetime.now()
                return True

            if idle_sec >= self.idle_threshold:
                self.last_activity = datetime.now()

        except Exception as e:
            logger.debug(f"Idle check failed: {e}")

        return False
```

#### Task 3: Lazy OCR Processing (Week 4, Days 1-2)

**File:** `domains/visual_timeline/lazy_ocr.py`

```python
class LazyOCRProcessor:
    """On-demand OCR processing."""

    def mark_for_lazy_processing(self, snapshot_id: str):
        """Mark snapshot for lazy OCR."""
        query = """
        MATCH (s:Snapshot {id: $snapshot_id})
        SET s.ocr_processed = false,
            s.ocr_queued = datetime()
        """
        self.neo4j.execute_write(query, {"snapshot_id": snapshot_id})

    def process_on_query(self, snapshot_id: str) -> List[str]:
        """Process OCR when snapshot is queried."""
        # Check if already processed
        query = """
        MATCH (s:Snapshot {id: $snapshot_id})
        OPTIONAL MATCH (s)-[:HAS_OCR]->(c:Chunk)
        RETURN s.ocr_processed as processed, collect(c.text) as texts
        """
        result = self.neo4j.execute_read(query, {"snapshot_id": snapshot_id})

        if result[0]['processed']:
            return result[0]['texts']

        # Process now
        logger.info(f"Lazy processing OCR for snapshot {snapshot_id}")
        snapshot = self.get_snapshot(snapshot_id)

        from domains.visual_timeline.ocr import OCRProcessor
        ocr = OCRProcessor()
        texts = ocr.process_image(snapshot['path'])

        # Mark as processed
        update_query = """
        MATCH (s:Snapshot {id: $snapshot_id})
        SET s.ocr_processed = true,
            s.ocr_processed_at = datetime()
        """
        self.neo4j.execute_write(update_query, {"snapshot_id": snapshot_id})

        return texts
```

### Acceptance Criteria

- [ ] Screenshot diffing reduces storage by 50%+
- [ ] App switch triggers working
- [ ] Idle return triggers working
- [ ] Batch processing (20 frames) operational
- [ ] Lazy OCR processes on-demand

---

## File Ingest Domain

**Priority: MEDIUM**
**Duration: 2-3 weeks**
**Dependencies: None (architecture already documented)**

### Implementation (already fully spec'd in docs)

See `docs/domains/file_ingest_implementation.md` for complete specifications.

**Tasks:**
1. Media deduplication collector (Week 5, Days 1-3)
2. Document ingestion collector (Week 5, Days 4-5)
3. Export processing collector (Week 6, Days 1-3)
4. Integration testing (Week 6, Days 4-5)

---

## Timeline Summary

| Week | Focus | Deliverables |
|------|-------|-------------|
| 1 | `/ask` API - Intent + Query Building | Intent classifier, Query builder, Tests |
| 2 | `/ask` API - LLM + Integration | LLM client, Response formatter, Full endpoint |
| 3 | Smart Capture - Diffing + Triggers | Screenshot diffing, App switch, Idle detection |
| 4 | Smart Capture - Lazy OCR | On-demand processing, Batch optimization |
| 5 | File Ingest - Media + Docs | Deduplication, Document routing |
| 6 | File Ingest - Exports + Testing | Export processing, Integration tests |
| 7-8 | MCP Registry | Server lifecycle, Docker control, Health checks |
| 9-10 | GUI Collector | AT-SPI integration, Event normalization |

---

## Success Metrics

### Phase 2 Complete (End of Week 2)
```bash
# All these must work:
curl -X POST http://localhost:8000/ask -d '{"query": "Where is docker-compose.yml?"}'
curl -X POST http://localhost:8000/ask -d '{"query": "What changed in /etc since 10:00?"}'
curl -X POST http://localhost:8000/ask -d '{"query": "Find OCR about TLS from this morning"}'
curl -X POST http://localhost:8000/ask -d '{"query": "Which MCP servers are running?"}'
```

### Smart Capture Working (End of Week 4)
- Screenshot storage reduced by 50%+
- App switch and idle triggers functional
- Batch processing operational
- Lazy OCR working

### File Ingest Operational (End of Week 6)
- Media files deduplicated and routed
- Documents auto-ingested to RAG
- Exports extracted and categorized
- Graph nodes created for all

---

## Next Steps

**Immediate (Today):**
1. Create `domains/agent_interface/` directory
2. Start implementing intent classifier
3. Write tests for intent classification

**This Week:**
- Complete intent classification + query building
- Start LLM integration
- Begin testing with real queries

**Next 2 Weeks:**
- Finish `/ask` API implementation
- Complete all Phase 2 acceptance criteria
- Update documentation with working examples

---

## Notes

**Don't get distracted:**
- ❌ Don't work on MCP Registry before `/ask` works
- ❌ Don't implement distributed architecture before Phase 2
- ❌ Don't build GUI before CLI queries work

**Stay focused on value delivery:**
The `/ask` API is what makes all the data capture useful. Without it, TheWatchman is just collecting data with no way to retrieve it effectively.
