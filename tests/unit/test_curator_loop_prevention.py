"""Comprehensive unit tests for Curator reentry loop prevention, adversarial fake card stripping,

sentence-level delayed promise replacement, debate mode isolation, SSE token buffering,
and session reset between turns.
"""

from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.errors import GraphRecursionError

from app.domain.graph.nodes import (
    DEFAULT_EMPTY_CURATION_FALLBACK,
    _replace_delayed_curation_promise,
    _sanitize_persona_output,
    cat_node,
    debate_critic_node,
)
from app.domain.graph.workflow import route_persona_exit
from app.domain.personas import CAT_ID, DEBATE_CRITIC_ID

# ==============================================================================
# 1. Three Reentry Paths Isolation Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_reentry_path_1_pre_delegation_blocked_when_curator_attempted():
    """Path 1 (Pre-delegation): When curator_attempted is True, recommend keywords

    must NOT cause re-delegation to curator_request, preventing infinite reentry loop.
    (This permanently retains the reproduction test).
    """
    state = {
        "messages": [HumanMessage(content="책 추천해줘")],
        "member_id": "test-uuid",
        "active_persona": CAT_ID,
        "librarian_name": None,
        "mode": "LIBRARIAN",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": None,
        "curator_request": None,
        "curated_books": None,
        "curator_attempted": True,
    }

    result = await cat_node(state)
    assert "curator_request" not in result, (
        "curator_attempted=True인데도 또 curator_request가 반환되어 무한 루프가 발생했습니다!"
    )
    assert "messages" in result
    assert result["active_persona"] == CAT_ID


@pytest.mark.asyncio
async def test_reentry_path_2_tool_binding_excludes_request_book_curation():
    """Path 2 (Tool Binding): When curator_attempted is True, request_book_curation

    must be completely excluded from active tools passed to LLM to prevent
    dangling tool calls without responses.
    """
    state = {
        "messages": [HumanMessage(content="책 추천해줘")],
        "member_id": "test-uuid",
        "active_persona": CAT_ID,
        "librarian_name": None,
        "mode": "LIBRARIAN",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": None,
        "curator_request": None,
        "curated_books": None,
        "curator_attempted": True,
    }

    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(content="서재에서 어울리는 책을 찾지 못했어요.")

    with patch("app.domain.graph.nodes._get_llm", return_value=mock_llm) as mock_get_llm:
        await cat_node(state)
        # Check tools passed to _get_llm
        bound_tools = mock_get_llm.call_args[1].get("tools") or []
        tool_names = [getattr(t, "name", "") for t in bound_tools]
        assert "request_book_curation" not in tool_names, (
            "curator_attempted=True 상태에서는 request_book_curation 도구가 제외되어야 합니다!"
        )


@pytest.mark.asyncio
async def test_reentry_path_3_delayed_promise_replaced_without_re_delegation():
    """Path 3 (Delayed Promise): When LLM mock outputs an empty promise ('골라올게')

    after curator failed, it must NOT re-delegate to curator, but replace the promise sentence.
    """
    state = {
        "messages": [HumanMessage(content="책 추천해줘")],
        "member_id": "test-uuid",
        "active_persona": CAT_ID,
        "librarian_name": None,
        "mode": "LIBRARIAN",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": None,
        "curator_request": None,
        "curated_books": None,
        "curator_attempted": True,
    }

    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(
        content="독자님의 기분을 이해해요. 조금만 기다려, 내가 멋진 책을 골라올게!"
    )

    with patch("app.domain.graph.nodes._get_llm", return_value=mock_llm):
        result = await cat_node(state)
        assert "curator_request" not in result, (
            "골라올게 발화로 인해 큐레이터로 다시 튕겨나갔습니다!"
        )
        reply_msg = result["messages"][0].content
        assert "골라올게" not in reply_msg
        assert "기다려" not in reply_msg
        assert "독자님의 기분을 이해해요" in reply_msg  # Prior context preserved


# ==============================================================================
# 2. Sentence-level Delayed Promise Replacement & Korean Delimiter Tests
# ==============================================================================


