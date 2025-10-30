import argparse
import asyncio
import os
import sys
import logging
from datetime import datetime
from typing import Dict, Any, List

from abilities import execute_ability, AbilityError, execute_parallel_tasks
from agent_loader import load_agent_yaml


def setup_logging():
    """Setup logging with both file and console handlers"""
    # Create logs directory if it doesn't exist
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(script_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Create a unique log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(logs_dir, f"reasonloop_{timestamp}.log")

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_filename), logging.StreamHandler(sys.stdout)],
    )

    return logging.getLogger(__name__)


def load_dotenv(path: str = ".env"):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


async def plan_tasks(agent: Dict[str, Any], objective: str) -> List[Dict[str, Any]]:
    # Single LLM call to create a small task list (no DAG complexity)
    abilities = ", ".join(agent.get("abilities", []))
    rfw = agent.get("reasoning_framework", "")
    dc = agent.get("decision_criteria", "")
    req = agent.get("required_output", "")
    prompt = f"""
You are {agent.get("name")} - {agent.get("description")}
Abilities available: {abilities}

Objective:
{objective}

Reasoning framework:
{rfw}

Decision criteria:
{dc}

Required output:
{req}

Return a concise JSON array of 3-6 tasks with fields:
- id (int, sequential from 1)
- description (string)
- ability (one of: {abilities})
- input (string or object)
- deps (array of ids, can be empty)

IMPORTANT ABILITY USAGE:
- Use "text-completion" for all tasks including research, analysis, synthesis, and generating structured content
- The system will use the LLM's built-in knowledge to provide comprehensive answers
- Structure your tasks to be self-contained and use the LLM's training data for information

Respond with JSON only.
"""
    tasks_json = await execute_ability("text-completion", prompt)
    # Minimal JSON parse without external deps
    import json
    import re

    try:
        # Clean the JSON string by removing invalid control characters
        # Remove control characters except newline, carriage return, and tab
        clean_json = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", "", tasks_json)

        # Fix specific malformed JSON patterns from LLM
        # Pattern 1: Fix "id": 4,\n", -> "id": 4,
        clean_json = re.sub(r'"id":\s*(\d+),\s*\n\s*",', r'"id": \1,', clean_json)

        # Pattern 2: Fix orphaned quote lines
        clean_json = re.sub(r'\n\s*",\s*\n', "\n", clean_json)

        # Pattern 3: Fix trailing commas followed by quotes on new lines
        clean_json = re.sub(r',\s*\n\s*"\s*,\s*\n', ",\n", clean_json)

        # Pattern 4: Fix missing description after ID (e.g., "id": 4,\n", -> "id": 4, "description": "...")
        clean_json = re.sub(
            r'"id":\s*(\d+),\s*\n\s*",\s*\n\s*"ability":',
            r'"id": \1,\n    "description": "Task \1 description",\n    "ability":',
            clean_json,
        )

        # Pattern 5: Fix corrupted property names (e.g., "-than": -> "ability":)
        clean_json = re.sub(r'[^"]*-than":\s*"([^"]+)"', r'"ability": "\1"', clean_json)
        clean_json = re.sub(
            r'"[^"]*-tion":\s*"([^"]+)"', r'"description": "\1"', clean_json
        )
        clean_json = re.sub(r'"[^"]*-put":\s*"([^"]+)"', r'"input": "\1"', clean_json)

        # Pattern 6: Fix malformed IDs - replace any non-numeric ID with proper sequential numbers
        lines = clean_json.split("\n")
        id_counter = 1

        for i, line in enumerate(lines):
            if '"id":' in line:
                # Extract and fix the ID line
                if not re.search(r'"id":\s*\d+,', line):
                    # Replace malformed ID with sequential number
                    lines[i] = re.sub(r'"id":\s*[^,]*,', f'"id": {id_counter},', line)
                    id_counter += 1
                else:
                    # Count existing numeric IDs
                    match = re.search(r'"id":\s*(\d+),', line)
                    if match:
                        existing_id = int(match.group(1))
                        if existing_id >= id_counter:
                            id_counter = existing_id + 1

        clean_json = "\n".join(lines)

        tasks = json.loads(clean_json)
        assert isinstance(tasks, list)
        # Light validation
        for t in tasks:
            if "id" not in t or "ability" not in t or "description" not in t:
                raise ValueError("Invalid task schema")
            if t["ability"] not in agent.get("abilities", []):
                raise ValueError(f"Ability not allowed: {t['ability']}")
            t.setdefault("deps", [])
            t.setdefault("input", "")
        return tasks
    except Exception as e:
        print("Failed to parse task list from LLM:", e, file=sys.stderr)
        print(tasks_json, file=sys.stderr)
        sys.exit(1)


