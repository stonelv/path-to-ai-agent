import asyncio

import pytest
from agent_loop import run_loop as student_loop
from authorization import authorize_read as student_authorize

from tool_agent.agent import Agent, Limits
from tool_agent.tools import ToolRegistry


def pytest_addoption(parser):
    parser.addoption(
        "--reference",
        action="store_true",
        help="Run exercise acceptance tests against the production implementation.",
    )


@pytest.fixture
def authorize_read(request):
    if not request.config.getoption("--reference"):
        return student_authorize

    def reference(arguments, allowed_docs):
        return ToolRegistry(allowed_docs).prepare("read_doc", arguments)["doc_id"]

    return reference


@pytest.fixture
def run_exercise(request, monkeypatch):
    reference = request.config.getoption("--reference")
    if not reference:

        async def forbidden(*args, **kwargs):
            raise AssertionError("Implement the exercise loop; do not delegate to Agent.run.")

        monkeypatch.setattr(Agent, "run", forbidden)

    def run(provider, registry=None, limits=None):
        registry = registry if registry is not None else ToolRegistry()
        limits = limits if limits is not None else Limits()
        if reference:
            operation = Agent(provider, registry, limits).run("Read the synthetic release guide.")
        else:
            operation = student_loop(
                provider, registry, "Read the synthetic release guide.", limits
            )

        async def guarded():
            # A broken cooperative student loop must not leave pytest waiting forever.
            return await asyncio.wait_for(operation, timeout=2.0)

        return asyncio.run(guarded())

    return run
