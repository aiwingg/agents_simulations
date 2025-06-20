#!/usr/bin/env python3
"""
CLI for LLM conversation simulation and batch management
"""
import argparse
import asyncio
import json
import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import Config
from src.openai_wrapper import OpenAIWrapper
from src.conversation_engine import ConversationEngine
from src.evaluator import ConversationEvaluator
from src.batch_processor import BatchProcessor
from src.result_storage import ResultStorage
from src.logging_utils import get_logger
from src.prompt_specification import PromptSpecificationManager

def setup_cli_logging():
    """Setup logging for CLI usage"""
    # For CLI, we'll just use a simple logger setup
    # The get_logger() function already sets up the necessary loggers
    pass

async def run_single_scenario(scenario: Dict[str, Any], output_dir: str, stream: bool = True, 
                            prompt_spec_name: str = "default_prompts") -> Dict[str, Any]:
    """Run a single scenario with optional streaming output"""
    
    logger = get_logger()
    openai_wrapper = OpenAIWrapper(Config.OPENAI_API_KEY)
    conversation_engine = ConversationEngine(openai_wrapper, prompt_spec_name)
    evaluator = ConversationEvaluator(openai_wrapper, prompt_spec_name)
    
    scenario_name = scenario.get('name', 'unknown')
    
    if stream:
        print(f"\n=== Running scenario: {scenario_name} ===\n")
    
    # Run conversation
    if stream:
        print("🔄 Starting conversation...")
    
    conversation_result = await conversation_engine.run_conversation_with_tools(scenario)
    
    if stream:
        if conversation_result.get('status') == 'completed':
            print(f"✅ Conversation completed in {conversation_result.get('duration_seconds', 0):.1f}s")
            print(f"📊 Total turns: {conversation_result.get('total_turns', 0)}")
            
            # Display conversation history
            history = conversation_result.get('conversation_history', [])
            for entry in history:
                speaker = "🤖 Agent" if entry['speaker'] == 'agent' else "👤 Client"
                content = entry['content']
                print(f"\n{speaker}: {content}")
                
                # Show tool calls if present
                if 'tool_calls' in entry and entry['tool_calls']:
                    for tool_call in entry['tool_calls']:
                        tool_name = tool_call['function']['name']
                        print(f"  🔧 Tool: {tool_name}")
                
                if 'tool_results' in entry and entry['tool_results']:
                    for result in entry['tool_results']:
                        if isinstance(result, dict) and 'status' in result:
                            print(f"  ↳ Result: {result.get('status', 'unknown')}")
        else:
            print(f"❌ Conversation failed: {conversation_result.get('error', 'unknown error')}")
    
    # Evaluate conversation
    if stream:
        print("\n🔄 Evaluating conversation...")
    
    evaluation_result = await evaluator.evaluate_conversation(conversation_result)
    
    if stream:
        score = evaluation_result.get('score', 0)
        comment = evaluation_result.get('comment', 'No comment')
        print(f"📋 Evaluation Score: {score}/3")
        print(f"💬 Comment: {comment}")
    
    # Combine results
    final_result = {
        **conversation_result,
        'score': evaluation_result.get('score', 0),
        'comment': evaluation_result.get('comment', 'No comment'),
        'evaluation_status': evaluation_result.get('evaluation_status', 'unknown')
    }
    
    # Save results
    result_storage = ResultStorage(output_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"single_{scenario_name}_{timestamp}.json"
    
    result_storage.save_single_result(filename, final_result)
    
    if stream:
        print(f"\n💾 Results saved to: {os.path.join(output_dir, filename)}")
    
    return final_result

async def run_batch_scenarios(scenarios: List[Dict[str, Any]], output_dir: str, 
                            prompt_spec_name: str = "default_prompts") -> Dict[str, Any]:
    """Run multiple scenarios as a batch"""
    
    logger = get_logger()
    batch_processor = BatchProcessor(Config.OPENAI_API_KEY, Config.CONCURRENCY)
    
    print(f"\n=== Running batch of {len(scenarios)} scenarios ===\n")
    print(f"📋 Prompt specification: {prompt_spec_name}")
    print(f"⚡ Concurrency: {Config.CONCURRENCY}")
    print(f"🔧 Using tools: {Config.USE_TOOLS}")
    
    # Create batch job
    batch_id = batch_processor.create_batch_job(
        scenarios=scenarios,
        prompt_version="cli-v1.0",
        prompt_spec_name=prompt_spec_name,
        use_tools=Config.USE_TOOLS
    )
    
    print(f"🆔 Batch ID: {batch_id}")
    
    # Run batch with progress tracking
    def progress_callback(completed: int, total: int):
        percentage = (completed / total) * 100
        print(f"📊 Progress: {completed}/{total} ({percentage:.1f}%)")
    
    try:
        result = await batch_processor.run_batch(batch_id, progress_callback)
        
        if result.get('status') == 'completed':
            print(f"\n✅ Batch completed successfully!")
            print(f"⏱️  Duration: {result.get('duration_seconds', 0):.1f}s")
            print(f"📊 Success rate: {result.get('success_rate', 0):.1%}")
            
            # Save results
            results = result.get('results', [])
            result_storage = ResultStorage(output_dir)
            
            # Save in multiple formats
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            ndjson_file = f"batch_{batch_id}_{timestamp}.ndjson"
            csv_file = f"batch_{batch_id}_{timestamp}.csv"
            json_file = f"batch_{batch_id}_{timestamp}.json"
            
            result_storage.save_batch_results_ndjson(batch_id, results)
            result_storage.save_batch_results_csv(batch_id, results)
            result_storage.save_batch_results_json(batch_id, results)
            
            print(f"\n💾 Results saved:")
            print(f"  📄 NDJSON: {ndjson_file}")
            print(f"  📊 CSV: {csv_file}")
            print(f"  📋 JSON: {json_file}")
            
            # Generate summary
            summary = result_storage.generate_summary_report(batch_id, results)
            summary_file = f"summary_{batch_id}_{timestamp}.json"
            result_storage.save_summary_report(summary)
            print(f"  📈 Summary: {summary_file}")
            
        else:
            print(f"\n❌ Batch failed: {result.get('error', 'unknown error')}")
            
        return result
        
    except Exception as e:
        logger.log_error("Batch execution failed", exception=e)
        print(f"\n❌ Batch execution failed: {str(e)}")
        return {'status': 'failed', 'error': str(e)}

def load_scenarios_from_file(file_path: str) -> List[Dict[str, Any]]:
    """Load scenarios from JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            scenarios = json.load(f)
        
        if not isinstance(scenarios, list):
            raise ValueError("Scenarios file must contain a JSON array")
        
        return scenarios
        
    except Exception as e:
        print(f"❌ Failed to load scenarios from {file_path}: {str(e)}")
        sys.exit(1)

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="LLM Conversation Simulation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all scenarios in batch mode
  python simulate.py run scenarios/sample_scenarios.json
  
  # Run single scenario with streaming
  python simulate.py run scenarios/sample_scenarios.json --single 0
  
  # Use custom prompt specification
  python simulate.py run scenarios/sample_scenarios.json --prompt-spec custom_prompts
  
  # Run batch with custom output directory
  python simulate.py run scenarios/sample_scenarios.json --output-dir ./my_results
  
  # Check batch status
  python simulate.py status 12345678-1234-1234-1234-123456789abc
  
  # Fetch results
  python simulate.py fetch 12345678-1234-1234-1234-123456789abc --format csv
  
  # List available prompt specifications
  python simulate.py prompts list
  
  # Get prompt specification contents
  python simulate.py prompts get default_prompts
  
  # Create new prompt specification
  python simulate.py prompts create my_custom_spec --from-file my_spec.json
  
  # Duplicate existing specification
  python simulate.py prompts duplicate default_prompts my_copy
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run conversation scenarios')
    run_parser.add_argument('scenarios_file', help='Path to scenarios JSON file')
    run_parser.add_argument('--output-dir', default='./results', help='Output directory for results')
    run_parser.add_argument('--single', type=int, metavar='INDEX', help='Run only the scenario at specified index')
    run_parser.add_argument('--no-stream', action='store_true', help='Disable streaming output for single scenarios')
    run_parser.add_argument('--prompt-spec', default='default_prompts', help='Prompt specification name to use')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check batch status')
    status_parser.add_argument('batch_id', help='Batch ID to check')
    status_parser.add_argument('--api-url', default='http://localhost:5000', help='API base URL')
    
    # Fetch command
    fetch_parser = subparsers.add_parser('fetch', help='Fetch batch results')
    fetch_parser.add_argument('batch_id', help='Batch ID to fetch results for')
    fetch_parser.add_argument('--output', help='Output file path')
    fetch_parser.add_argument('--format', choices=['json', 'csv', 'ndjson'], default='json', help='Output format')
    fetch_parser.add_argument('--api-url', default='http://localhost:5000', help='API base URL')
    
    # Prompt specifications command
    prompts_parser = subparsers.add_parser('prompts', help='Manage prompt specifications')
    prompts_subparsers = prompts_parser.add_subparsers(dest='prompts_command', help='Prompt specification commands')
    
    # List prompt specs
    list_prompts_parser = prompts_subparsers.add_parser('list', help='List available prompt specifications')
    
    # Get prompt spec
    get_prompts_parser = prompts_subparsers.add_parser('get', help='Get prompt specification contents')
    get_prompts_parser.add_argument('spec_name', help='Name of the specification to retrieve')
    get_prompts_parser.add_argument('--output', help='Output file path (default: print to console)')
    
    # Create prompt spec
    create_prompts_parser = prompts_subparsers.add_parser('create', help='Create new prompt specification')
    create_prompts_parser.add_argument('spec_name', help='Name for the new specification')
    create_prompts_parser.add_argument('--from-file', required=True, help='JSON file containing the specification')
    
    # Duplicate prompt spec
    duplicate_prompts_parser = prompts_subparsers.add_parser('duplicate', help='Duplicate existing prompt specification')
    duplicate_prompts_parser.add_argument('source_spec', help='Name of the specification to duplicate')
    duplicate_prompts_parser.add_argument('new_spec', help='Name for the duplicated specification')
    duplicate_prompts_parser.add_argument('--display-name', help='Display name for the new specification')
    duplicate_prompts_parser.add_argument('--version', default='1.0.0', help='Version for the new specification')
    duplicate_prompts_parser.add_argument('--description', help='Description for the new specification')
    
    # Delete prompt spec
    delete_prompts_parser = prompts_subparsers.add_parser('delete', help='Delete prompt specification')
    delete_prompts_parser.add_argument('spec_name', help='Name of the specification to delete')
    delete_prompts_parser.add_argument('--force', action='store_true', help='Skip confirmation prompt')
    
    # Validate prompt spec
    validate_prompts_parser = prompts_subparsers.add_parser('validate', help='Validate prompt specification')
    validate_prompts_parser.add_argument('spec_file', help='JSON file containing the specification to validate')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Setup logging
    setup_cli_logging()
    
    if args.command == 'run':
        # Load scenarios
        scenarios = load_scenarios_from_file(args.scenarios_file)
        
        # Create output directory
        os.makedirs(args.output_dir, exist_ok=True)
        
        if args.single is not None:
            # Run single scenario
            if args.single < 0 or args.single >= len(scenarios):
                print(f"❌ Invalid scenario index: {args.single}. Available: 0-{len(scenarios)-1}")
                sys.exit(1)
            
            scenario = scenarios[args.single]
            stream = not args.no_stream
            
            result = asyncio.run(run_single_scenario(
                scenario, 
                args.output_dir, 
                stream=stream,
                prompt_spec_name=args.prompt_spec
            ))
            
            if not stream:
                # Print summary if not streaming
                print(f"Scenario: {scenario.get('name', 'unknown')}")
                print(f"Status: {result.get('status', 'unknown')}")
                print(f"Score: {result.get('score', 0)}/3")
                print(f"Duration: {result.get('duration_seconds', 0):.1f}s")
        
        else:
            # Run batch
            result = asyncio.run(run_batch_scenarios(
                scenarios, 
                args.output_dir,
                prompt_spec_name=args.prompt_spec
            ))
    
    elif args.command == 'status':
        # Check batch status via API
        import requests
        
        try:
            response = requests.get(f"{args.api_url}/api/batches/{args.batch_id}")
            
            if response.status_code == 200:
                status = response.json()
                print(f"Batch ID: {status['batch_id']}")
                print(f"Status: {status['status']}")
                print(f"Progress: {status['progress']:.1f}%")
                print(f"Scenarios: {status['completed_scenarios']}/{status['total_scenarios']}")
                print(f"Prompt Spec: {status.get('prompt_spec_name', 'unknown')}")
                if status.get('created_at'):
                    print(f"Created: {status['created_at']}")
                if status.get('completed_at'):
                    print(f"Completed: {status['completed_at']}")
            elif response.status_code == 404:
                print(f"❌ Batch not found: {args.batch_id}")
            else:
                print(f"❌ API error: {response.status_code}")
                
        except requests.RequestException as e:
            print(f"❌ Failed to connect to API: {str(e)}")
    
    elif args.command == 'fetch':
        # Fetch batch results via API
        import requests
        
        try:
            url = f"{args.api_url}/api/batches/{args.batch_id}/results"
            params = {'format': args.format}
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        if args.format == 'json':
                            json.dump(response.json(), f, ensure_ascii=False, indent=2)
                        else:
                            f.write(response.text)
                    print(f"💾 Results saved to: {args.output}")
                else:
                    print(response.text)
            elif response.status_code == 404:
                print(f"❌ Batch not found: {args.batch_id}")
            else:
                print(f"❌ API error: {response.status_code}")
                
        except requests.RequestException as e:
            print(f"❌ Failed to connect to API: {str(e)}")
    
    elif args.command == 'prompts':
        handle_prompts_command(args)

def handle_prompts_command(args):
    """Handle prompt specification management commands"""
    manager = PromptSpecificationManager()
    
    if not args.prompts_command:
        print("❌ No prompt command specified. Use 'python simulate.py prompts --help' for options.")
        sys.exit(1)
    
    try:
        if args.prompts_command == 'list':
            # List available specifications
            print("📋 Available Prompt Specifications:")
            print("=" * 50)
            
            specs = manager.list_available_specifications()
            
            if not specs:
                print("No prompt specifications found.")
                return
            
            for spec in specs:
                print(f"\n📄 {spec['name']}")
                print(f"   Display Name: {spec['display_name']}")
                print(f"   Version: {spec['version']}")
                print(f"   Description: {spec['description']}")
                print(f"   Agents: {', '.join(spec['agents'])}")
                print(f"   File Size: {spec['file_size']} bytes")
                
                # Format last modified time
                from datetime import datetime
                modified_time = datetime.fromtimestamp(spec['last_modified'])
                print(f"   Last Modified: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        elif args.prompts_command == 'get':
            # Get specification contents
            if not manager.specification_exists(args.spec_name):
                print(f"❌ Prompt specification not found: {args.spec_name}")
                sys.exit(1)
            
            contents = manager.get_specification_contents(args.spec_name)
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(contents, f, ensure_ascii=False, indent=2)
                print(f"💾 Specification saved to: {args.output}")
            else:
                print(json.dumps(contents, ensure_ascii=False, indent=2))
        
        elif args.prompts_command == 'create':
            # Create new specification
            if not os.path.exists(args.from_file):
                print(f"❌ Specification file not found: {args.from_file}")
                sys.exit(1)
            
            with open(args.from_file, 'r', encoding='utf-8') as f:
                spec_data = json.load(f)
            
            if manager.specification_exists(args.spec_name):
                print(f"⚠️  Specification '{args.spec_name}' already exists. Overwriting...")
            
            manager.save_specification(args.spec_name, spec_data)
            print(f"✅ Prompt specification '{args.spec_name}' created successfully!")
        
        elif args.prompts_command == 'duplicate':
            # Duplicate existing specification
            if not manager.specification_exists(args.source_spec):
                print(f"❌ Source specification not found: {args.source_spec}")
                sys.exit(1)
            
            if manager.specification_exists(args.new_spec):
                print(f"❌ Target specification already exists: {args.new_spec}")
                sys.exit(1)
            
            # Get source contents
            source_contents = manager.get_specification_contents(args.source_spec)
            
            # Update metadata
            source_contents['name'] = getattr(args, 'display_name', None) or f"{source_contents['name']} (Copy)"
            source_contents['version'] = args.version
            if args.description:
                source_contents['description'] = args.description
            
            # Save new specification
            manager.save_specification(args.new_spec, source_contents)
            print(f"✅ Specification duplicated from '{args.source_spec}' to '{args.new_spec}'!")
        
        elif args.prompts_command == 'delete':
            # Delete specification
            if not manager.specification_exists(args.spec_name):
                print(f"❌ Prompt specification not found: {args.spec_name}")
                sys.exit(1)
            
            if args.spec_name == 'default_prompts':
                print("❌ Cannot delete the default prompt specification!")
                sys.exit(1)
            
            if not args.force:
                confirmation = input(f"Are you sure you want to delete '{args.spec_name}'? (y/N): ")
                if confirmation.lower() != 'y':
                    print("❌ Deletion cancelled.")
                    sys.exit(0)
            
            manager.delete_specification(args.spec_name)
            print(f"✅ Prompt specification '{args.spec_name}' deleted successfully!")
        
        elif args.prompts_command == 'validate':
            # Validate specification file
            if not os.path.exists(args.spec_file):
                print(f"❌ Specification file not found: {args.spec_file}")
                sys.exit(1)
            
            with open(args.spec_file, 'r', encoding='utf-8') as f:
                spec_data = json.load(f)
            
            # Create temporary specification object for validation
            from src.prompt_specification import SystemPromptSpecification
            try:
                specification = SystemPromptSpecification.from_dict(spec_data)
                issues = manager.validate_specification(specification)
                
                if issues:
                    print("❌ Specification validation failed:")
                    for issue in issues:
                        print(f"   • {issue}")
                    sys.exit(1)
                else:
                    print("✅ Specification is valid!")
                    print(f"   Name: {specification.name}")
                    print(f"   Version: {specification.version}")
                    print(f"   Agents: {', '.join(specification.agents.keys())}")
                    
            except Exception as e:
                print(f"❌ Failed to parse specification: {str(e)}")
                sys.exit(1)
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()