def topo_sort(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_id = {t["id"]: t for t in tasks}
    visited, temp, order = set(), set(), []

    def visit(nid: int):
        if nid in visited:
            return
        if nid in temp:
            raise ValueError("Cycle detected in task deps")
        temp.add(nid)
        for d in by_id[nid].get("deps", []):
            if d not in by_id:
                raise ValueError(f"Unknown dep id: {d}")
            visit(d)
        temp.remove(nid)
        visited.add(nid)
        order.append(by_id[nid])

    for t in tasks:
        visit(t["id"])
    return order


async def execute_task(task: Dict[str, Any]) -> str:
    ability = task["ability"]
    desc = task["description"]
    inp = task.get("input", "")

    if ability == "text-completion":
        try:
            # Add timeout for individual task execution
            return await asyncio.wait_for(
                execute_ability("text-completion", f"{desc}\n\nInput:\n{inp}"),
                timeout=180,  # 3 minutes per task
            )
        except asyncio.TimeoutError:
            print(f"Task {task['id']} timed out after 3 minutes", file=sys.stderr)
            return f"Task timed out - unable to complete: {desc[:100]}..."
        except Exception as e:
            print(f"Task {task['id']} failed with error: {e}", file=sys.stderr)
            return f"Task failed - {str(e)}: {desc[:100]}..."
    raise AbilityError(f"Unknown ability {ability}")


async def run_agent(agent_path: str, objective: str) -> None:
    logger = logging.getLogger(__name__)
    logger.info(f"Starting ReasonLoop run with objective: {objective}")
    logger.info(f"Using agent: {agent_path}")

    agent = load_agent_yaml(agent_path)
    logger.info(
        f"Agent loaded: {agent.get('name', 'Unknown')} - {agent.get('description', 'No description')}"
    )

    # Plan
    logger.info("Planning tasks...")
    tasks = await plan_tasks(agent, objective)
    logger.info(f"Generated {len(tasks)} tasks")
    for task in tasks:
        logger.info(f"Task {task['id']}: {task['description']}")

    ordered = topo_sort(tasks)
    logger.info(f"Tasks ordered for execution: {[t['id'] for t in ordered]}")

    # Execute respecting deps; simple concurrency for independent tasks
    completed: Dict[int, str] = {}

    async def ready_tasks():
        return [
            t
            for t in ordered
            if t["id"] not in completed
            and all(d in completed for d in t.get("deps", []))
        ]

    # Enhanced loop with parallel execution for independent tasks
    while len(completed) < len(ordered):
        batch = await ready_tasks()
        if not batch:
            raise RuntimeError("Deadlock: no ready tasks but not complete")

        logger.info(f"Executing batch of {len(batch)} tasks in parallel...")

        # Use parallel execution for the batch
        start_time = datetime.now()
        batch_results = await execute_parallel_tasks(batch, max_concurrent=3)

        # Update completed tasks
        for task_id, result in batch_results.items():
            completed[task_id] = result

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Completed batch of {len(batch)} tasks in {duration:.2f}s")

    # Final assembly: pass prior outputs to LLM for final synthesis if last task is text-completion
    logger.info("Starting final synthesis...")
    final_output = None
    last_task = ordered[-1]
    if last_task["ability"] == "text-completion":
        combined_parts = []
        for t in ordered:
            combined_parts.append(
                f"Task {t['id']} ({t['description']}):\n{completed[t['id']]}"
            )
        combined_text = "\n\n".join(combined_parts)

        synthesis_prompt = (
            f"Using the agent's decision criteria, synthesize a final response for the objective:\n"
            f"{objective}\n\n"
            f"Context from executed tasks:\n"
            f"{combined_text}\n\n"
            f"Return a concise, actionable final output."
        )
        logger.info("Performing final synthesis...")
        final_output = await execute_ability("text-completion", synthesis_prompt)
    else:
        final_output = completed[last_task["id"]]

    logger.info(f"Final output generated ({len(final_output)} characters)")
    print(final_output.strip())
    logger.info("ReasonLoop run completed successfully")


def main():
    parser = argparse.ArgumentParser(description="Ultra-minimal async agent runner")
    parser.add_argument("--objective", required=True, help="Objective to achieve")
    parser.add_argument("--agent", required=True, help="Path to agent YAML")
    parser.add_argument("--env", default=".env", help="Path to .env file")
    args = parser.parse_args()

    # Setup logging first
    logger = setup_logging()

    load_dotenv(args.env)
    try:
        logger.info("=== ReasonLoop Starting ===")
        logger.info(f"Objective: {args.objective}")
        logger.info(f"Agent: {args.agent}")
        asyncio.run(run_agent(args.agent, args.objective))
        logger.info("=== ReasonLoop Finished Successfully ===")
    except SystemExit:
        raise
    except AbilityError as e:
        logger.error(f"Ability error: {e}")
        print(f"Ability error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
