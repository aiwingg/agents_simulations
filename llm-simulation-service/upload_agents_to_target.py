#!/usr/bin/env python3
"""
CLI script for uploading agents to Target AI platform
"""

import os
import sys
import argparse
from typing import List
from dotenv import load_dotenv

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import Config
from src.target_agent_uploader import (
    TargetAgentUploader,
    UploadResult,
    MappingNotFoundError,
    AuthenticationError
)
from src.prompt_specification import PromptSpecificationManager
from src.logging_utils import get_logger


def print_upload_results(results: List[UploadResult]) -> None:
    """Print formatted upload results"""
    print("\n" + "="*60)
    print("UPLOAD RESULTS")
    print("="*60)
    
    successful = []
    failed = []
    
    for result in results:
        if result.success:
            successful.append(result)
        else:
            failed.append(result)
    
    # Print successful uploads
    if successful:
        print(f"\n✅ SUCCESSFUL UPLOADS ({len(successful)}):")
        for result in successful:
            print(f"  • {result.agent_name}")
            if result.response and 'id' in result.response:
                print(f"    ID: {result.response['id']}")
    
    # Print failed uploads
    if failed:
        print(f"\n❌ FAILED UPLOADS ({len(failed)}):")
        for result in failed:
            print(f"  • {result.agent_name}")
            print(f"    Error: {result.error}")
    
    # Print summary
    print(f"\n📊 SUMMARY:")
    print(f"  Total agents: {len(results)}")
    print(f"  Successful: {len(successful)}")
    print(f"  Failed: {len(failed)}")
    
    if failed:
        print(f"\n⚠️  Some uploads failed. Check the errors above and:")
        print(f"  1. Verify agent IDs are set in target_agents_mapping.json")
        print(f"  2. Check TARGET_API_KEY is valid")
        print(f"  3. Ensure tools exist in target_tools_mapping.json")


def validate_environment() -> None:
    """Validate required environment variables"""
    try:
        Config.validate_target_config()
        print("✅ Environment configuration validated")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\nRequired environment variables:")
        print("  - TARGET_API_KEY: Your Target AI API key")
        print("  - TARGET_COMPANY_ID: Your company ID (default: 54)")
        print("  - TARGET_BASE_URL: Target API base URL (default: https://app.targetai.ai)")
        sys.exit(1)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Upload agents to Target AI platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload agents from default prompt specification
  python upload_agents_to_target.py

  # Upload from specific prompt specification
  python upload_agents_to_target.py --spec-name multiagent_prompts

  # Dry run to validate configuration without uploading
  python upload_agents_to_target.py --dry-run

  # Verbose output
  python upload_agents_to_target.py --verbose

Environment Variables:
  TARGET_API_KEY      - Required: Your Target AI API key
  TARGET_COMPANY_ID   - Optional: Company ID (default: 54)
  TARGET_BASE_URL     - Optional: API base URL (default: https://app.targetai.ai)
        """
    )
    
    parser.add_argument(
        "--spec-name",
        default="file_based_prompts",
        help="Name of prompt specification to upload (default: file_based_prompts)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and build payloads without uploading"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--list-specs",
        action="store_true",
        help="List available prompt specifications and exit"
    )

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()
    
    # Initialize logger
    logger = get_logger()
    
    try:
        # Initialize prompt specification manager
        prompt_manager = PromptSpecificationManager()
        
        # Handle --list-specs
        if args.list_specs:
            print("Available prompt specifications:")
            specs = prompt_manager.list_available_specifications()
            for spec in specs:
                print(f"  • {spec['name']}")
                print(f"    Description: {spec['description']}")
                print(f"    Version: {spec['version']}")
                print(f"    Agents: {', '.join(spec['agents'])}")
                print()
            return
        
        print(f"🚀 Target AI Agent Uploader")
        print(f"📋 Specification: {args.spec_name}")
        
        if args.dry_run:
            print("🧪 DRY RUN MODE - No actual uploads will be performed")
        
        # Validate environment
        validate_environment()
        
        # Load prompt specification
        print(f"\n📖 Loading prompt specification: {args.spec_name}")
        try:
            prompt_spec = prompt_manager.load_specification(args.spec_name)
            print(f"✅ Loaded specification with {len(prompt_spec.agents)} agents")
        except FileNotFoundError:
            print(f"❌ Prompt specification not found: {args.spec_name}")
            print("\nAvailable specifications:")
            for spec in prompt_manager.list_available_specifications():
                print(f"  • {spec['name']}")
            sys.exit(1)
        
        # Initialize uploader
        print(f"\n🔧 Initializing Target AI uploader...")
        try:
            uploader = TargetAgentUploader(
                base_url=Config.TARGET_BASE_URL,
                company_id=Config.TARGET_COMPANY_ID,
                api_key=Config.TARGET_API_KEY,
                prompts_dir=Config.PROMPTS_DIR
            )
            print(f"✅ Uploader initialized successfully")
        except MappingNotFoundError as e:
            print(f"❌ Mapping error: {e}")
            print("\nEnsure the following files exist in the prompts directory:")
            print("  • target_tools_mapping.json")
            print("  • target_agents_mapping.json")
            sys.exit(1)
        
        # Filter agents to upload (exclude client and evaluator)
        uploadable_agents = {
            name: spec for name, spec in prompt_spec.agents.items()
            if name not in {"client", "evaluator"}
        }
        
        print(f"\n📋 Agents to upload: {list(uploadable_agents.keys())}")
        
        if args.dry_run:
            print(f"\n🧪 DRY RUN: Validating agent configurations...")
            
            errors = []
            for agent_name, agent_spec in uploadable_agents.items():
                try:
                    # Check if agent has mapping
                    if agent_name not in uploader.agents_mapping:
                        errors.append(f"Agent '{agent_name}' not found in agents mapping")
                        continue
                    
                    agent_id = uploader.agents_mapping[agent_name]
                    if agent_id is None:
                        errors.append(f"Agent '{agent_name}' has null ID in mapping")
                        continue
                    
                    # Try building payload
                    payload = uploader.build_agent_payload(agent_spec, agent_id)
                    
                    if args.verbose:
                        print(f"  ✅ {agent_name}: Payload built successfully")
                        print(f"     Tools: {len(payload['version']['tools'])}")
                    else:
                        print(f"  ✅ {agent_name}")
                    
                except Exception as e:
                    errors.append(f"Agent '{agent_name}': {str(e)}")
                    print(f"  ❌ {agent_name}: {str(e)}")
            
            if errors:
                print(f"\n❌ Validation failed with {len(errors)} errors:")
                for error in errors:
                    print(f"  • {error}")
                sys.exit(1)
            else:
                print(f"\n✅ All agents validated successfully!")
                print(f"Run without --dry-run to perform actual upload.")
            return
        
        # Perform actual upload
        print(f"\n🚀 Starting agent upload...")
        results = uploader.upload_all_agents(prompt_spec)
        
        # Print results
        print_upload_results(results)
        
        # Exit with error code if any uploads failed
        failed_count = sum(1 for r in results if not r.success)
        if failed_count > 0:
            sys.exit(1)
        else:
            print(f"\n🎉 All agents uploaded successfully!")
    
    except AuthenticationError as e:
        print(f"❌ Authentication error: {e}")
        print("Check your TARGET_API_KEY environment variable")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n⚠️ Upload cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 