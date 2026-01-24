"""
ReasonLoop - A modular AI agent system

Usage:
    from reasonloop import run_agent, run_execution_loop

    # Simple usage
    result = run_agent("email_campaign_generator", "Generate emails for https://example.com")

    # Or direct execution loop
    from reasonloop.config import update_setting
    update_setting("PROMPT_TEMPLATE", "email_campaign_generator")
    result = run_execution_loop("Generate emails for https://example.com")
"""

__version__ = "0.2.1"


# Lazy imports to avoid circular dependencies
def run_execution_loop(objective: str) -> str:
    """Run the execution loop with an objective"""
    from core.execution_loop import run_execution_loop as _run

    return _run(objective)


def run_agent(template: str, objective: str) -> str:
    """
    Run an agent template with an objective.

    Args:
        template: Agent template name (e.g., "email_campaign_generator")
        objective: The objective/task to accomplish

    Returns:
        Path to the result file
    """
    from config.settings import update_setting
    from core.execution_loop import run_execution_loop as _run

    update_setting("PROMPT_TEMPLATE", template)
    return _run(objective)


__all__ = [
    "__version__",
    "run_execution_loop",
    "run_agent",
]