def test_replace_delayed_curation_promise_with_korean_delimiters():
    """Verify sentence-level replacement preserves preceding context and handles commas,

    exclamation marks, and multiple sentences on one line.
    """
    # Case 1: Comma and exclamation
    text1 = "잠시만요, 골라올게요! 책을 읽는 건 좋은 일이에요."
    replaced1 = _replace_delayed_curation_promise(text1)
    assert "골라올게" not in replaced1
    assert "책을 읽는 건 좋은 일이에요." in replaced1
    assert "이번에는 맞는 책을 서재에서 찾지 못했어요." in replaced1

    # Case 2: Multi-line structure
    text2 = "오늘 참 힘든 하루였군요.\n내가 꼭 맞는 책을 찾아올게요!\n편히 쉬세요."
    replaced2 = _replace_delayed_curation_promise(text2)
    assert "오늘 참 힘든 하루였군요." in replaced2
    assert "찾아올게" not in replaced2
    assert "편히 쉬세요." in replaced2

    # Case 3: No promise
    text3 = "언제든 서재에 찾아와 주세요."
    assert _replace_delayed_curation_promise(text3) == text3


# ==============================================================================
# 3. Adversarial Fake Card Sanitization & Empty Response Fallback
# ==============================================================================


def test_adversarial_fake_card_stripping_and_empty_fallback():
    """Verify adversarial fake card hallucination is stripped completely,

    and if stripped output is too short, default empty fallback is returned.
    """
    # Adversarial mock output with fake heading and registration button
    adversarial_content = (
        "### 📖 존재하지 않는 가짜 책\n💡 추천 이유: 그냥 지어냈어요.\n🏷️ 장르: 문학\n등록 ➔\n"
    )

    cleaned = _sanitize_persona_output(adversarial_content, curated_books=None)
    assert "### 📖" not in cleaned
    assert "등록 ➔" not in cleaned
    assert "존재하지 않는 가짜 책" not in cleaned
    # Output was completely stripped (< 15 chars), so it should return default gentle fallback
    assert cleaned == DEFAULT_EMPTY_CURATION_FALLBACK

    # Adversarial output with legitimate thoughts + fake card
    mixed_content = (
        "오늘 하루 마음이 무거우셨군요. 조용히 사색의 시간을 가져보세요.\n\n"
        "### 📖 가짜 책\n"
        "💡 추천 이유: 가짜\n"
        "등록 ➔"
    )
    cleaned_mixed = _sanitize_persona_output(mixed_content, curated_books=None)
    assert "### 📖" not in cleaned_mixed
    assert "등록 ➔" not in cleaned_mixed
    assert "오늘 하루 마음이 무거우셨군요" in cleaned_mixed


# ==============================================================================
# 4. Debate Mode Isolation Test
# ==============================================================================


@pytest.mark.asyncio
async def test_debate_mode_unaffected_by_curator_attempted():
    """Verify debate mode does NOT activate curator_attempted logic and keeps

    trigger_debate_conclude intact.
    """
    state = {
        "messages": [HumanMessage(content="오늘 토론은 여기까지 하고 토론 마무리하자.")],
        "member_id": "test-uuid",
        "active_persona": DEBATE_CRITIC_ID,
        "librarian_name": None,
        "mode": "DEBATE",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": None,
        "curator_request": None,
        "curated_books": None,
        "curator_attempted": False,
    }

    result = await debate_critic_node(state)
    # Debate conclude intent should still successfully delegate to curator_request for finale wrap-up!
    assert result.get("is_concluded") is True
    assert "curator_request" in result


# ==============================================================================
# 5. Workflow Exit Routing Guard Test
# ==============================================================================


def test_route_persona_exit_guards_curator_reentry():
    """Verify route_persona_exit never returns 'curator_node' if curator_attempted is True."""
    state_loop = {
        "curator_request": "책 추천",
        "curated_books": None,
        "curator_attempted": True,
        "handoff_target": None,
        "messages": [AIMessage(content="대체 답변입니다.")],
    }
    next_node = route_persona_exit(state_loop)
    assert next_node != "curator_node"
    assert next_node == "__end__"


# ==============================================================================
# 6. Session Reset Between Turns Test
# ==============================================================================


@pytest.mark.asyncio
async def test_turn_reset_curator_attempted_in_prepare_chat_context():
    """Verify _prepare_chat_context resets curator_attempted to False on every new turn."""
    from app.api.router import _prepare_chat_context
    from app.api.schemas import ChatRequest

    req = ChatRequest(
        message="새로운 책 골라줘",
        session_id="test-session-1",
        persona="CAT",
    )

    (
        session_id,
        active_persona,
        mode,
        initial_state,
        weather,
        mgr,
        role,
        guest_id,
    ) = await _prepare_chat_context(req)

    assert initial_state["curator_attempted"] is False
    assert initial_state["curated_books"] is None


