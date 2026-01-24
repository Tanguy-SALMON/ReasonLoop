"""
Output directory management for organized session-based file storage
Creates timestamped folders for each crawl/analysis session
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class OutputManager:
    """
    Manages organized output directories for web scraping and email generation.

    Structure:
    output/
      ├── domain.com_20260124/      # Date-only, multiple runs same day share folder
      │   ├── screenshots/
      │   ├── emails/
      │   ├── data/
      │   └── summary.md
      └── domain.com_20260125/
          └── ...
    """

    def __init__(
        self, domain: str, base_dir: str = "output", timestamp: Optional[str] = None
    ):
        """
        Initialize output manager for a domain.

        Args:
            domain: Clean domain identifier (e.g., "shiseido.com-us-en")
            base_dir: Base output directory (default: "output")
            timestamp: Optional date string YYYYMMDD (auto-generated if not provided)
        """
        self.domain = domain
        self.base_dir = base_dir
        # Use date-only format so multiple runs on same day share the folder
        self.timestamp = timestamp or datetime.now().strftime("%Y%m%d")

        # Create session folder: output/domain_YYYYMMDD/
        self.session_dir = os.path.join(base_dir, f"{domain}_{self.timestamp}")

        # Subdirectories
        self.screenshots_dir = os.path.join(self.session_dir, "screenshots")
        self.emails_dir = os.path.join(self.session_dir, "emails")
        self.data_dir = os.path.join(self.session_dir, "data")

        logger.info(f"Output session: {self.session_dir}")

    def setup(self) -> str:
        """
        Create all necessary directories.

        Returns:
            Path to session directory
        """
        os.makedirs(self.screenshots_dir, exist_ok=True)
        os.makedirs(self.emails_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)

        logger.info(f"Created output structure in: {self.session_dir}")
        return self.session_dir

    def get_screenshot_path(self, filename: str = None) -> str:
        """Get path for screenshot file"""
        if filename:
            return os.path.join(self.screenshots_dir, filename)
        return self.screenshots_dir

    def get_email_path(self, filename: str) -> str:
        """Get path for email template file"""
        return os.path.join(self.emails_dir, filename)

    def get_data_path(self, filename: str) -> str:
        """Get path for data file (JSON, etc.)"""
        return os.path.join(self.data_dir, filename)

    def get_summary_path(self) -> str:
        """Get path for summary markdown file"""
        return os.path.join(self.session_dir, "summary.md")

    def get_session_path(self, *paths) -> str:
        """Get path relative to session directory"""
        return os.path.join(self.session_dir, *paths)

    def create_summary(
        self,
        url: str,
        pages_crawled: int = 0,
        products_found: int = 0,
        emails_created: int = 0,
        design_system_extracted: bool = False,
        notes: str = "",
        tasks: list = None,
        execution_time: float = 0,
    ) -> str:
        """
        Create a summary.md file with session information.

        Returns:
            Path to created summary file
        """
        summary_path = self.get_summary_path()

        # Build task section if tasks provided
        task_section = ""
        if tasks:
            task_section = "\n## Task Execution\n\n"
            for task in tasks:
                status = task.get("status", "unknown")
                status_icon = (
                    "✓"
                    if status == "complete"
                    else "○"
                    if status == "incomplete"
                    else "✗"
                )
                task_desc = task.get("description", task.get("task", ""))
                # Truncate long descriptions
                if len(task_desc) > 150:
                    task_desc = task_desc[:147] + "..."
                task_section += f"{status_icon} **Task #{task.get('id')}** `[{task.get('ability')}]`\n"
                task_section += f"   {task_desc}\n\n"

        content = f"""# Web Scraping & Email Generation Summary

## Session Information
- **Date**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **Domain**: {self.domain}
- **Source URL**: {url}
- **Execution Time**: {execution_time:.1f}s

## Crawling Results
- **Pages Crawled**: {pages_crawled}
- **Products Found**: {products_found}
- **Design System Extracted**: {"✓ Yes" if design_system_extracted else "✗ No"}

