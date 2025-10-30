import os
import asyncio
import logging
from typing import Dict, List
from xai_sdk import AsyncClient
from xai_sdk.chat import user, system

logger = logging.getLogger(__name__)


class AbilityError(Exception):
    pass


# Global client instance for reuse
_client = None


def get_client():
    """Get or create AsyncClient instance"""
    global _client
    if _client is None:
        api_key = os.getenv("XAI_API_KEY")
        if not api_key:
            raise AbilityError("XAI_API_KEY environment variable not set")

        _client = AsyncClient(
            api_key=api_key,
            timeout=3600,  # Override default timeout with longer timeout for reasoning models
        )
    return _client


async def ability_text_completion(
    prompt: str, temperature: float = 0.2, max_tokens: int = 1024
) -> str:
    """Text completion using xAI Grok with AsyncClient"""
    try:
        client = get_client()

        # Create chat session
        chat = client.chat.create(
            model="grok-4-fast-reasoning",
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # Add system message
        chat.append(
            system(
                "You are a helpful AI assistant that provides accurate, concise, and well-structured responses."
            )
        )

        # Add user message
        chat.append(user(prompt))

        # Get response
        logger.debug(f"Sending request to xAI: {prompt[:100]}...")
        response = await chat.sample()

        if response and response.content:
            result = response.content.strip()
            logger.debug(f"Received response ({len(result)} chars): {result[:100]}...")
            return result
        else:
            raise AbilityError("No response content received from xAI")

    except Exception as e:
        logger.error(f"xAI API error: {e}")
        raise AbilityError(f"xAI API error: {e}")


ABILITIES = {
    "text-completion": ability_text_completion,
}


async def execute_ability(name: str, *args, **kwargs) -> str:
    """Execute an ability by name"""
    if name not in ABILITIES:
        raise AbilityError(f"Unknown ability: {name}")
    return await ABILITIES[name](*args, **kwargs)


async def execute_parallel_tasks(
    tasks: List[Dict], max_concurrent: int = 3
) -> Dict[int, str]:
    """
    Execute multiple independent tasks in parallel with concurrency control.

    Args:
        tasks: List of task dictionaries
        max_concurrent: Maximum number of concurrent requests

    Returns:
        Dictionary mapping task IDs to their results
    """
    # Define a semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(max_concurrent)
    results = {}

    async def process_task(task: Dict) -> None:
        async with semaphore:
            task_id = task["id"]
            description = task["description"]
            input_text = task.get("input", "")

            logger.info(f"Processing task {task_id} in parallel: {description[:50]}...")

            try:
                # Execute the task
                if task["ability"] == "text-completion":
                    result = await ability_text_completion(
                        f"{description}\n\nInput:\n{input_text}"
                    )
                    results[task_id] = result
                    logger.info(
                        f"Completed parallel task {task_id} ({len(result)} chars)"
                    )
                else:
                    raise AbilityError(f"Unknown ability: {task['ability']}")

            except Exception as e:
                logger.error(f"Parallel task {task_id} failed: {e}")
                results[task_id] = f"Task failed: {str(e)}"

    # Create tasks for all independent tasks
    task_coroutines = [process_task(task) for task in tasks]

    # Execute all tasks in parallel
    await asyncio.gather(*task_coroutines)

    return results
