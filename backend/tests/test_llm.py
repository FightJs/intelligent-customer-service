"""LLM client 生命周期测试。"""
from unittest.mock import AsyncMock, MagicMock, patch

import agent.llm as llm


def test_get_async_client_reuses_single_instance():
    created = MagicMock()
    original = llm._async_client
    llm._async_client = None
    try:
        with patch.object(llm, '_create_async_client', return_value=created) as factory:
            assert llm.get_async_client() is created
            assert llm.get_async_client() is created
        factory.assert_called_once_with()
    finally:
        llm._async_client = original


async def test_close_clients_is_idempotent_and_allows_recreation():
    first = MagicMock()
    first.close = AsyncMock()
    second = MagicMock()
    original = llm._async_client
    llm._async_client = None
    try:
        with patch.object(
            llm,
            '_create_async_client',
            side_effect=[first, second],
        ) as factory:
            assert llm.get_async_client() is first
            await llm.close_clients()
            await llm.close_clients()
            assert llm.get_async_client() is second

        first.close.assert_awaited_once_with()
        assert factory.call_count == 2
    finally:
        llm._async_client = original
