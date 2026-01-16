"""
Main execution loop for the application
"""

import logging
import time
from core.task_manager import TaskManager

logger = logging.getLogger(__name__)


def run_execution_loop(objective: str) -> bool:
    """Run the main execution loop"""
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
    logger.info(task_manager.get_session_summary())

    return True
