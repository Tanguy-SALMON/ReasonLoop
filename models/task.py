from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Literal
from enum import Enum
import json
from datetime import datetime

class TaskStatus(str, Enum):
    """Valid task status values"""
    INCOMPLETE = "incomplete"
    COMPLETE = "complete"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"

@dataclass
class Task:
    """Represents a task to be executed"""
    id: int
    description: str = "Objective"  # More descriptive name than 'task'
    status: TaskStatus = TaskStatus.INCOMPLETE
    ability: str = "text-completion"
    dependent_task_ids: List[int] = field(default_factory=list)
    output: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Dynamic attributes storage
    _additional_attributes: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate task after initialization"""
        # Convert string status to enum if needed
        if isinstance(self.status, str):
            try:
                self.status = TaskStatus(self.status)
            except ValueError:
                # Default to INCOMPLETE if invalid status
                self.status = TaskStatus.INCOMPLETE
    
    def __getattr__(self, name):
        """Allow access to additional attributes"""
        if name in self._additional_attributes:
            return self._additional_attributes[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create task from dictionary with flexible schema"""
        # Extract known fields
        task_id = data.pop("id")
        description = data.pop("task", data.pop("description", "Objective"))
        status = data.pop("status", TaskStatus.INCOMPLETE)
        ability = data.pop("ability", "text-completion")
        dependent_task_ids = data.pop("dependent_task_ids", [])

        # Handle datetime conversion
        created_at = data.pop("created_at", None)
        if created_at and isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        else:
            created_at = datetime.now()

        completed_at = data.pop("completed_at", None)
        if completed_at and isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at)

        output = data.pop("output", None)
        metadata = data.pop("metadata", {})

        # Create task instance
        task = cls(
            id=task_id,
            description=description,
            status=status,
            ability=ability,
            dependent_task_ids=dependent_task_ids,
            output=output,
            created_at=created_at,
            completed_at=completed_at,
            metadata=metadata
        )

        # Store all remaining fields as additional attributes
        task._additional_attributes = data
        return task

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        result = {
            "id": self.id,
            "task": self.description,  # Keep 'task' for backward compatibility
            "status": self.status.value,  # Convert enum to string
            "ability": self.ability,
            "dependent_task_ids": self.dependent_task_ids,
            "output": self.output,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata
        }

        # Add all additional attributes
        result.update(self._additional_attributes)
        return result

    def __str__(self) -> str:
        """String representation of task"""
        # Use the main description field with fallbacks to dynamic attributes
        display_desc = self._additional_attributes.get("insight", self.description)
        deps = f" (depends on: {self.dependent_task_ids})" if self.dependent_task_ids else ""
        return f"Task #{self.id}: {display_desc} [{self.status.value}] [{self.ability}]{deps}"

    def mark_complete(self, output: str) -> None:
        """Mark task as complete with output"""
        self.status = TaskStatus.COMPLETE
        self.output = output
        self.completed_at = datetime.now()
        
    def mark_failed(self, error_message: str) -> None:
        """Mark task as failed with error message"""
        self.status = TaskStatus.FAILED
        self.output = f"ERROR: {error_message}"
        self.completed_at = datetime.now()
        
    def mark_in_progress(self) -> None:
        """Mark task as in progress"""
        self.status = TaskStatus.IN_PROGRESS

    def to_json(self) -> str:
        """Convert task to JSON string"""
        return json.dumps(self.to_dict(), default=str)