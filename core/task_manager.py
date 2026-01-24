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


def _extract_domain_from_url(text: str) -> Optional[str]:
    """Extract clean domain from a URL in text"""
    match = re.search(r"https?://[^\s,]+", text)
    if match:
        url = match.group(0).rstrip(".,;:)")
        _, domain = normalize_url(url)
        return domain
    return None


class TaskManager:
    """Manages tasks in the system"""

    def __init__(self, objective: str):
        self.tasks: List[Task] = []
        self.session_summary = ""
        self.objective = objective

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
            logger.error("Failed to parse task list from LLM response")
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
        display_desc = task_desc[:97] + "..." if len(task_desc) > 100 else task_desc

        print(
            f"\n{Fore.YELLOW}▶ Executing Task #{task.id}{Style.RESET_ALL} [{Fore.WHITE}{task.ability}{Style.RESET_ALL}]"
        )
        print(f"  {display_desc}\n")

        # Collect dependency outputs
        dep_outputs = []
        for dep_id in task.dependent_task_ids:
            dep_task = self.get_task_by_id(dep_id)
            if dep_task and dep_task.output:
                dep_outputs.append(dep_task.output)

        full_dependency_output = "\n\n".join(dep_outputs)
        context = "\n\n".join(
            f"Output from task #{dep_id}:\n{out[:500]}..."
            for dep_id, out in zip(task.dependent_task_ids, dep_outputs)
        )

        # Execute based on ability type
        output = self._execute_ability(task, task_desc, full_dependency_output, context)

        task.mark_complete(output)
        self.session_summary += f"\n\nTask {task.id} - {task_desc}:\n{output}"

        print(f"{Fore.GREEN}✓ Task #{task.id} completed{Style.RESET_ALL}\n")
        return Result(task_id=task.id, content=output, success=True)

    def _execute_ability(
        self, task: Task, task_desc: str, full_dep_output: str, context: str
    ) -> str:
        """Execute the appropriate ability for a task"""
        domain = _extract_domain_from_url(self.objective)

        if task.ability == "text-completion":
            prompt = f"Complete this task: {task_desc}\nObjective: {self.objective}"
            if context:
                prompt += f"\n\nPrevious outputs:{context}"
            return execute_ability(
                task.ability,
                prompt,
                task_id=task.id,
                role=self._determine_role(task_desc),
            )

        if task.ability == "save-email-templates":
            return execute_ability(
                task.ability, full_dep_output.strip(), domain=domain, task_id=task.id
            )

        if task.ability == "email-design":
            campaign_goal = self._extract_campaign_goal(task_desc)
            output_dir = f"output/{domain}/emails" if domain else None
            return execute_ability(
                task.ability,
                full_dep_output.strip(),
                campaign_goal=campaign_goal,
                output_dir=output_dir,
                task_id=task.id,
            )

        return execute_ability(task.ability, task_desc, task_id=task.id)

    def _extract_campaign_goal(self, task_desc: str) -> str:
        """Extract campaign goal from task description"""
        match = re.search(r"campaign goal[:\s]+(.+?)(?:\.|$)", task_desc, re.IGNORECASE)
        return (
            match.group(1).strip()
            if match
            else "Promote products and drive conversions"
        )

    def _determine_role(self, task_desc: str) -> str:
        """Determine AI role based on task description"""
        task_lower = task_desc.lower()

        if any(k in task_lower for k in ["plan", "design", "outline", "structure"]):
            return "planner"
        if any(k in task_lower for k in ["review", "analyze", "evaluate", "check"]):
            return "reviewer"
        if any(k in task_lower for k in ["execute", "implement", "generate", "write"]):
            return "executor"
        return "orchestrator"

    def print_task_list(self) -> None:
        """Print the current task list"""
        print(f"\n{Fore.YELLOW}{'─' * 80}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{Style.BRIGHT}TASK LIST{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'─' * 80}{Style.RESET_ALL}\n")

        status_icons = {
            "complete": f"{Fore.GREEN}✓{Style.RESET_ALL}",
            "incomplete": f"{Fore.YELLOW}○{Style.RESET_ALL}",
            "failed": f"{Fore.RED}✗{Style.RESET_ALL}",
        }

        for task in self.tasks:
            icon = status_icons.get(task.status.value, f"{Fore.RED}?{Style.RESET_ALL}")
            desc = task._additional_attributes.get("insight", task.description)
            desc = desc[:117] + "..." if len(desc) > 120 else desc

            print(
                f"{icon} {Fore.YELLOW}Task #{task.id}{Style.RESET_ALL} [{Fore.WHITE}{task.ability}{Style.RESET_ALL}]"
            )
            print(f"  {desc}")

            if task.dependent_task_ids:
                deps = ", ".join(f"#{d}" for d in task.dependent_task_ids)
                print(f"  {Fore.YELLOW}Depends on:{Style.RESET_ALL} {deps}")
            print()

        print(f"{Fore.CYAN}{'─' * 80}{Style.RESET_ALL}\n")

    def get_session_summary(self) -> str:
        """Get the current session summary"""
        return self.session_summary
