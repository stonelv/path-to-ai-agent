import pytest

from tool_agent.tools import InvalidArguments, ToolDenied


def test_allowed_identifier(authorize_read):
    assert authorize_read({"doc_id": "deploy-guide"}, frozenset({"deploy-guide"})) == "deploy-guide"


def test_forbidden_identifier(authorize_read):
    with pytest.raises(ToolDenied):
        authorize_read({"doc_id": "private-release"}, frozenset({"deploy-guide"}))


@pytest.mark.parametrize(
    "arguments",
    [
        {"doc_id": "../secret"},
        {"doc_id": True},
        {"doc_id": "deploy-guide", "path": "."},
        {},
    ],
    ids=["path", "boolean", "extra-field", "missing-field"],
)
def test_invalid_arguments(arguments, authorize_read):
    with pytest.raises(InvalidArguments):
        authorize_read(arguments, frozenset({"deploy-guide"}))