## Generated Content
- **Email Templates Created**: {emails_created}
{task_section}
## File Structure
```
{self.domain}_{self.timestamp}/
├── screenshots/          # Full-page screenshots
├── emails/              # HTML email templates
│   ├── minimalist.html
│   ├── bold.html
│   └── elegant.html
├── data/                # Extracted data
│   ├── design_system.json
│   ├── products.json
│   └── crawl_data.json
└── summary.md           # This file
```

## Notes
{notes if notes else "_No additional notes_"}

---

Generated by ReasonLoop
"""

        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Summary created: {summary_path}")
        return summary_path

    def update_summary_with_tasks(
        self, tasks_data: list, execution_time: float = 0
    ) -> str:
        """
        Update existing summary with task execution details.

        Args:
            tasks_data: List of task dictionaries with id, description, ability, status
            execution_time: Total execution time in seconds

        Returns:
            Path to updated summary file
        """
        import os

        summary_path = self.get_summary_path()

        if not os.path.exists(summary_path):
            logger.warning(f"Summary file not found: {summary_path}")
            return summary_path

        # Read existing summary
        with open(summary_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Update execution time if provided
        if execution_time > 0 and "**Execution Time**:" in content:
            import re

            content = re.sub(
                r"\*\*Execution Time\*\*: [\d.]+s",
                f"**Execution Time**: {execution_time:.1f}s",
                content,
            )

        # Build task section
        task_section = "\n## Task Execution\n\n"
        for task in tasks_data:
            status = task.get("status", "unknown")
            status_icon = (
                "✓" if status == "complete" else "○" if status == "incomplete" else "✗"
            )
            task_desc = task.get("description", task.get("task", ""))
            # Truncate long descriptions
            if len(task_desc) > 150:
                task_desc = task_desc[:147] + "..."
            task_section += (
                f"{status_icon} **Task #{task.get('id')}** `[{task.get('ability')}]`\n"
            )
            task_section += f"   {task_desc}\n\n"

        # Insert task section before "## File Structure"
        if "## File Structure" in content:
            content = content.replace(
                "## File Structure", f"{task_section}## File Structure"
            )
        else:
            # Append before footer
            if "---" in content:
                content = content.replace("---", f"{task_section}\n---")
            else:
                content += f"\n{task_section}"

        # Write updated content
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Summary updated with {len(tasks_data)} tasks")
        return summary_path

    def update_email_count(self, count: int) -> None:
        """Update the email templates count in summary.md"""
        import re

        summary_path = self.get_summary_path()

        if not os.path.exists(summary_path):
            return

        with open(summary_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Update email count
        content = re.sub(
            r"\*\*Email Templates Created\*\*: \d+",
            f"**Email Templates Created**: {count}",
            content,
        )

        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Updated summary: {count} email templates")

    def get_info(self) -> dict:
        """Get session information as dictionary"""
        return {
            "domain": self.domain,
            "timestamp": self.timestamp,
            "session_dir": self.session_dir,
            "screenshots_dir": self.screenshots_dir,
            "emails_dir": self.emails_dir,
            "data_dir": self.data_dir,
        }


# Convenience function for use in abilities
def create_output_session(
    domain: str, timestamp: Optional[str] = None
) -> OutputManager:
    """
    Create and setup an output session.

    Args:
        domain: Clean domain identifier
        timestamp: Optional timestamp (auto-generated if not provided)

    Returns:
        OutputManager instance with directories created
    """
    manager = OutputManager(domain, timestamp=timestamp)
    manager.setup()
    return manager


# Test example
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Example usage
    manager = create_output_session("shiseido.com-us-en")

    print("\nSession Info:")
    for key, value in manager.get_info().items():
        print(f"  {key}: {value}")

    print(f"\nScreenshot path: {manager.get_screenshot_path('homepage.png')}")
    print(f"Email path: {manager.get_email_path('minimalist.html')}")
    print(f"Data path: {manager.get_data_path('design_system.json')}")

    # Create summary
    manager.create_summary(
        url="https://www.shiseido.com/us/en/",
        pages_crawled=5,
        products_found=12,
        emails_created=3,
        design_system_extracted=True,
        notes="Successfully extracted brand colors and typography.",
    )

    print(f"\nSummary created at: {manager.get_summary_path()}")
