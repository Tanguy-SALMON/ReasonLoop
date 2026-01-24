"""
ReasonLoop - A modular AI agent system with clean, straightforward error handling
"""

import argparse
import logging
import sys
import time
from datetime import datetime

from abilities.ability_registry import list_abilities
from config.logging_config import setup_logging
from config.settings import get_model_for_provider, get_setting, update_setting
from core.execution_loop import run_execution_loop
from utils.llm_utils import test_llm_service
from utils.metrics import MetricsManager

# Colors for terminal output
try:
    from colorama import Back, Fore, Style, init

    init(autoreset=True)
    COLORS_ENABLED = True
except ImportError:
    # Fallback if colorama not installed
    class Fore:
        GREEN = CYAN = YELLOW = RED = BLUE = MAGENTA = WHITE = ""

    class Style:
        BRIGHT = RESET_ALL = ""

    COLORS_ENABLED = False

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
        print(f"\n{Fore.CYAN}{'=' * 80}")
        print(
            f"{Fore.CYAN}{Style.BRIGHT}ReasonLoop v0.2.0{Style.RESET_ALL} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")

    def _print_config(self):
        """Display current configuration"""
        model = get_model_for_provider(self.config.provider, None)
        print(f"{Fore.YELLOW}Provider:{Style.RESET_ALL}  {self.config.provider}")
        print(f"{Fore.YELLOW}Model:{Style.RESET_ALL}     {model}")
        if self.config.template:
            print(f"{Fore.YELLOW}Agent:{Style.RESET_ALL}     {self.config.template}")
        print(f"{Fore.YELLOW}Task:{Style.RESET_ALL}      {self.config.objective}")
        print(f"{Fore.CYAN}{'-' * 80}{Style.RESET_ALL}\n")

    async def _list_abilities(self) -> int:
        """List all available abilities"""
        abilities = list_abilities()
        print(f"{Fore.GREEN}Available abilities:{Style.RESET_ALL}")
        for name in abilities:
            print(f"  {Fore.CYAN}•{Style.RESET_ALL} {name}")
        return 0

    def _test_llm_connection(self) -> bool:
        """Test LLM API connection before execution"""
        print(f"{Fore.CYAN}Testing LLM connection...{Style.RESET_ALL}")
        success, message = test_llm_service()

        if success:
            print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}\n")
            return True
        else:
            print(f"{Fore.RED}✗ LLM Connection Failed: {message}{Style.RESET_ALL}")
            print(f"\n{Fore.YELLOW}Please check:{Style.RESET_ALL}")
            provider = self.config.provider.upper()
            print(
                f"  {Fore.CYAN}1.{Style.RESET_ALL} {provider}_API_KEY is set in .env file"
            )
            print(f"  {Fore.CYAN}2.{Style.RESET_ALL} API key is valid and not expired")
            print(
                f"  {Fore.CYAN}3.{Style.RESET_ALL} Account has sufficient credits/balance"
            )
            print(f"  {Fore.CYAN}4.{Style.RESET_ALL} Network connection is working\n")
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
            print(
                f"\n{Fore.GREEN}✓ Execution completed in {elapsed:.2f}s{Style.RESET_ALL}"
            )
            print(f"{Fore.CYAN}📄 Results:{Style.RESET_ALL} {result_file}")
        else:
            print(
                f"\n{Fore.RED}✗ Execution failed after {elapsed:.2f}s{Style.RESET_ALL}"
            )

        # Save metrics
        self.metrics.save_session()
        print(f"{Fore.CYAN}📊 Metrics:{Style.RESET_ALL} logs/metrics/")

        return bool(result_file)

    async def run(self) -> int:
        """Main execution flow"""
        self.session_id = self.metrics.start_session()
        self._print_banner()

        if self.config.list_abilities:
            return await self._list_abilities()

        if not self.config.objective:
            print(f"{Fore.RED}✗ Error: No objective provided{Style.RESET_ALL}")
            print(
                f"{Fore.YELLOW}Use --objective to specify what you want to achieve{Style.RESET_ALL}"
            )
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
            """,
        )

        parser.add_argument(
            "--objective", "-o", type=str, help="The objective to achieve"
        )
        parser.add_argument(
            "--template",
            "-t",
            type=str,
            default="default_tasks",
            help="Prompt template to use",
        )
        parser.add_argument(
            "--model", "-m", type=str, help="LLM model to use (overrides .env setting)"
        )
        parser.add_argument(
            "--verbose", "-v", action="store_true", help="Enable verbose logging"
        )
        parser.add_argument(
            "--list-abilities",
            "-l",
            action="store_true",
            help="List available abilities and exit",
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
