"""Security and isolation tests for LangGraph memory tools.

Guarantees:
1. Zero member_id exposure in tool schemas (IDOR prevention).
2. Fail-closed behavior when member_id is None / guest.
3. Concurrency isolation across concurrent async tasks (ContextVar protection).
4. Strict tool partitioning between Librarian and Debate modes.
"""

import asyncio

import pytest
from langchain_core.utils.function_calling import convert_to_openai_tool

from app.core.context import current_member_id
from app.domain.graph.tools import DEBATE_TOOLS, GENERIC_TOOLS, LIBRARIAN_TOOLS
from app.domain.memory.debate_memory_tool import search_debate_memory
from app.domain.memory.my_library_tool import search_my_library
from app.domain.memory.rag_tool import search_scrap_memory

ALL_TOOLS = list({t.name: t for t in (LIBRARIAN_TOOLS + DEBATE_TOOLS + GENERIC_TOOLS)}.values())


@pytest.mark.parametrize("tool_instance", ALL_TOOLS)
def test_tool_schemas_strictly_exclude_member_id(tool_instance):
    """Verify tool args, args_schema, and OpenAI JSON schema strictly have NO member_id parameter.

    This prevents the LLM from ever seeing, generating, or manipulating member_id (IDOR mitigation).
    """
    # 1. Inspect tool.args dictionary
    args = tool_instance.args
    assert "member_id" not in args, f"Tool '{tool_instance.name}' exposes member_id in tool.args!"

    # 2. Inspect Pydantic args_schema
    if tool_instance.args_schema:
        schema = tool_instance.args_schema.model_json_schema()
        properties = schema.get("properties", {})
        assert "member_id" not in properties, (
            f"Tool '{tool_instance.name}' exposes member_id in args_schema properties!"
        )

    # 3. Inspect OpenAI function calling serialization (exact schema fed to LLM API)
    openai_tool = convert_to_openai_tool(tool_instance)
    fn_params = openai_tool.get("function", {}).get("parameters", {}).get("properties", {})
    assert "member_id" not in fn_params, (
        f"Tool '{tool_instance.name}' exposes member_id in OpenAI function schema!"
    )


@pytest.mark.asyncio
async def test_tools_fail_closed_when_member_id_is_none():
    """Verify all memory tools reject access with explicit non-retry message when unauthenticated."""
    current_member_id.set(None)

    # 1. Scrap memory
    scrap_res = await search_scrap_memory.ainvoke({"query": "행복한 삶"})
    assert "인증 정보" in scrap_res
    assert "조회할 수 없습니다" in scrap_res
    assert "다시 호출하지 마시고" in scrap_res

    # 2. Bookshelf memory
    lib_res = await search_my_library.ainvoke({})
    assert "인증 정보" in lib_res
    assert "조회할 수 없습니다" in lib_res
    assert "다시 호출하지 마시고" in lib_res

    # 3. Debate memory
    debate_res = await search_debate_memory.ainvoke({"query": "자아 실현"})
    assert "인증 정보" in debate_res
    assert "조회할 수 없습니다" in debate_res
    assert "다시 호출하지 마시고" in debate_res


@pytest.mark.asyncio
async def test_concurrent_requests_contextvar_member_id_isolation():
    """Verify concurrent async tasks strictly isolate their respective member_id ContextVars."""
    results = {}

    async def task_a():
        # Set task A's member_id and delay briefly to yield to event loop
        current_member_id.set("user-aaa-uuid")
        await asyncio.sleep(0.01)
        # Verify ContextVar remains intact
        assert current_member_id.get() == "user-aaa-uuid"
        # Invoke scrap memory tool and check logged/returned context
        res = await search_scrap_memory.ainvoke({"query": "존재하지않는내용"})
        results["task_a"] = (current_member_id.get(), res)

    async def task_b():
        # Set task B's member_id and delay briefly
        current_member_id.set("user-bbb-uuid")
        await asyncio.sleep(0.01)
        # Verify ContextVar remains intact
        assert current_member_id.get() == "user-bbb-uuid"
        res = await search_scrap_memory.ainvoke({"query": "존재하지않는내용"})
        results["task_b"] = (current_member_id.get(), res)

    # Run tasks concurrently
    await asyncio.gather(task_a(), task_b())

    assert results["task_a"][0] == "user-aaa-uuid"
    assert results["task_b"][0] == "user-bbb-uuid"
    assert "user-aaa-uuid" in results["task_a"][1] or "존재하지않는내용" in results["task_a"][1]
    assert "user-bbb-uuid" in results["task_b"][1] or "존재하지않는내용" in results["task_b"][1]