# ==============================================================================
# 7. SSE Streaming Token Buffering & Recursion Fallback Test
# ==============================================================================


@pytest.mark.asyncio
async def test_streaming_buffers_failed_curator_turn_and_no_fake_card_tokens():
    """Verify that in SSE streaming, when returning from curator failure, tokens are

    buffered and emitted as the clean sanitized message without leaking fake card markers.
    """
    from fastapi import BackgroundTasks

    from app.api.router import _graph, chat_stream_with_persona
    from app.api.schemas import ChatRequest

    req = ChatRequest(
        message="책 추천해줘",
        session_id="test-sse-fail-1",
        persona="CAT",
    )

    # Simulate curator_node returning 0 books, followed by persona node producing fake card
    async def mock_astream_events(initial_state, version, config):
        # 1. curator_node finishes with 0 books
        yield {
            "event": "on_chain_end",
            "name": "curator_node",
            "data": {"output": {"curated_books": []}},
        }
        # 2. cat_node streams raw tokens with fake card (which should be BUFFERED)
        yield {
            "event": "on_chat_model_stream",
            "metadata": {"langgraph_node": "cat_node"},
            "data": {"chunk": AIMessage(content="### 📖 가짜 책\n등록 ➔")},
        }
        # 3. cat_node finishes with sanitized output
        yield {
            "event": "on_chain_end",
            "name": "cat_node",
            "data": {
                "output": {
                    "active_persona": "CAT",
                    "messages": [
                        AIMessage(
                            content="독자님의 마음에 꼭 맞는 책을 이번에는 서재에서 찾아내지 못했네요. 대신 어떤 이야기를 더 나누고 싶으신가요?"
                        )
                    ],
                }
            },
        }

    with patch.object(_graph, "astream_events", side_effect=mock_astream_events):
        bg = BackgroundTasks()
        resp = await chat_stream_with_persona(req, background_tasks=bg)

        # Collect all emitted SSE events
        events = []
        async for chunk in resp.body_iterator:
            events.append(chunk if isinstance(chunk, str) else chunk.decode("utf-8"))

        full_stream = "".join(events)
        # CRITICAL ASSERTION: No fake card markdown or button ever reached the client!
        assert "### 📖" not in full_stream
        assert "등록 ➔" not in full_stream
        assert "가짜 책" not in full_stream
        # The clean fallback message was emitted
        assert "독자님의 마음에 꼭 맞는 책을 이번에는" in full_stream


@pytest.mark.asyncio
async def test_streaming_handles_midstream_graph_recursion_error():
    """Verify that if GraphRecursionError occurs mid-stream, fallback token is emitted

    and safe clean state is preserved in Redis.
    """
    from fastapi import BackgroundTasks

    from app.api.router import _graph, chat_stream_with_persona
    from app.api.schemas import ChatRequest

    req = ChatRequest(
        message="무한 루프 유발 질문",
        session_id="test-sse-recursion-1",
        persona="CAT",
    )

    async def mock_astream_events(initial_state, version, config):
        yield {
            "event": "on_chat_model_stream",
            "metadata": {"langgraph_node": "cat_node"},
            "data": {"chunk": AIMessage(content="생각 중")},
        }
        raise GraphRecursionError("Recursion limit of 25 reached")

    from app.infrastructure.redis_session import get_redis_session_manager

    session_mgr = get_redis_session_manager()
    saved_calls = []
    original_save = session_mgr.save_session

    async def mock_save(session_id, data):
        saved_calls.append((session_id, data))
        return await original_save(session_id, data)

    with (
        patch.object(_graph, "astream_events", side_effect=mock_astream_events),
        patch.object(session_mgr, "save_session", side_effect=mock_save),
    ):
        bg = BackgroundTasks()
        resp = await chat_stream_with_persona(req, background_tasks=bg)

        events = []
        async for chunk in resp.body_iterator:
            events.append(chunk if isinstance(chunk, str) else chunk.decode("utf-8"))

        full_stream = "".join(events)
        assert "도서 추천 및 답변을 정리하는 과정에서 일시적인 지연이 발생했어요" in full_stream
        assert "event: done" in full_stream

        # Verify Redis saved data: contains user's original message AND the clean fallback
        assert len(saved_calls) >= 1
        saved_session_id, saved_data = saved_calls[0]
        messages = saved_data.get("messages", [])
        assert any(
            m.get("role") == "user" and m.get("content") == "무한 루프 유발 질문" for m in messages
        ), "사용자의 원래 질문이 Redis 세션에 보존되어야 합니다!"
        assert any(
            m.get("role") == "assistant"
            and "도서 추천 및 답변을 정리하는 과정에서 일시적인 지연이 발생했어요"
            in m.get("content")
            for m in messages
        ), "Redis에 찌꺼기 대신 온전한 대체 메시지가 저장되어야 합니다!"


