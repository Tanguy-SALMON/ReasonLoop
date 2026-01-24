"""
Task manager for creating, validating, and executing tasks
"""

import logging
import re
from typing import List, Optional

from colorama import Fore, Style

from abilities.ability_registry import execute_ability
from config.settings import get_setting
from models.result import Result
from models.task import Task
from utils.agent_loader import get_prompt_template
from utils.json_parser import extract_json_from_text
from utils.prompt_logger import log_prompt
from utils.url_normalizer import normalize_url

logger = logging.getLogger(__name__)


class TaskManager:
    """Manages tasks in the system"""

    def __init__(self, objective: str):
        self.tasks: List[Task] = []
        self.session_summary = ""
        self.objective = objective
        self.domain = self._extract_domain()

    def _extract_domain(self) -> Optional[str]:
        """Extract domain from objective URL"""
        match = re.search(r"https?://[^\s,]+", self.objective)
        if match:
            url = match.group(0).rstrip(".,;:)")
            _, domain = normalize_url(url)
            return domain
        return None

    def create_initial_tasks(self) -> List[Task]:
        """Create the initial task list using AI"""
        print(f"{Fore.CYAN}Creating task plan...{Style.RESET_ALL}")

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
            print(f"{Fore.RED}Error: Could not create task plan{Style.RESET_ALL}")
            return []

        self.tasks = [Task.from_dict(item) for item in json_data]
        return self.tasks

    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        """Find a task by its ID"""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def find_next_task(self) -> Optional[Task]:
        """Find the next executable task (incomplete with all dependencies met)"""
        for task in self.tasks:
            if task.status != "incomplete":
                continue
            deps_met = all(
                self.get_task_by_id(dep_id)
                and self.get_task_by_id(dep_id).status == "complete"
                for dep_id in task.dependent_task_ids
            )
            if deps_met:
                return task
        return None

    def execute_task(self, task: Task) -> Result:
        """Execute a task and return the result"""
        task_desc = task.description or f"Task #{task.id}"

        # Show role if present (for multi-agent workflows)
        role = task._additional_attributes.get("role")
        role_str = f" @{Fore.MAGENTA}{role}{Style.RESET_ALL}" if role else ""

        print(
            f"\n{Fore.YELLOW}▶ Task #{task.id}{Style.RESET_ALL} [{Fore.WHITE}{task.ability}{Style.RESET_ALL}]{role_str}"
        )
        # Show full description (wrap at ~75 chars per line, max 3 lines)
        import textwrap

        wrapped = textwrap.wrap(task_desc, width=75)
        for line in wrapped[:3]:
            print(f"  {line}")
        if len(wrapped) > 3:
            print(f"  ...")
        print()

        # Collect dependency outputs
        dep_outputs = [
            self.get_task_by_id(dep_id).output
            for dep_id in task.dependent_task_ids
            if self.get_task_by_id(dep_id) and self.get_task_by_id(dep_id).output
        ]
        full_dep_output = "\n\n".join(dep_outputs)

        # Build context for text-completion
        context = {
            "objective": self.objective,
            "domain": self.domain,
            "task_description": task_desc,
            "dependency_output": full_dep_output,
        }

        # Get role from task if specified (for multi-agent workflows)
        role = task._additional_attributes.get("role")
        output = self._execute_ability(task.ability, context, task.id, role=role)

        task.mark_complete(output)
        self.session_summary += f"\n\nTask {task.id} - {task_desc}:\n{output}"
        print(f"{Fore.GREEN}✓ Task #{task.id} completed{Style.RESET_ALL}\n")

        return Result(task_id=task.id, content=output, success=True)

    def _execute_ability(
        self, ability: str, context: dict, task_id: int, role: Optional[str] = None
    ) -> str:
        """Execute ability with context"""

        # text-completion: build a prompt with task description and dependencies
        if ability == "text-completion":
            prompt = f"Complete this task: {context['task_description']}\nObjective: {context['objective']}"
            if context["dependency_output"]:
                prompt += (
                    f"\n\nPrevious outputs:\n{context['dependency_output'][:4000]}"
                )
            # Use specified role or default to executor
            execution_role = role or "executor"
            return execute_ability(
                ability, prompt, task_id=task_id, role=execution_role
            )

        # All other abilities: pass dependency output (or task description) plus domain
        content = context["dependency_output"] or context["task_description"]
        return execute_ability(
            ability,
            content,
            domain=context["domain"],
            task_id=task_id,
        )

    def print_task_list(self) -> None:
        """Print the current task list"""
        print(f"\n{Fore.YELLOW}{'─' * 80}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{Style.BRIGHT}TASK LIST{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'─' * 80}{Style.RESET_ALL}\n")

        icons = {
            "complete": f"{Fore.GREEN}✓",
            "incomplete": f"{Fore.YELLOW}○",
            "failed": f"{Fore.RED}✗",
        }

        for task in self.tasks:
            icon = icons.get(task.status.value, f"{Fore.RED}?") + Style.RESET_ALL
            desc = task._additional_attributes.get("insight", task.description)
            desc = desc[:117] + "..." if len(desc) > 120 else desc

            # Show role if present (for multi-agent workflows)
            role = task._additional_attributes.get("role")
            role_str = f" @{Fore.MAGENTA}{role}{Style.RESET_ALL}" if role else ""

            print(
                f"{icon} {Fore.YELLOW}Task #{task.id}{Style.RESET_ALL} [{Fore.WHITE}{task.ability}{Style.RESET_ALL}]{role_str}"
            )
            print(f"  {desc}")
            if task.dependent_task_ids:
                print(
                    f"  {Fore.YELLOW}Depends on:{Style.RESET_ALL} {', '.join(f'#{d}' for d in task.dependent_task_ids)}"
                )
            print()

        print(f"{Fore.CYAN}{'─' * 80}{Style.RESET_ALL}\n")

    def get_session_summary(self) -> str:
        return self.session_summary