def test_tool_partitioning_between_librarian_and_debate_modes():
    """Verify strict tool partitioning: Librarian vs Debate mode tools."""
    lib_tool_names = {t.name for t in LIBRARIAN_TOOLS}
    debate_tool_names = {t.name for t in DEBATE_TOOLS}

    # 1. Debate tools must NOT contain bookshelf search or curation requests
    assert "search_my_library" not in debate_tool_names
    assert "search_recent_books" not in debate_tool_names
    assert "request_book_curation" not in debate_tool_names

    # 2. Debate tools MUST contain scrap memory and debate-specific tools
    assert "search_scrap_memory" in debate_tool_names
    assert "search_debate_memory" in debate_tool_names
    assert "trigger_debate_conclude" in debate_tool_names

    # 3. Librarian tools must NOT contain debate memory or conclude trigger
    assert "search_debate_memory" not in lib_tool_names
    assert "trigger_debate_conclude" not in lib_tool_names

    # 4. Librarian tools MUST contain reading & curation tools
    assert "search_scrap_memory" in lib_tool_names
    assert "search_my_library" in lib_tool_names
    assert "search_recent_books" in lib_tool_names
    assert "request_book_curation" in lib_tool_names


@pytest.mark.asyncio
async def test_unauthenticated_conclude_skips_debate_insight_write(monkeypatch: pytest.MonkeyPatch):
    """Verify that unauthenticated conclude requests with forged member_id NEVER trigger DB write tasks."""
    from unittest.mock import AsyncMock, patch
    from uuid import uuid4

    from httpx import ASGITransport, AsyncClient
    from langchain_core.messages import AIMessage

    from app.api import router
    from app.core.config import settings
    from app.main import app

    monkeypatch.setattr(settings, "app_env", "production")

    # Mock graph to return concluded state with summary
    async def _mock_ainvoke(initial_state, config=None):
        return {
            **initial_state,
            "messages": [
                *initial_state.get("messages", []),
                AIMessage(content="토론 마무리 총평입니다."),
            ],
            "is_concluded": True,
            "debate_summary": "위조 공격자가 삽입하려는 악의적 토론 요약입니다.",
        }

    monkeypatch.setattr(router._graph, "ainvoke", AsyncMock(side_effect=_mock_ainvoke))

    transport = ASGITransport(app=app)
    victim_id = str(uuid4())

    with patch("app.api.router.save_debate_insight_task") as mock_save_task:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/api/v1/chat",
                json={
                    "session_id": str(uuid4()),
                    "member_id": victim_id,  # Forged member_id without Authorization header
                    "message": "토론 끝내자",
                    "mode": "DEBATE",
                    "persona": "DEBATE_CRITIC",
                    "action": "conclude",
                },
            )
            assert res.status_code == 200
            # Crucial: Background DB write must NOT be scheduled for unauthenticated requests
            mock_save_task.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_token_rejected_with_401():
    """Verify that tokens with type='refresh' are strictly rejected with 401 Unauthorized."""
    from uuid import uuid4

    import jwt
    from httpx import ASGITransport, AsyncClient

    from app.core.config import settings
    from app.main import app

    payload = {
        "sub": str(uuid4()),
        "role": "member",
        "type": "refresh",  # Explicit refresh token
    }
    refresh_token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/chat",
            headers={"Authorization": f"Bearer {refresh_token}"},
            json={
                "message": "안녕",
                "mode": "LIBRARIAN",
                "persona": "CAT",
            },
        )
        assert res.status_code == 401
        assert "Refresh 토큰" in res.json().get("detail", "")


@pytest.mark.asyncio
async def test_request_body_member_id_is_strictly_ignored_when_authenticated(
    monkeypatch: pytest.MonkeyPatch,
):
    """Verify request.member_id in JSON body is completely ignored when JWT token is present."""
    from uuid import uuid4

    import jwt
    from httpx import ASGITransport, AsyncClient
    from langchain_core.messages import AIMessage

    from app.api import router
    from app.core.config import settings
    from app.core.context import current_member_id
    from app.main import app

    legit_sub = str(uuid4())
    attacker_sub = str(uuid4())

    token = jwt.encode(
        {"sub": legit_sub, "role": "member"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    observed_member_id_in_graph = None

    async def _mock_ainvoke(initial_state, config=None):
        nonlocal observed_member_id_in_graph
        observed_member_id_in_graph = current_member_id.get()
        return {
            **initial_state,
            "messages": [
                *initial_state.get("messages", []),
                AIMessage(content="답변 완료"),
            ],
        }

    monkeypatch.setattr(router._graph, "ainvoke", _mock_ainvoke)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "message": "내 서재 알려줘",
                "member_id": attacker_sub,  # Forged body member_id
                "mode": "LIBRARIAN",
                "persona": "CAT",
            },
        )
        assert res.status_code == 200
        # Critical verification: the graph/tools see ONLY the verified JWT sub, NOT the attacker ID
        assert observed_member_id_in_graph == legit_sub
        assert observed_member_id_in_graph != attacker_sub


