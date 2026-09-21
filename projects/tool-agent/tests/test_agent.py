import asyncio
import json

import pytest

from tool_agent.agent import Agent, Limits
from tool_agent.contracts import ModelTurn, ProviderFailure, ToolCall
from tool_agent.demo import ScriptedProvider, read_turn
from tool_agent.tools import DOCUMENTS, ToolFailure, ToolRegistry


class SequenceProvider:
    def __init__(self, *turns):
        self.turns = iter(turns)
        self.requests = []

    async def complete(self, messages, tools):
        self.requests.append((messages, tools))
        try:
            return next(self.turns)
        except StopIteration as exc:
            raise ProviderFailure("Script exhausted.") from exc


class RecordingRegistry(ToolRegistry):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dispatched = []

    async def _read_doc(self, arguments):
        self.dispatched.append(dict(arguments))
        return await super()._read_doc(arguments)


def run(provider, registry=None, limits=None):
    return asyncio.run(Agent(provider, registry or ToolRegistry(), limits).run("Read the note."))


def test_actual_tool_execution_arguments_and_observation_round_trip():
    provider = SequenceProvider(read_turn("deploy-guide"), ModelTurn(answer="Done."))
    registry = RecordingRegistry()
    result = run(provider, registry)
    assert result.termination == "success"
    assert (result.steps, result.tool_calls, result.answer) == (2, 1, "Done.")
    assert registry.dispatched == [{"doc_id": "deploy-guide"}]
    messages, tools = provider.requests[1]
    assert [message.role for message in messages] == ["system", "user", "assistant", "tool"]
    assert messages[-2].tool_calls[0].arguments == {"doc_id": "deploy-guide"}
    assert messages[-1].tool_call_id == "read-1"
    observation = json.loads(messages[-1].content)
    assert observation == {
        "status": "ok",
        "content": DOCUMENTS["deploy-guide"],
        "truncated": False,
        "untrusted": True,
    }
    assert {tool.name for tool in tools} == {"list_docs", "read_doc"}
    assert [event["event"] for event in result.events] == [
        "model_requested",
        "model_returned",
        "tool_started",
        "tool_finished",
        "model_requested",
        "model_returned",
        "terminated",
    ]


@pytest.mark.parametrize(
    ("turn", "termination"),
    [
        (read_turn("private-release"), "denied"),
        (ModelTurn(tool_calls=(ToolCall("x", "shell", {}),)), "denied"),
        (read_turn("../secrets"), "invalid_request"),
        (read_turn(True), "invalid_request"),
        (ModelTurn(tool_calls=(ToolCall("x", "read_doc", {}),)), "invalid_request"),
    ],
)
def test_denial_or_invalid_arguments_never_dispatch(turn, termination):
    registry = RecordingRegistry()
    result = run(SequenceProvider(turn), registry)
    assert result.termination == termination
    assert result.tool_calls == 0
    assert registry.dispatched == []
    assert not any(event["event"] == "tool_started" for event in result.events)
    assert result.answer is None


def test_entire_turn_authorized_before_any_dispatch():
    registry = RecordingRegistry()
    turn = ModelTurn(
        tool_calls=(
            ToolCall("a", "read_doc", {"doc_id": "deploy-guide"}),
            ToolCall("b", "read_doc", {"doc_id": "private-release"}),
        )
    )
    result = run(SequenceProvider(turn), registry)
    assert result.termination == "denied"
    assert result.tool_calls == 0
    assert registry.dispatched == []


def test_multiple_tools_execute_sequentially():
    turn = ModelTurn(
        tool_calls=(
            ToolCall("a", "read_doc", {"doc_id": "deploy-guide"}),
            ToolCall("b", "read_doc", {"doc_id": "untrusted-note"}),
        )
    )
    registry = RecordingRegistry()
    provider = SequenceProvider(turn, ModelTurn(answer="Done."))
    result = run(provider, registry)
    assert result.termination == "success"
    assert registry.dispatched == [{"doc_id": "deploy-guide"}, {"doc_id": "untrusted-note"}]
    assert [message.tool_call_id for message in provider.requests[1][0][-2:]] == ["a", "b"]
    assert [event["event"] for event in result.events][2:6] == [
        "tool_started",
        "tool_finished",
        "tool_started",
        "tool_finished",
    ]


@pytest.mark.parametrize(
    "turn",
    [
        None,
        ModelTurn(),
        ModelTurn(answer=""),
        ModelTurn(answer="a" * 4097),
        ModelTurn(answer="answer", tool_calls=read_turn("deploy-guide").tool_calls),
        ModelTurn(tool_calls=(ToolCall("bad\nid", "read_doc", {}),)),
        ModelTurn(tool_calls=(ToolCall("x", "read_doc", []),)),
        ModelTurn(tool_calls=(ToolCall("x", "read_doc", {}), ToolCall("x", "read_doc", {}))),
    ],
)
def test_invalid_model_turn_has_explicit_failure(turn):
    result = run(SequenceProvider(turn))
    assert result.termination == "invalid_request"
    assert result.tool_calls == 0


def test_step_limit_counts_model_requests():
    provider = SequenceProvider(read_turn("deploy-guide"), read_turn("deploy-guide"))
    result = run(provider, limits=Limits(max_steps=2))
    assert result.termination == "step_limit"
    assert (result.steps, result.tool_calls, result.answer) == (2, 2, None)
    assert len(provider.requests) == 2


