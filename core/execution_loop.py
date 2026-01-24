"""
Main execution loop for the application
"""

import json
import logging
import os
import time
from datetime import datetime

from core.task_manager import TaskManager

logger = logging.getLogger(__name__)


def _update_crawler_summary(task_manager: TaskManager, execution_time: float) -> None:
    """
    Update output/*/summary.md with task execution details if web crawler was used.

    Searches for web_crawler tasks, finds their output_session paths, and updates
    the summary files with the complete task list.
    """
    # Check if any task used web crawler abilities
    crawler_sessions = []

    for task in task_manager.tasks:
        if (
            task.ability in ["web_crawler", "web_crawler_with_screenshots"]
            and task.output
        ):
            try:
                # Parse JSON output to find output_session path
                output_data = json.loads(task.output)
                session_dir = output_data.get("output_session")

                if session_dir:
                    crawler_sessions.append(session_dir)
            except (json.JSONDecodeError, KeyError, TypeError):
                # Task output not in expected format, skip
                continue

    if not crawler_sessions:
        # No web crawler tasks found
        return

    # Import OutputManager
    from utils.output_manager import OutputManager

    # Convert tasks to dict format for update_summary_with_tasks
    tasks_data = [task.to_dict() for task in task_manager.tasks]

    # Update each crawler session's summary
    for session_dir in crawler_sessions:
        try:
            # Create OutputManager from existing session dir
            # Extract domain and timestamp from session_dir format: output/domain_timestamp
            session_name = os.path.basename(session_dir)
            parts = session_name.rsplit(
                "_", 2
            )  # Split from right: domain_YYYYMMDD_HHMMSS

            if len(parts) >= 3:
                domain = "_".join(parts[:-2])
                timestamp = f"{parts[-2]}_{parts[-1]}"
            else:
                # Fallback: use entire name as domain
                domain = session_name
                timestamp = None

            output_manager = OutputManager(domain, timestamp)
            output_manager.update_summary_with_tasks(tasks_data, execution_time)

            logger.info(f"Updated summary in {session_dir}")
        except Exception as e:
            logger.warning(f"Failed to update summary in {session_dir}: {e}")

    if crawler_sessions:
        logger.info(
            f"Updated {len(crawler_sessions)} crawler session summaries with task details"
        )


def run_execution_loop(objective: str) -> str:
    """Run the main execution loop and return the result file path"""
    logger.info(f"Starting: {objective}")
    start_time = time.time()

    task_manager = TaskManager(objective)
    tasks = task_manager.create_initial_tasks()

    if not tasks:
        logger.error("Failed to create initial tasks")
        return False

    task_manager.print_task_list()

    cycle_count = 0
    completed_tasks = 0
    total_tasks = len(tasks)

    # Import colors
    try:
        from colorama import Fore, Style
    except ImportError:

        class Fore:
            CYAN = GREEN = YELLOW = ""

        class Style:
            BRIGHT = RESET_ALL = ""

    while True:
        cycle_count += 1
        progress_bar = "█" * completed_tasks + "░" * (total_tasks - completed_tasks)
        print(f"\n{Fore.CYAN}{'═' * 80}{Style.RESET_ALL}")
        print(
            f"{Fore.GREEN}Progress: [{progress_bar}] {completed_tasks}/{total_tasks}{Style.RESET_ALL}"
        )
        print(f"{Fore.CYAN}{'═' * 80}{Style.RESET_ALL}")

        next_task = task_manager.find_next_task()
        if not next_task:
            print(f"\n{Fore.GREEN}✓ All tasks completed!{Style.RESET_ALL}\n")
            break

        result = task_manager.execute_task(next_task)
        if result.success:
            completed_tasks += 1
        else:
            logger.error(f"Task #{next_task.id} failed: {result.error}")

        task_manager.print_task_list()
        time.sleep(0.5)

    execution_time = time.time() - start_time
    logger.info(
        f"COMPLETE: {completed_tasks}/{total_tasks} tasks in {execution_time:.2f}s"
    )

    # Update output summary with task details if web crawler was used
    _update_crawler_summary(task_manager, execution_time)

    # Save results to markdown file
    output_dir = "sessions"
    os.makedirs(output_dir, exist_ok=True)

    # Create filename from objective (first 100 chars, sanitized)
    safe_name = "".join(
        c if c.isalnum() or c in (" ", "-", "_") else "_" for c in objective[:100]
    )
    safe_name = safe_name.strip().replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/{safe_name}_{timestamp}.md"

    summary = task_manager.get_session_summary()

    # Create markdown content
    markdown_content = f"""# ReasonLoop Execution Results

**Objective:** {objective}
**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Execution Time:** {execution_time:.2f} seconds
**Tasks Completed:** {completed_tasks}/{total_tasks}

---

{summary}
"""

    with open(filename, "w") as f:
        f.write(markdown_content)

    logger.info(f"Results saved to {filename}")
    logger.info(summary)

    return filename
