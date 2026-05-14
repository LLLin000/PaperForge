"""paperforge.commands — shared command implementations for CLI and Agent."""

# Command registry for dynamic dispatch
_COMMAND_REGISTRY: dict[str, str] = {
    "sync": "paperforge.commands.sync",
    "ocr": "paperforge.commands.ocr",
    "deep": "paperforge.commands.deep",
    "repair": "paperforge.commands.repair",
    "status": "paperforge.commands.status",
    "context": "paperforge.commands.context",
    "dashboard": "paperforge.commands.dashboard",
    "finalize": "paperforge.commands.finalize",
    "memory": "paperforge.commands.memory",
    "embed": "paperforge.commands.embed",
    "retrieve": "paperforge.commands.retrieve",
    "paper-status": "paperforge.commands.paper_status",
    "agent-context": "paperforge.commands.agent_context",
    "reading-log": "paperforge.commands.reading_log",
}


def get_command_module(name: str):
    """Dynamically import a command module by name."""
    import importlib

    module_path = _COMMAND_REGISTRY.get(name)
    if module_path is None:
        raise ValueError(f"Unknown command: {name}")
    return importlib.import_module(module_path)


__all__ = ["get_command_module", "_COMMAND_REGISTRY"]
