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
            # Extract domain and timestamp from session_dir format: output/domain_YYYYMMDD
            session_name = os.path.basename(session_dir)
            parts = session_name.rsplit("_", 1)  # Split from right: domain_YYYYMMDD

            if len(parts) >= 2:
                domain = parts[0]
                timestamp = parts[1]
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


def _save_intelligence_output(task_manager: TaskManager, objective: str) -> None:
    """
    Save the final intelligence JSON to output folder if:
    1. Objective contains a URL
    2. Final task output contains JSON with intelligence_report or email_campaign_recommendations
    """
    import re

    try:
        from colorama import Fore, Style
    except ImportError:

        class Fore:
            GREEN = ""

        class Style:
            RESET_ALL = ""

    # Extract URL from objective
    url_match = re.search(r"https?://[^\s,;:)]+", objective)
    if not url_match:
        return

    url = url_match.group(0).rstrip(".,;:)")

    # Get the last completed task's output
    completed_tasks = [
        t for t in task_manager.tasks if t.status == "complete" and t.output
    ]
    if not completed_tasks:
        return

    last_task = completed_tasks[-1]
    output = last_task.output

    # Try to extract JSON from the output
    json_data = None

    # Check if output contains a JSON code block
    json_match = re.search(r"```json\s*([\s\S]*?)\s*```", output)
    if json_match:
        try:
            json_data = json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # If no code block, try parsing the whole output as JSON
    if not json_data:
        try:
            json_data = json.loads(output)
        except json.JSONDecodeError:
            pass

    # Check if it looks like an intelligence report
    if not json_data:
        return

    if not isinstance(json_data, dict):
        return

    # Must have intelligence_report or email_campaign_recommendations
    if (
        "intelligence_report" not in json_data
        and "email_campaign_recommendations" not in json_data
    ):
        return

    # Save to output folder
    try:
        from utils.output_manager import create_output_session
        from utils.url_normalizer import normalize_url

        normalized_url, clean_domain = normalize_url(url)
        output_manager = create_output_session(clean_domain)

        # Save intelligence JSON
        intelligence_path = output_manager.save_data("intelligence.json", json_data)
        logger.info(f"Saved intelligence report to {intelligence_path}")

        # Create/update summary
        output_manager.create_summary(
            url=normalized_url,
            pages_crawled=1,
            screenshots_taken=0,
            emails_generated=0,
            additional_info={"source": "website_intelligence_agent"},
        )

        print(
            f"\n{Fore.GREEN}Saved intelligence to: {intelligence_path}{Style.RESET_ALL}"
        )

    except Exception as e:
        logger.warning(f"Failed to save intelligence output: {e}")


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
        print(f"\n{Fore.YELLOW}{'═' * 80}{Style.RESET_ALL}")
        print(
            f"{Fore.YELLOW}Progress: [{progress_bar}] {completed_tasks}/{total_tasks}{Style.RESET_ALL}"
        )
        print(f"{Fore.YELLOW}{'═' * 80}{Style.RESET_ALL}")

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

    # Save intelligence JSON to output folder if objective contains a URL
    _save_intelligence_output(task_manager, objective)

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

    # Pretty print the summary to terminal
    _print_session_summary(
        filename, objective, execution_time, completed_tasks, total_tasks, summary
    )

    return filename


def _print_session_summary(
    filename: str,
    objective: str,
    execution_time: float,
    completed_tasks: int,
    total_tasks: int,
    summary: str,
) -> None:
    """Print a nicely formatted session summary to terminal."""
    try:
        from colorama import Fore, Style
    except ImportError:

        class Fore:
            YELLOW = GREEN = WHITE = CYAN = ""

        class Style:
            BRIGHT = RESET_ALL = ""

    # Header
    print(f"\n{Fore.YELLOW}{'─' * 80}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{Style.BRIGHT}SESSION COMPLETE{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'─' * 80}{Style.RESET_ALL}\n")

    # Stats
    print(
        f"{Fore.WHITE}Objective:{Style.RESET_ALL} {objective[:70]}{'...' if len(objective) > 70 else ''}"
    )
    print(f"{Fore.WHITE}Duration:{Style.RESET_ALL}  {execution_time:.1f}s")
    print(
        f"{Fore.WHITE}Tasks:{Style.RESET_ALL}     {Fore.GREEN}{completed_tasks}/{total_tasks} completed{Style.RESET_ALL}"
    )
    print(
        f"{Fore.WHITE}Saved to:{Style.RESET_ALL}  {Fore.CYAN}{filename}{Style.RESET_ALL}"
    )

    # Summary preview (first 500 chars, cleaned up)
    if summary:
        print(f"\n{Fore.YELLOW}{'─' * 80}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{Style.BRIGHT}SUMMARY PREVIEW{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'─' * 80}{Style.RESET_ALL}\n")

        # Clean and truncate summary
        preview = summary.strip()
        if len(preview) > 800:
            preview = preview[:800] + "..."

        # Print with subtle coloring
        for line in preview.split("\n"):
            if line.startswith("#"):
                print(f"{Fore.YELLOW}{Style.BRIGHT}{line}{Style.RESET_ALL}")
            elif line.startswith("**") or line.startswith("- **"):
                print(f"{Fore.WHITE}{line}{Style.RESET_ALL}")
            else:
                print(line)

    print(f"\n{Fore.YELLOW}{'─' * 80}{Style.RESET_ALL}\n")
