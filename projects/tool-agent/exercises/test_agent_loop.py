import asyncio
import json

import pytest

from tool_agent.agent import Limits, Result
from tool_agent.contracts import ModelTurn, ProviderFailure, ToolCall
from tool_agent.tools import DOCUMENTS, ToolRegistry


def read(doc_id="deploy-guide", call_id="read-1"):
    return ToolCall(call_id, "read_doc", {"doc_id": doc_id})


class RepeatingProvider:
    def __init__(self, turn):
        self.turn = turn
        self.requests = []

    async def complete(self, messages, tools):
        self.requests.append((messages, tools))
        await asyncio.sleep(0)
        return self.turn


class RecordingRegistry(ToolRegistry):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dispatched = []

    async def execute(self, name, arguments):
        self.dispatched.append((name, dict(arguments)))
        return await super().execute(name, arguments)


def assert_stopped(result, reason, steps, calls):
    assert isinstance(result, Result)
    assert result.termination == reason
    assert (result.steps, result.tool_calls) == (steps, calls)
    assert result.answer is None


def test_success_executes_tool_and_feeds_observation_back(run_exercise):
    class FeedbackProvider:
        requests = 0

        async def complete(self, messages, tools):
            self.requests += 1
            assert {tool.name for tool in tools} == {"list_docs", "read_doc"}
            assert messages[0].role == "system"
            assert any(message.role == "user" for message in messages)
            if self.requests == 1:
                return ModelTurn(tool_calls=(read(),))
            assert self.requests == 2
            assistant = next(message for message in messages if message.role == "assistant")
            assert assistant.tool_calls == (read(),)
            observation = messages[-1]
            assert observation.role == "tool"
            assert observation.tool_call_id == "read-1"
            payload = json.loads(observation.content)
            assert payload["status"] == "ok"
            assert payload["untrusted"] is True
            assert payload["truncated"] is False
            return ModelTurn(answer="Read: " + payload["content"])

    registry = RecordingRegistry()
    result = run_exercise(FeedbackProvider(), registry)
    assert isinstance(result, Result)
    assert result.termination == "success"
    assert result.answer == "Read: " + DOCUMENTS["deploy-guide"]
    assert (result.steps, result.tool_calls) == (2, 1)
    assert registry.dispatched == [("read_doc", {"doc_id": "deploy-guide"})]


def test_denied_second_request_prevents_entire_turn_dispatch(run_exercise):
    registry = RecordingRegistry()
    provider = RepeatingProvider(
        ModelTurn(tool_calls=(read(call_id="a"), read("private-release", "b")))
    )
    result = run_exercise(provider, registry)
    assert_stopped(result, "denied", 1, 0)
    assert registry.dispatched == []
    assert len(provider.requests) == 1


def test_authorized_missing_resource_is_tool_error(run_exercise):
    registry = RecordingRegistry(allowed_docs=frozenset({"missing-doc"}))
    provider = RepeatingProvider(ModelTurn(tool_calls=(read("missing-doc"),)))
    result = run_exercise(provider, registry)
    assert_stopped(result, "tool_error", 1, 1)
    assert registry.dispatched == [("read_doc", {"doc_id": "missing-doc"})]
    assert len(provider.requests) == 1


def test_step_limit_stops_model_requests(run_exercise):
    provider = RepeatingProvider(ModelTurn(tool_calls=(read(),)))
    result = run_exercise(provider, limits=Limits(max_steps=2))
    assert_stopped(result, "step_limit", 2, 2)
    assert len(provider.requests) == 2


def test_tool_limit_preflights_whole_turn(run_exercise):
    registry = RecordingRegistry()
    provider = RepeatingProvider(
        ModelTurn(tool_calls=(read(call_id="a"), read("untrusted-note", "b")))
    )
    result = run_exercise(provider, registry, Limits(max_tool_calls=1))
    assert_stopped(result, "tool_limit", 1, 0)
    assert registry.dispatched == []


def test_tool_budget_accumulates_across_steps(run_exercise):
    registry = RecordingRegistry()
    provider = RepeatingProvider(ModelTurn(tool_calls=(read(),)))
    result = run_exercise(provider, registry, Limits(max_tool_calls=1))
    assert_stopped(result, "tool_limit", 2, 1)
    assert len(registry.dispatched) == 1


def test_answer_on_final_allowed_step_is_success(run_exercise):
    provider = RepeatingProvider(ModelTurn(answer="Final answer."))
    result = run_exercise(provider, limits=Limits(max_steps=1))
    assert result.termination == "success"
    assert (result.steps, result.tool_calls, result.answer) == (1, 0, "Final answer.")


@pytest.mark.parametrize("waiting_on", ["model", "tool"])
def test_overall_timeout_cancels_in_flight_work(run_exercise, waiting_on):
    cancelled = []

    async def wait_until_cancelled():
        try:
            await asyncio.sleep(3600)
        finally:
            cancelled.append(waiting_on)

    class WaitingProvider(RepeatingProvider):
        async def complete(self, messages, tools):
            if waiting_on == "model":
                await wait_until_cancelled()
            return await super().complete(messages, tools)

    class WaitingRegistry(ToolRegistry):
        async def _read_doc(self, arguments):
            await wait_until_cancelled()
            return await super()._read_doc(arguments)

    result = run_exercise(
        WaitingProvider(ModelTurn(tool_calls=(read(),))),
        WaitingRegistry(),
        Limits(timeout_seconds=0.01),
    )
    assert_stopped(result, "timeout", 1, int(waiting_on == "tool"))
    assert cancelled == [waiting_on]


def test_deadline_is_not_reset_between_model_and_tool(run_exercise):
    class DelayedProvider(RepeatingProvider):
        async def complete(self, messages, tools):
            await asyncio.sleep(0.03)
            if any(message.role == "tool" for message in messages):
                return ModelTurn(answer="Too late.")
            return await super().complete(messages, tools)

    class DelayedRegistry(ToolRegistry):
        async def _read_doc(self, arguments):
            await asyncio.sleep(0.03)
            return await super()._read_doc(arguments)

    result = run_exercise(
        DelayedProvider(ModelTurn(tool_calls=(read(),))),
        DelayedRegistry(),
        Limits(timeout_seconds=0.05),
    )
    assert result.termination == "timeout"
    assert result.answer is None


def test_malformed_model_turn_never_dispatches(run_exercise):
    registry = RecordingRegistry()
    result = run_exercise(
        RepeatingProvider(ModelTurn(answer="Both?", tool_calls=(read(),))), registry
    )
    assert_stopped(result, "invalid_request", 1, 0)
    assert registry.dispatched == []


def test_typed_provider_failure_has_explicit_termination(run_exercise):
    class FailedProvider:
        async def complete(self, messages, tools):
            raise ProviderFailure("Expected provider outage.")

    assert_stopped(run_exercise(FailedProvider()), "provider_error", 1, 0)


def test_unexpected_programming_error_is_not_silently_translated(run_exercise):
    class BuggyProvider:
        async def complete(self, messages, tools):
            raise RuntimeError("Programming bug must remain visible.")

    with pytest.raises(RuntimeError, match="Programming bug must remain visible"):
        run_exercise(BuggyProvider())