def test_final_answer_allowed_on_last_step():
    result = run(SequenceProvider(ModelTurn(answer="Done.")), limits=Limits(max_steps=1))
    assert result.termination == "success"
    assert result.tool_calls == 0


def test_tool_budget_rejects_whole_turn_before_dispatch():
    turn = ModelTurn(
        tool_calls=(
            ToolCall("a", "read_doc", {"doc_id": "deploy-guide"}),
            ToolCall("b", "read_doc", {"doc_id": "untrusted-note"}),
        )
    )
    registry = RecordingRegistry()
    result = run(SequenceProvider(turn), registry, Limits(max_tool_calls=1))
    assert result.termination == "tool_limit"
    assert result.tool_calls == 0
    assert registry.dispatched == []


def test_tool_budget_counts_across_steps():
    result = run(ScriptedProvider("step-limit"), limits=Limits(max_tool_calls=1))
    assert result.termination == "tool_limit"
    assert (result.steps, result.tool_calls) == (2, 1)


def test_missing_authorized_document_is_tool_error_not_answer():
    result = run(
        SequenceProvider(read_turn("missing-doc")),
        ToolRegistry(allowed_docs=frozenset({"missing-doc"})),
    )
    assert result.termination == "tool_error"
    assert result.answer is None
    assert result.tool_calls == 1


def test_expected_tool_failure_does_not_leak_exception_text():
    class BrokenRegistry(ToolRegistry):
        async def _read_doc(self, arguments):
            raise ToolFailure("private diagnostic")

    result = run(SequenceProvider(read_turn("deploy-guide")), BrokenRegistry())
    assert result.termination == "tool_error"
    assert "private diagnostic" not in str(result.events)


def test_provider_exception_has_no_silent_fallback():
    result = run(SequenceProvider())
    assert result.termination == "provider_error"
    assert result.answer is None


def test_unexpected_tool_programming_error_propagates():
    class BrokenRegistry(ToolRegistry):
        async def _read_doc(self, arguments):
            raise RuntimeError("Broken tool implementation.")

    with pytest.raises(RuntimeError, match="Broken tool implementation"):
        run(SequenceProvider(read_turn("deploy-guide")), BrokenRegistry())


@pytest.mark.parametrize(
    "failure", [ValueError("Implementation error."), TimeoutError("Upstream.")]
)
def test_unexpected_provider_errors_are_not_hidden_as_termination(failure):
    class BrokenProvider:
        async def complete(self, messages, tools):
            raise failure

    with pytest.raises(type(failure)) as caught:
        run(BrokenProvider())
    assert caught.value is failure


def test_model_timeout_cancels_in_flight_work():
    class SlowProvider:
        cancelled = False

        async def complete(self, messages, tools):
            try:
                await asyncio.sleep(3600)
            finally:
                self.cancelled = True

    provider = SlowProvider()
    result = run(provider, limits=Limits(timeout_seconds=0.01))
    assert result.termination == "timeout"
    assert provider.cancelled
    assert (result.steps, result.tool_calls) == (1, 0)


def test_tool_timeout_cancels_in_flight_work():
    class SlowRegistry(ToolRegistry):
        cancelled = False

        async def _read_doc(self, arguments):
            try:
                await asyncio.sleep(3600)
            finally:
                self.cancelled = True

    registry = SlowRegistry()
    result = run(
        SequenceProvider(read_turn("deploy-guide")), registry, Limits(timeout_seconds=0.01)
    )
    assert result.termination == "timeout"
    assert registry.cancelled
    assert result.tool_calls == 1


def test_deadline_covers_combined_model_and_tool_time():
    class SlowProvider(SequenceProvider):
        async def complete(self, messages, tools):
            await asyncio.sleep(0.03)
            return await super().complete(messages, tools)

    class SlowRegistry(ToolRegistry):
        async def _read_doc(self, arguments):
            await asyncio.sleep(0.03)
            return await super()._read_doc(arguments)

    result = run(
        SlowProvider(read_turn("deploy-guide"), ModelTurn(answer="Done.")),
        SlowRegistry(),
        Limits(timeout_seconds=0.05),
    )
    assert result.termination == "timeout"
    assert result.answer is None


def test_injected_text_does_not_grant_resource_authorization():
    provider = SequenceProvider(read_turn("untrusted-note"), read_turn("private-release"))
    registry = RecordingRegistry()
    result = run(provider, registry)
    assert result.termination == "denied"
    assert registry.dispatched == [{"doc_id": "untrusted-note"}]
    observation = json.loads(provider.requests[1][0][-1].content)
    assert observation["untrusted"] is True
    assert "IGNORE ALL PREVIOUS INSTRUCTIONS" in observation["content"]
    assert DOCUMENTS["private-release"] not in str(result.events)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_steps": 0},
        {"max_steps": True},
        {"max_tool_calls": -1},
        {"max_tool_calls": 101},
        {"timeout_seconds": 0},
        {"timeout_seconds": float("nan")},
        {"timeout_seconds": float("inf")},
        {"timeout_seconds": True},
    ],
)
def test_limits_are_strict(kwargs):
    with pytest.raises(ValueError):
        Limits(**kwargs)


@pytest.mark.parametrize("user_request", ["", " " * 5, "x" * 4097, None])
def test_invalid_request_does_not_call_model(user_request):
    provider = SequenceProvider()
    result = asyncio.run(Agent(provider, ToolRegistry()).run(user_request))
    assert result.termination == "invalid_request"
    assert result.steps == 0
    assert provider.requests == []
