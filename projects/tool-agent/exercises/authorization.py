"""Deliberately unfinished lesson 05 starter; not used by the running application."""


def authorize_read(arguments: dict[str, object], allowed_docs: frozenset[str]) -> str:
    """Validate exactly one doc_id, authorize it, then return the identifier.

    Reuse tool_agent.tools.validate_read_arguments. Raise InvalidArguments for
    malformed parameters and ToolDenied for a well-formed but forbidden doc_id.
    Do not open a file, dispatch a tool, or return document content.
    """
    raise NotImplementedError("Implement argument validation followed by resource authorization.")
