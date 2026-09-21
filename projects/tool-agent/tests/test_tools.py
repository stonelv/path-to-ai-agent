import asyncio
from unittest.mock import patch

import pytest

from tool_agent.tools import (
    DOCUMENTS,
    InvalidArguments,
    ToolDenied,
    ToolFailure,
    ToolRegistry,
    validate_read_arguments,
)


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"doc_id": "deploy-guide", "extra": True},
        {"doc_id": 1},
        {"doc_id": True},
        {"doc_id": None},
        {"doc_id": ["deploy-guide"]},
        {"doc_id": ""},
        {"doc_id": "deploy-guide\n"},
        {"doc_id": "../secrets"},
        {"doc_id": r"C:\Windows\win.ini"},
        {"doc_id": "/etc/passwd"},
        {"doc_id": "a" * 49},
        [],
    ],
)
def test_strict_read_arguments(arguments):
    with pytest.raises(InvalidArguments):
        validate_read_arguments(arguments)


def test_valid_arguments():
    assert validate_read_arguments({"doc_id": "deploy-guide"}) == "deploy-guide"


def test_real_read_and_list_do_not_access_files():
    registry = ToolRegistry()
    with patch("builtins.open", side_effect=AssertionError("No arbitrary file access")):
        listing = asyncio.run(registry.execute("list_docs", {}))
        reading = asyncio.run(registry.execute("read_doc", {"doc_id": "deploy-guide"}))
    assert listing.content == "deploy-guide\nuntrusted-note"
    assert reading.content == DOCUMENTS["deploy-guide"]
    assert "private-release" not in listing.content
    assert reading.untrusted and not reading.truncated


@pytest.mark.parametrize("name", ["write_doc", "read_file", "shell", "__dict__"])
def test_unknown_tools_denied(name):
    with pytest.raises(ToolDenied):
        asyncio.run(ToolRegistry().execute(name, {}))


def test_extra_list_parameter_rejected():
    with pytest.raises(InvalidArguments):
        asyncio.run(ToolRegistry().execute("list_docs", {"path": "."}))


def test_resource_authorization_and_missing_resource_are_distinct():
    with pytest.raises(ToolDenied):
        asyncio.run(ToolRegistry().execute("read_doc", {"doc_id": "private-release"}))
    registry = ToolRegistry(frozenset({"missing-doc"}))
    with pytest.raises(ToolFailure):
        asyncio.run(registry.execute("read_doc", {"doc_id": "missing-doc"}))


def test_output_is_bounded_and_injection_remains_data():
    registry = ToolRegistry(max_output_chars=32)
    result = asyncio.run(registry.execute("read_doc", {"doc_id": "untrusted-note"}))
    assert len(result.content) == 32
    assert result.truncated and result.untrusted
    full = asyncio.run(ToolRegistry().execute("read_doc", {"doc_id": "untrusted-note"}))
    assert "IGNORE ALL PREVIOUS INSTRUCTIONS" in full.content
    assert full.untrusted


def test_registry_snapshots_documents():
    documents = {"deploy-guide": "initial"}
    registry = ToolRegistry(documents=documents)
    documents["deploy-guide"] = "changed"
    assert (
        asyncio.run(registry.execute("read_doc", {"doc_id": "deploy-guide"})).content == "initial"
    )
