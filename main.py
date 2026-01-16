"""
ReasonLoop - A modular AI agent system with clean, straightforward error handling
"""

import argparse
import logging
import sys
import time
from datetime import datetime

from config.logging_config import setup_logging
from config.settings import get_setting, update_setting, get_model_for_provider
from core.execution_loop import run_execution_loop
from abilities.ability_registry import list_abilities
from utils.metrics import MetricsManager
from utils.llm_utils import test_llm_service

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class ApplicationConfig:
    """Configuration from command line arguments"""

    def __init__(self, args):
        self.objective = args.objective or get_setting("DEFAULT_OBJECTIVE")
        self.template = args.template
        self.model = args.model
        self.verbose = args.verbose
        self.list_abilities = args.list_abilities
        self.provider = get_setting("LLM_PROVIDER", "xai").lower()


class ReasonLoopCLI:
    """Clean CLI interface for ReasonLoop"""

    def __init__(self, config: ApplicationConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.metrics = MetricsManager()
        self.session_id = None

    def _print_banner(self):
        """Display welcome banner"""
        print("\n" + "=" * 80)
        print(f"ReasonLoop v0.1.0 - Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80 + "\n")

    def _print_config(self):
        """Display current configuration"""
        model = get_model_for_provider(self.config.provider, None)
        print(f"Provider: {self.config.provider}")
        print(f"Model: {model}")
        print(f"Template: {self.config.template}")
        print(f"Objective: {self.config.objective}")
        print("-" * 80 + "\n")

    async def _list_abilities(self) -> int:
        """List all available abilities"""
        abilities = list_abilities()
        print("Available abilities:")
        for name in abilities:
            print(f"  - {name}")
        return 0

    def _test_llm_connection(self) -> bool:
        """Test LLM API connection before execution"""
        print("Testing LLM API connection...")
        success, message = test_llm_service()

        if success:
            print(f"✓ {message}\n")
            return True
        else:
            print(f"✗ LLM API Test Failed: {message}")
            print("\nPlease check:")
            provider = self.config.provider.upper()
            print(f"  1. {provider}_API_KEY is set in .env file")
            print(f"  2. API key is valid and not expired")
            print(f"  3. Account has sufficient credits/balance")
            print(f"  4. Network connection is working\n")
            return False

    async def _execute_objectives(self) -> bool:
        """Execute the main objective"""
        self._print_config()

        # Test LLM connection before starting
        if not self._test_llm_connection():
            return False

        start_time = time.time()
        result_file = run_execution_loop(self.config.objective)
        end_time = time.time()

        # Display results
        elapsed = end_time - start_time
        if result_file:
            print(f"\n✓ Execution completed in {elapsed:.2f} seconds")
            print(f"\n📄 Results saved to: {result_file}")
        else:
            print(f"\n✗ Execution failed after {elapsed:.2f} seconds")

        # Save metrics
        self.metrics.save_session()
        print(f"Metrics saved to logs/ directory")

        return bool(result_file)

    async def run(self) -> int:
        """Main execution flow"""
        self.session_id = self.metrics.start_session()
        self._print_banner()

        if self.config.list_abilities:
            return await self._list_abilities()

        if not self.config.objective:
            print("❌ Error: No objective provided")
            print("Use --objective to specify what you want to achieve")
            return 1

        # Apply command line model override
        if self.config.model:
            model_key = f"{self.config.provider.upper()}_MODEL"
            update_setting(model_key, self.config.model)
            self.logger.info(f"Using model: {self.config.model}")

        # Apply template
        if self.config.template:
            update_setting("PROMPT_TEMPLATE", self.config.template)
            self.logger.info(f"Using template: {self.config.template}")

        # Execute objectives
        success = await self._execute_objectives()
        return 0 if success else 1


class ReasonLoopApplication:
    """Main application orchestrator"""

    @staticmethod
    def parse_args():
        """Parse command line arguments"""
        parser = argparse.ArgumentParser(
            description="ReasonLoop - A modular AI agent system",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python main.py -o "Analyze website traffic patterns"
  python main.py -o "Create marketing report" -t marketing_insights
  python main.py -l  # List available abilities
            """
        )

        parser.add_argument(
            "--objective", "-o",
            type=str,
            help="The objective to achieve"
        )
        parser.add_argument(
            "--template", "-t",
            type=str,
            default="default_tasks",
            help="Prompt template to use"
        )
        parser.add_argument(
            "--model", "-m",
            type=str,
            help="LLM model to use (overrides .env setting)"
        )
        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Enable verbose logging"
        )
        parser.add_argument(
            "--list-abilities", "-l",
            action="store_true",
            help="List available abilities and exit"
        )

        return parser.parse_args()

    @staticmethod
    def setup_logging(verbose: bool):
        """Configure logging"""
        log_level = logging.DEBUG if verbose else logging.INFO
        setup_logging(log_level)

    @staticmethod
    async def run():
        """Run the application"""
        # Parse arguments
        args = ReasonLoopApplication.parse_args()
        config = ApplicationConfig(args)

        # Setup logging
        ReasonLoopApplication.setup_logging(config.verbose)

        # Run CLI
        cli = ReasonLoopCLI(config)
        return await cli.run()


def main():
    """Entry point"""
    import asyncio

    exit_code = asyncio.run(ReasonLoopApplication.run())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
