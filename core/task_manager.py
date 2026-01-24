"""
Task manager for creating, validating, and executing tasks
"""

import logging
from typing import List, Optional

from abilities.ability_registry import execute_ability
from config.settings import get_setting
from models.result import Result
from models.task import Task
from utils.agent_loader import get_prompt_template
from utils.json_parser import extract_json_from_text
from utils.prompt_logger import log_prompt

logger = logging.getLogger(__name__)


class TaskManager:
    """Manages tasks in the system"""

    def __init__(self, objective: str):
        self.tasks: List[Task] = []
        self.session_summary = ""
        self.objective = objective

    def create_initial_tasks(self) -> List[Task]:
        """Create the initial task list using AI"""
        # Import colors
        try:
            from colorama import Fore, Style
        except ImportError:

            class Fore:
                CYAN = ""

            class Style:
                RESET_ALL = ""

        print(f"{Fore.CYAN}Creating task plan...{Style.RESET_ALL}")
        logger.debug("Creating initial task list")

        template_name = get_setting("PROMPT_TEMPLATE", "default_tasks")
        prompt = get_prompt_template(template_name, objective=self.objective)

        response = execute_ability("text-completion", prompt, task_id=0, role="planner")

        log_prompt(
            prompt=prompt,
            response=response,
            template_name=template_name,
            ability="text-completion",
            task_id=0,
            metadata={"objective": self.objective},
        )

        json_data = extract_json_from_text(response)
        if not json_data:
            logger.error("No valid JSON found in response")
            return []

        self.tasks = [Task.from_dict(item) for item in json_data]
        logger.debug(f"Created {len(self.tasks)} tasks")
        return self.tasks

    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        """Find a task by its ID"""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def find_next_task(self) -> Optional[Task]:
        """Find the next executable task"""
        for task in self.tasks:
            if task.status == "incomplete":
                # Check dependencies
                can_execute = True
                for dep_id in task.dependent_task_ids:
                    dep_task = self.get_task_by_id(dep_id)
                    if not dep_task or dep_task.status != "complete":
                        can_execute = False
                        break

                if can_execute:
                    return task
        return None

    def execute_task(self, task: Task) -> Result:
        """Execute a task and return the result"""
        # Import colors
        try:
            from colorama import Fore, Style
        except ImportError:

            class Fore:
                CYAN = GREEN = YELLOW = BLUE = ""

            class Style:
                BRIGHT = RESET_ALL = ""

        # Get task description
        task_desc = getattr(
            task, "description", getattr(task, "task", f"Task #{task.id}")
        )

        # Truncate long descriptions for console
        display_desc = task_desc if len(task_desc) <= 100 else task_desc[:97] + "..."

        print(
            f"\n{Fore.YELLOW}▶ Executing Task #{task.id}{Style.RESET_ALL} [{Fore.WHITE}{task.ability}{Style.RESET_ALL}]"
        )
        print(f"  {display_desc}\n")

        logger.debug(f"Executing task #{task.id}: {task_desc}")

        # Prepare context from dependencies
        context = ""
        for dep_id in task.dependent_task_ids:
            dep_task = self.get_task_by_id(dep_id)
            if dep_task and dep_task.output:
                context += (
                    f"\n\nOutput from task #{dep_id}:\n{dep_task.output[:500]}..."
                )

        # Build prompt
        task_prompt = f"Complete this task: {task_desc}\nObjective: {self.objective}"
        if context:
            task_prompt += f"\n\nPrevious outputs:{context}"

        # Execute ability
        if task.ability == "text-completion":
            role = self._determine_role(task_desc)
            output = execute_ability(
                task.ability, task_prompt, task_id=task.id, role=role
            )
        else:
            output = execute_ability(task.ability, task_desc, task_id=task.id)

        # Log execution is handled by execute_ability in ability_registry

        # Update task
        task.mark_complete(output)
        self.session_summary += f"\n\nTask {task.id} - {task_desc}:\n{output}"

        # Import colors for completion message
        try:
            from colorama import Fore, Style
        except ImportError:

            class Fore:
                GREEN = ""

            class Style:
                RESET_ALL = ""

        print(f"{Fore.GREEN}✓ Task #{task.id} completed{Style.RESET_ALL}\n")
        logger.debug(f"Task #{task.id} completed")
        return Result(task_id=task.id, content=output, success=True)

    def print_task_list(self) -> None:
        """Print the current task list in a readable format"""
        # Import colors
        try:
            from colorama import Fore, Style
        except ImportError:

            class Fore:
                CYAN = GREEN = YELLOW = RED = BLUE = ""

            class Style:
                BRIGHT = RESET_ALL = ""

        print(f"\n{Fore.YELLOW}{'─' * 80}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{Style.BRIGHT}TASK LIST{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'─' * 80}{Style.RESET_ALL}\n")

        for task in self.tasks:
            # Status indicator
            if task.status.value == "complete":
                status_icon = f"{Fore.GREEN}✓{Style.RESET_ALL}"
            elif task.status.value == "incomplete":
                status_icon = f"{Fore.YELLOW}○{Style.RESET_ALL}"
            else:
                status_icon = f"{Fore.RED}✗{Style.RESET_ALL}"

            # Task description
            display_desc = task._additional_attributes.get("insight", task.description)

            # Truncate long descriptions
            if len(display_desc) > 120:
                display_desc = display_desc[:117] + "..."

            # Print task header
            print(
                f"{status_icon} {Fore.YELLOW}Task #{task.id}{Style.RESET_ALL} [{Fore.WHITE}{task.ability}{Style.RESET_ALL}]"
            )
            print(f"  {display_desc}")

            # Print dependencies if any
            if task.dependent_task_ids:
                deps = ", ".join([f"#{d}" for d in task.dependent_task_ids])
                print(f"  {Fore.YELLOW}Depends on:{Style.RESET_ALL} {deps}")

            print()  # Blank line between tasks

        print(f"{Fore.CYAN}{'─' * 80}{Style.RESET_ALL}\n")

    def get_session_summary(self) -> str:
        """Get the current session summary"""
        return self.session_summary

    def _determine_role(self, task_desc: str) -> str:
        """Determine AI role based on task description"""
        task_lower = task_desc.lower()

        if any(k in task_lower for k in ["plan", "design", "outline", "structure"]):
            return "planner"
        elif any(k in task_lower for k in ["review", "analyze", "evaluate", "check"]):
            return "reviewer"
        elif any(
            k in task_lower for k in ["execute", "implement", "generate", "write"]
        ):
            return "executor"
        else:
            return "orchestrator"
