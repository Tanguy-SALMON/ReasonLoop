"""
Registry of all available abilities
"""

import asyncio
import inspect
import logging
import time
from typing import Dict, Callable, Any, Optional

logger = logging.getLogger(__name__)

# Dictionary to store all registered abilities
ABILITY_REGISTRY: Dict[str, Callable] = {}


def register_ability(name: str, func: Callable) -> None:
    """Register an ability function with a name"""
    logger.debug(f"Registering ability: {name}")
    ABILITY_REGISTRY[name] = func


def get_ability(name: str) -> Optional[Callable]:
    """Get an ability function by name"""
    ability = ABILITY_REGISTRY.get(name)
    if ability is None:
        logger.warning(f"Ability not found: {name}")
    return ability


def list_abilities() -> Dict[str, Callable]:
    """List all registered abilities"""
    return ABILITY_REGISTRY.copy()


def execute_ability(name: str, *args: Any, **kwargs: Any) -> Any:
    """Execute an ability by name with arguments"""
    from utils.prompt_logger import log_prompt

    ability = get_ability(name)
    if ability is None:
        logger.warning(f"Ability not found: {name}")
        raise ValueError(f"Ability not found: {name}")

    logger.debug(f"Executing ability: {name}")

    # Extract task_id and role from kwargs if present
    task_id = kwargs.pop("task_id", None)
    role = kwargs.pop("role", None)

    # Get the prompt (usually the first argument for text abilities)
    prompt = args[0] if args and isinstance(args[0], str) else str(args)

    # For text-completion ability, add role to kwargs if provided and request usage data
    if name == "text-completion" and role:
        kwargs["role"] = role
        kwargs["return_usage"] = True
        logger.debug(f"Using role: {role} for text-completion")

    # Execute the ability and capture the response
    start_time = time.time()
    try:
        # Check if ability is async (coroutine)
        result = ability(*args, **kwargs)
        if inspect.iscoroutine(result):
            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                # We're in a loop, shouldn't happen in sync context
                logger.warning("Async ability called from within event loop - this may cause issues")
            except RuntimeError:
                # No loop running, safe to use asyncio.run()
                result = asyncio.run(result)

        execution_time = time.time() - start_time

        # Handle tuple response (response, usage_dict) from text-completion
        usage_data = None
        if isinstance(result, tuple) and len(result) == 2:
            response, usage_data = result
        else:
            response = result

        # Log the prompt and response with usage data
        log_prompt(
            prompt=prompt,
            response=response if isinstance(response, str) else str(response),
            ability=name,
            task_id=task_id,
            metadata={
                "execution_time": execution_time,
                "role": role,
                "args": str(args[1:]) if len(args) > 1 else None,
                "kwargs": str(kwargs) if kwargs else None,
            },
            usage=usage_data
        )

        return response
    except Exception as e:
        execution_time = time.time() - start_time

        # Log the error
        log_prompt(
            prompt=prompt,
            response=f"ERROR: {str(e)}",
            ability=name,
            task_id=task_id,
            metadata={
                "execution_time": execution_time,
                "role": role,
                "error": str(e),
                "args": str(args[1:]) if len(args) > 1 else None,
                "kwargs": str(kwargs) if kwargs else None,
            },
        )
        raise