@pytest.mark.asyncio
async def test_guest_token_maps_to_guest_member_id_and_tools_succeed(
    monkeypatch: pytest.MonkeyPatch,
):
    """Verify verified guest JWT (sub='guest-...') maps current_member_id to GUEST_MEMBER_ID."""
    import jwt

    from app.api.router import _prepare_chat_context
    from app.api.schemas import ChatRequest
    from app.core.config import settings
    from app.core.context import current_member_id

    guest_jwt = jwt.encode(
        {"sub": "guest-abc-1234", "role": "guest"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    req = ChatRequest(
        message="가이드북 봤어",
        mode="LIBRARIAN",
        persona="CAT",
    )

    (
        session_id,
        active_persona,
        mode,
        state,
        weather,
        mgr,
        user_role,
        guest_id,
    ) = await _prepare_chat_context(req, authorization=f"Bearer {guest_jwt}")

    assert user_role == "guest"
    assert guest_id == "guest-abc-1234"
    # Must map to shared GUEST_MEMBER_ID ("00000000-0000-0000-0000-000000000003")
    assert current_member_id.get() == settings.guest_member_id
    assert current_member_id.get() == "00000000-0000-0000-0000-000000000003"

    # Memory tool should NOT fail-closed when mapped to guest_member_id
    scrap_res = await search_scrap_memory.ainvoke({"query": "바인더 가이드"})
    assert "인증 정보가 없어" not in scrap_res


@pytest.mark.asyncio
async def test_guest_session_key_enforces_guest_prefix_from_jwt():
    """Verify guest session_id strictly incorporates 'guest:' prefix isolated by verified JWT sub."""
    import jwt

    from app.api.router import _prepare_chat_context
    from app.api.schemas import ChatRequest
    from app.core.config import settings

    guest_jwt = jwt.encode(
        {"sub": "guest-550e8400", "role": "guest"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    req = ChatRequest(
        message="대화 시작",
        mode="LIBRARIAN",
        persona="CAT",
    )

    (
        session_id,
        _,
        _,
        _,
        _,
        _,
        user_role,
        guest_id,
    ) = await _prepare_chat_context(req, authorization=f"Bearer {guest_jwt}")

    assert user_role == "guest"
    # Verified guest prefix and sub in session_id
    assert session_id.startswith("guest:")
    assert "550e8400" in session_id
    assert session_id.endswith(":CAT")


@pytest.mark.asyncio
async def test_guest_conclude_skips_debate_insight_save(monkeypatch: pytest.MonkeyPatch):
    """Verify that concluding debate under guest token NEVER schedules debate insight DB persistence."""
    from unittest.mock import AsyncMock, patch

    import jwt
    from httpx import ASGITransport, AsyncClient
    from langchain_core.messages import AIMessage

    from app.api import router
    from app.core.config import settings
    from app.main import app

    guest_jwt = jwt.encode(
        {"sub": "guest-test-uuid", "role": "guest"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    async def _mock_ainvoke(initial_state, config=None):
        return {
            **initial_state,
            "messages": [
                *initial_state.get("messages", []),
                AIMessage(content="토론이 종료되었습니다."),
            ],
            "is_concluded": True,
            "debate_summary": "게스트의 토론 요약입니다.",
        }

    monkeypatch.setattr(router._graph, "ainvoke", AsyncMock(side_effect=_mock_ainvoke))

    transport = ASGITransport(app=app)
    with patch("app.api.router.save_debate_insight_task") as mock_save_task:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/api/v1/chat",
                headers={"Authorization": f"Bearer {guest_jwt}"},
                json={
                    "message": "토론 끝내자",
                    "mode": "DEBATE",
                    "persona": "DEBATE_CRITIC",
                    "action": "conclude",
                },
            )
            assert res.status_code == 200
            # Must NOT save debate insight for guests
            mock_save_task.assert_not_called()
