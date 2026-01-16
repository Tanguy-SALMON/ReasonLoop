"""
Main execution loop for the application
"""

import logging
import time
import os
from datetime import datetime
from core.task_manager import TaskManager

logger = logging.getLogger(__name__)


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

    while True:
        cycle_count += 1
        logger.info(f"CYCLE #{cycle_count} ({completed_tasks}/{total_tasks} completed)")

        next_task = task_manager.find_next_task()
        if not next_task:
            logger.info("All tasks complete")
            break

        result = task_manager.execute_task(next_task)
        if result.success:
            completed_tasks += 1
        else:
            logger.error(f"Task #{next_task.id} failed: {result.error}")

        task_manager.print_task_list()
        time.sleep(0.5)

    execution_time = time.time() - start_time
    logger.info(f"COMPLETE: {completed_tasks}/{total_tasks} tasks in {execution_time:.2f}s")

    # Save results to markdown file
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)

    # Create filename from objective (first 100 chars, sanitized)
    safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in objective[:100])
    safe_name = safe_name.strip().replace(' ', '_')
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

    with open(filename, 'w') as f:
        f.write(markdown_content)

    logger.info(f"Results saved to {filename}")
    logger.info(summary)

    return filename
