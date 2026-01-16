#!/usr/bin/env python3
"""
Example script demonstrating multi-agent functionality in ReasonLoop
This script shows how different AI models are used for different roles
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()  # Load .env file
except ImportError:
    pass  # python-dotenv not installed, environment variables will still work

from abilities.text_completion import text_completion_ability, stream_text_completion
from config.settings import get_model_for_provider, get_setting


def demonstrate_multi_agent_roles():
    """Demonstrate different AI models being used for different roles"""
    print("=" * 70)
    print("ReasonLoop Multi-Agent Demonstration")
    print("=" * 70)
    print()

    # Display current configuration
    provider = get_setting("LLM_PROVIDER", "xai")
    print(f"Current Model Configuration (Provider: {provider}):")
    print(f"  Orchestrator: {get_model_for_provider(provider, 'orchestrator')}")
    print(f"  Planner:      {get_model_for_provider(provider, 'planner')}")
    print(f"  Executor:     {get_model_for_provider(provider, 'executor')}")
    print(f"  Reviewer:     {get_model_for_provider(provider, 'reviewer')}")
    print()

    # Example scenarios for each role
    scenarios = {
        "orchestrator": {
            "prompt": "You are coordinating a team project. Briefly explain how you would delegate tasks for creating a marketing campaign.",
            "description": "Coordination and delegation",
        },
        "planner": {
            "prompt": "Create a high-level plan for launching a new product. Provide 3-4 main phases with key objectives.",
            "description": "Strategic planning",
        },
        "executor": {
            "prompt": "Write a compelling product description for a smart water bottle that tracks hydration levels.",
            "description": "Content creation/execution",
        },
        "reviewer": {
            "prompt": "Review this marketing copy and provide constructive feedback: 'Our product is the best! Buy it now for amazing results!'",
            "description": "Quality review and analysis",
        },
    }

    print("Testing each role with appropriate tasks:")
    print("-" * 50)

    for role, scenario in scenarios.items():
        provider = get_setting("LLM_PROVIDER", "xai")
        model = get_model_for_provider(provider, role)
        print(f"\n🤖 {role.upper()} ({model})")
        print(f"Task: {scenario['description']}")
        print(f"Prompt: {scenario['prompt'][:80]}...")
        print()

        try:
            # Call the text completion with specific role
            response = text_completion_ability(scenario["prompt"], role=role)

            # Display the response (truncated for readability)
            response_preview = (
                response[:300] + "..." if len(response) > 300 else response
            )
            print(f"Response: {response_preview}")

        except Exception as e:
            print(f"❌ Error: {e}")

        print("-" * 50)

    print("\n✅ Multi-agent demonstration completed!")
    print(
        "\nNote: Each role uses a different model as configured in your .env file."
    )
    print(
        "The system automatically selects the appropriate model based on the task context."
    )


def show_role_selection_logic():
    """Demonstrate how the system determines which role to use for different tasks"""
    print("\n" + "=" * 70)
    print("Role Selection Logic Demonstration")
    print("=" * 70)
    print()

    # Import the task manager to use its role determination logic
    from core.task_manager import TaskManager
    from models.task import Task

    # Create a dummy task manager instance
    task_manager = TaskManager("Demo objective")

    # Example tasks that would trigger different roles
    example_tasks = [
        "Create a comprehensive marketing strategy for the new product",
        "Analyze the performance metrics and provide insights",
        "Generate compelling copy for the landing page",
        "Review and validate the final report before submission",
        "Coordinate the development timeline across teams",
        "Execute the data migration process",
    ]

    print("Example task assignments:")
    print("-" * 40)

    for i, task_description in enumerate(example_tasks, 1):
        # Create a mock task object
        mock_task = Task(
            id=i,
            description=task_description,
            ability="text-completion",
            dependent_task_ids=[],
            status="incomplete",
        )

        # Determine the role
        role = task_manager._determine_task_role(mock_task)
        provider = get_setting("LLM_PROVIDER", "xai")
        model = get_model_for_provider(provider, role)

        print(f"{i}. Task: {task_description}")
        print(f"   → Role: {role.upper()}")
        print(f"   → Model: {model}")
        print()


def test_llm_connection():
    """Test if configured LLM service is running and models are available"""
    print("=" * 70)
    print("LLM Connection Test")
    print("=" * 70)
    print()

    provider = get_setting("LLM_PROVIDER", "zai")
    print(f"Testing {provider} provider...")

    # Test basic connectivity
    try:
        test_prompt = (
            "Hello! Please respond with 'Connection successful' if you can read this."
        )
        response = text_completion_ability(test_prompt, role="orchestrator")

        if response and "error" not in response.lower():
            print(f"✅ {provider} connection successful!")
            print(f"Test response: {response[:100]}...")
        else:
            print(f"⚠️  {provider} responded but there might be issues:")
            print(f"Response: {response}")

    except Exception as e:
        print(f"❌ {provider} connection failed:")
        print(f"Error: {e}")
        print("\nTroubleshooting steps:")
        if provider.lower() == "xai":
            print("1. Check your XAI_API_KEY in .env file")
            print("2. Verify your X.AI account balance")
            print("3. Confirm XAI_API_URL is correct")
        elif provider.lower() == "zai":
            print("1. Check your ZAI_API_KEY in .env file")
            print("2. Verify your Z.ai account balance")
            print("3. Confirm ZAI_BASE_URL is correct")
        elif provider.lower() == "ollama":
            print("1. Make sure Ollama is running: ollama serve")
            print("2. Check if your models are available: ollama list")
            print("3. Verify your .env configuration")
        elif provider.lower() == "openai":
            print("1. Check your OPENAI_API_KEY in .env file")
            print("2. Verify your OpenAI account balance")
        elif provider.lower() == "anthropic":
            print("1. Check your ANTHROPIC_API_KEY in .env file")
            print("2. Verify your Anthropic account balance")

    print()


def main():
    """Run the multi-agent demonstration"""
    print("Starting ReasonLoop Multi-Agent System Demo...")
    print()

    # Check if we're in dry-run mode
    if "--dry-run" in sys.argv:
        print("🔍 DRY RUN MODE - No actual API calls will be made")
        show_role_selection_logic()
        return

    # Test LLM connection first
    if "--skip-connection-test" not in sys.argv:
        test_llm_connection()

    # Show role selection logic
    show_role_selection_logic()

    # Run the main demonstration
    if "--skip-demo" not in sys.argv:
        demonstrate_multi_agent_roles()

    print("\n" + "=" * 70)
    print(
        "Demo completed! Your ReasonLoop system is configured for multi-agent operation."
    )
    print("=" * 70)


if __name__ == "__main__":
    main()