# ==============================================================================
# 8. Real Guest Frontend Token E2E Verification Test
# ==============================================================================


@pytest.mark.asyncio
async def test_guest_frontend_token_chat_and_stream_e2e(monkeypatch: pytest.MonkeyPatch):
    """Verify that a real guest sending sub: 'guest-{uuid}' receives 200 OK on /chat

    and /chat/stream, with user questions safely persisted in Redis and no 422 errors.
    """
    import jwt
    from httpx import ASGITransport, AsyncClient

    from app.core.config import settings
    from app.main import app

    monkeypatch.setattr(settings, "app_env", "production")

    guest_uuid = "a1b2c3d4-e5f6-4a1b-8c2d-3e4f5a6b7c8d"
    guest_sub = f"guest-{guest_uuid}"
    guest_jwt = jwt.encode(
        {"sub": guest_sub, "role": "guest"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test POST /api/v1/chat
        res_chat = await client.post(
            "/api/v1/chat",
            headers={"Authorization": f"Bearer {guest_jwt}"},
            json={
                "message": "안녕 고양이 사서님! 오늘 책 추천받을 수 있을까?",
                "persona": "CAT",
                "mode": "LIBRARIAN",
            },
        )
        assert res_chat.status_code == 200, (
            f"Expected 200 but got {res_chat.status_code}: {res_chat.text}"
        )
        data = res_chat.json()
        assert data["active_persona"] == "CAT"
        assert f"guest:{guest_uuid}:CAT" == data["session_id"]
        assert len(data["reply"]) > 0

        # 2. Test POST /api/v1/chat/stream
        res_stream = await client.post(
            "/api/v1/chat/stream",
            headers={"Authorization": f"Bearer {guest_jwt}"},
            json={
                "message": "따뜻한 차와 함께 읽을 책 알려줘",
                "persona": "CAT",
                "mode": "LIBRARIAN",
            },
        )
        assert res_stream.status_code == 200
        stream_text = res_stream.text
        assert "event: metadata" in stream_text
        assert "event: done" in stream_text
        assert "event: error" not in stream_text


@pytest.mark.asyncio
async def test_streaming_normal_turn_emits_multiple_realtime_tokens():
    """Verify that a normal successful turn does NOT buffer tokens and streams deltas in real-time.

    Guarantees that token buffering is strictly limited to curator failure recovery turns.
    """
    from fastapi import BackgroundTasks

    from app.api.router import _graph, chat_stream_with_persona
    from app.api.schemas import ChatRequest

    req = ChatRequest(
        message="오늘 기분이 좋아",
        session_id="test-normal-stream-1",
        persona="CAT",
    )

    # Simulate normal master persona streaming multiple real-time chunks
    async def mock_astream_events(initial_state, version, config):
        chunks = ["오늘 ", "기분이 ", "좋으시다니 ", "저도 ", "기쁩니다냥!"]
        for c in chunks:
            yield {
                "event": "on_chat_model_stream",
                "metadata": {"langgraph_node": "cat_node"},
                "data": {"chunk": AIMessage(content=c)},
            }
        yield {
            "event": "on_chain_end",
            "name": "cat_node",
            "data": {
                "output": {
                    "active_persona": "CAT",
                    "messages": [AIMessage(content="오늘 기분이 좋으시다니 저도 기쁩니다냥!")],
                }
            },
        }

    with patch.object(_graph, "astream_events", side_effect=mock_astream_events):
        bg = BackgroundTasks()
        resp = await chat_stream_with_persona(req, background_tasks=bg)

        token_events = []
        async for chunk in resp.body_iterator:
            text = chunk if isinstance(chunk, str) else chunk.decode("utf-8")
            if "event: token" in text:
                token_events.append(text)

        # Real-time streaming assertion: Each chunk was emitted independently as its own token event!
        assert len(token_events) == 5, (
            f"일반 턴에서는 실시간으로 분할된 5개의 토큰 이벤트가 나가야 합니다 (실제: {len(token_events)}개)"
        )
