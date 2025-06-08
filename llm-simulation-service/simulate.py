#!/usr/bin/env python3
"""
CLI interface for LLM Simulation Service
Usage: python simulate.py <command> [options]
"""
import argparse
import asyncio
import json
import sys
import os
import time
from typing import Dict, List, Any, Optional
import requests
from src.config import Config
from src.batch_processor import BatchProcessor
from src.conversation_engine import ConversationEngine
from src.evaluator import ConversationEvaluator
from src.openai_wrapper import OpenAIWrapper
from src.result_storage import ResultStorage
from src.logging_utils import get_logger

class SimulateCLI:
    """Command-line interface for simulation service"""
    
    def __init__(self):
        self.logger = get_logger()
        self.result_storage = ResultStorage()
    
    def load_scenarios_from_file(self, filepath: str) -> List[Dict[str, Any]]:
        """Load scenarios from JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                scenarios = json.load(f)
            
            if not isinstance(scenarios, list):
                raise ValueError("Scenarios file must contain a JSON array")
            
            return scenarios
            
        except Exception as e:
            print(f"Error loading scenarios from {filepath}: {e}")
            sys.exit(1)
    
    def run_batch_local(self, scenarios_file: str, output_dir: Optional[str] = None) -> str:
        """Run batch simulation locally (not via REST API)"""
        
        # Validate configuration
        try:
            Config.validate()
        except ValueError as e:
            print(f"Configuration error: {e}")
            print("Please set the OPENAI_API_KEY environment variable")
            sys.exit(1)
        
        # Load scenarios
        scenarios = self.load_scenarios_from_file(scenarios_file)
        print(f"Loaded {len(scenarios)} scenarios from {scenarios_file}")
        
        # Create batch processor
        processor = BatchProcessor(Config.OPENAI_API_KEY, Config.CONCURRENCY)
        batch_id = processor.create_batch_job(scenarios)
        
        print(f"Created batch job: {batch_id}")
        print(f"Running with concurrency: {Config.CONCURRENCY}")
        print("Starting simulation...")
        
        # Progress callback
        def progress_callback(batch_id: str, completed: int):
            total = len(scenarios)
            percentage = (completed / total) * 100
            print(f"Progress: {completed}/{total} ({percentage:.1f}%)")
        
        # Run batch
        async def run_async():
            return await processor.run_batch(batch_id, progress_callback)
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(run_async())
            
            print(f"\nBatch completed!")
            print(f"Status: {result['status']}")
            print(f"Successful scenarios: {result['successful_scenarios']}")
            print(f"Failed scenarios: {result['failed_scenarios']}")
            print(f"Duration: {result['duration_seconds']:.1f} seconds")
            
            # Save results
            results = result['results']
            
            # Determine output directory
            if output_dir is None:
                output_dir = Config.RESULTS_DIR
            
            # Save in both formats
            ndjson_path = self.result_storage.save_batch_results_ndjson(batch_id, results)
            csv_path = self.result_storage.save_batch_results_csv(batch_id, results)
            
            # Generate and save summary
            summary = self.result_storage.generate_summary_report(batch_id, results)
            summary_path = self.result_storage.save_summary_report(summary)
            
            print(f"\nResults saved:")
            print(f"  NDJSON: {ndjson_path}")
            print(f"  CSV: {csv_path}")
            print(f"  Summary: {summary_path}")
            
            # Print quick summary
            scores = [r.get('score', 1) for r in results]
            if scores:
                avg_score = sum(scores) / len(scores)
                print(f"\nQuick Summary:")
                print(f"  Average score: {avg_score:.2f}")
                score_dist = {s: scores.count(s) for s in [1, 2, 3]}
                print(f"  Score distribution: {score_dist}")
            
            return batch_id
            
        except Exception as e:
            print(f"Batch execution failed: {e}")
            sys.exit(1)
        finally:
            loop.close()
    
    def run_single_scenario(self, scenario_file: str, scenario_index: int = 0, stream: bool = True):
        """Run a single scenario with optional streaming output"""
        
        # Validate configuration
        try:
            Config.validate()
        except ValueError as e:
            print(f"Configuration error: {e}")
            sys.exit(1)
        
        # Load scenarios
        scenarios = self.load_scenarios_from_file(scenario_file)
        
        if scenario_index >= len(scenarios):
            print(f"Error: Scenario index {scenario_index} not found (file has {len(scenarios)} scenarios)")
            sys.exit(1)
        
        scenario = scenarios[scenario_index]
        scenario_name = scenario.get('name', f'scenario_{scenario_index}')
        
        print(f"Running single scenario: {scenario_name}")
        if stream:
            print("Streaming mode enabled - conversation will be displayed in real-time")
        print("-" * 60)
        
        # Create components
        openai_wrapper = OpenAIWrapper(Config.OPENAI_API_KEY)
        conversation_engine = ConversationEngine(openai_wrapper)
        evaluator = ConversationEvaluator(openai_wrapper)
        
        # Run conversation
        async def run_conversation():
            result = await conversation_engine.run_conversation(scenario)
            
            if stream and result.get('status') == 'completed':
                print("\n=== CONVERSATION ===")
                for entry in result.get('conversation_history', []):
                    speaker = "AGENT" if entry['speaker'] == 'agent' else "CLIENT"
                    print(f"\n{speaker}: {entry['content']}")
                
                print("\n" + "=" * 60)
            
            return result
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            conversation_result = loop.run_until_complete(run_conversation())
            
            if conversation_result.get('status') == 'completed':
                print(f"Conversation completed successfully!")
                print(f"Total turns: {conversation_result.get('total_turns')}")
                print(f"Duration: {conversation_result.get('duration_seconds', 0):.1f} seconds")
                
                # Evaluate conversation
                print("\nEvaluating conversation...")
                evaluation_result = loop.run_until_complete(evaluator.evaluate_conversation(conversation_result))
                
                print(f"\n=== EVALUATION ===")
                print(f"Score: {evaluation_result.get('score')}/3")
                print(f"Comment: {evaluation_result.get('comment')}")
                
            else:
                print(f"Conversation failed: {conversation_result.get('error')}")
                sys.exit(1)
                
        except Exception as e:
            print(f"Single scenario execution failed: {e}")
            sys.exit(1)
        finally:
            loop.close()
    
    def get_batch_status_via_api(self, batch_id: str, api_url: str = "http://localhost:5000"):
        """Get batch status via REST API"""
        try:
            response = requests.get(f"{api_url}/api/batches/{batch_id}")
            
            if response.status_code == 200:
                status = response.json()
                
                print(f"Batch ID: {batch_id}")
                print(f"Status: {status['status']}")
                print(f"Progress: {status['progress']:.1f}%")
                print(f"Total scenarios: {status['total_scenarios']}")
                print(f"Completed: {status['completed_scenarios']}")
                print(f"Failed: {status['failed_scenarios']}")
                print(f"Created: {status['created_at']}")
                
                if status.get('started_at'):
                    print(f"Started: {status['started_at']}")
                
                if status.get('completed_at'):
                    print(f"Completed: {status['completed_at']}")
                
                if status.get('error_message'):
                    print(f"Error: {status['error_message']}")
                
            elif response.status_code == 404:
                print(f"Batch {batch_id} not found")
                sys.exit(1)
            else:
                print(f"API error: {response.status_code} - {response.text}")
                sys.exit(1)
                
        except requests.exceptions.ConnectionError:
            print(f"Cannot connect to API at {api_url}")
            print("Make sure the service is running")
            sys.exit(1)
        except Exception as e:
            print(f"Error getting batch status: {e}")
            sys.exit(1)
    
    def fetch_batch_results_via_api(self, batch_id: str, output_file: Optional[str] = None, 
                                  format_type: str = "json", api_url: str = "http://localhost:5000"):
        """Fetch batch results via REST API"""
        try:
            params = {'format': format_type} if format_type != 'json' else {}
            response = requests.get(f"{api_url}/api/batches/{batch_id}/results", params=params)
            
            if response.status_code == 200:
                if format_type in ['csv', 'ndjson']:
                    # File download
                    if output_file is None:
                        output_file = f"batch_{batch_id}_results.{format_type}"
                    
                    with open(output_file, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"Results saved to: {output_file}")
                    
                else:
                    # JSON response
                    results = response.json()
                    
                    if output_file:
                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump(results, f, ensure_ascii=False, indent=2)
                        print(f"Results saved to: {output_file}")
                    else:
                        print(json.dumps(results, ensure_ascii=False, indent=2))
                
            elif response.status_code == 404:
                print(f"Batch {batch_id} not found")
                sys.exit(1)
            elif response.status_code == 400:
                error_data = response.json()
                print(f"Error: {error_data.get('error')}")
                if 'current_status' in error_data:
                    print(f"Current status: {error_data['current_status']}")
                sys.exit(1)
            else:
                print(f"API error: {response.status_code} - {response.text}")
                sys.exit(1)
                
        except requests.exceptions.ConnectionError:
            print(f"Cannot connect to API at {api_url}")
            print("Make sure the service is running")
            sys.exit(1)
        except Exception as e:
            print(f"Error fetching batch results: {e}")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='LLM Simulation CLI')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run simulation scenarios')
    run_parser.add_argument('scenarios_file', help='Path to scenarios JSON file')
    run_parser.add_argument('--output-dir', help='Output directory for results')
    run_parser.add_argument('--single', type=int, metavar='INDEX', help='Run single scenario by index')
    run_parser.add_argument('--no-stream', action='store_true', help='Disable streaming output for single scenario')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check batch status')
    status_parser.add_argument('batch_id', help='Batch ID to check')
    status_parser.add_argument('--api-url', default='http://localhost:5000', help='API base URL')
    
    # Fetch command
    fetch_parser = subparsers.add_parser('fetch', help='Fetch batch results')
    fetch_parser.add_argument('batch_id', help='Batch ID to fetch')
    fetch_parser.add_argument('--output', help='Output file path')
    fetch_parser.add_argument('--format', choices=['json', 'csv', 'ndjson'], default='json', help='Output format')
    fetch_parser.add_argument('--api-url', default='http://localhost:5000', help='API base URL')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    cli = SimulateCLI()
    
    if args.command == 'run':
        if args.single is not None:
            # Run single scenario
            cli.run_single_scenario(
                args.scenarios_file, 
                args.single, 
                stream=not args.no_stream
            )
        else:
            # Run batch
            cli.run_batch_local(args.scenarios_file, args.output_dir)
    
    elif args.command == 'status':
        cli.get_batch_status_via_api(args.batch_id, args.api_url)
    
    elif args.command == 'fetch':
        cli.fetch_batch_results_via_api(
            args.batch_id, 
            args.output, 
            args.format, 
            args.api_url
        )

if __name__ == '__main__':
    main()

