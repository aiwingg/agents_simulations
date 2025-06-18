#!/usr/bin/env python3
"""
Test script for verifying progress tracking improvements
"""

import asyncio
import json
import time
from src.batch_processor import BatchProcessor
from src.config import Config

async def test_progress_tracking():
    """Test the improved progress tracking with a small batch"""
    
    # Create simple test scenarios
    test_scenarios = [
        {
            "name": "test_scenario_1",
            "variables": {
                "CURRENT_DATE": "2024-01-15",
                "CLIENT_NAME": "Test Client 1",
                "LOCATION": "Test Location 1"
            }
        },
        {
            "name": "test_scenario_2", 
            "variables": {
                "CURRENT_DATE": "2024-01-15",
                "CLIENT_NAME": "Test Client 2",
                "LOCATION": "Test Location 2"
            }
        },
        {
            "name": "test_scenario_3",
            "variables": {
                "CURRENT_DATE": "2024-01-15",
                "CLIENT_NAME": "Test Client 3",
                "LOCATION": "Test Location 3"
            }
        }
    ]
    
    # Initialize batch processor
    processor = BatchProcessor(Config.OPENAI_API_KEY, concurrency=2)
    
    # Create batch job
    batch_id = processor.create_batch_job(test_scenarios, use_tools=False)
    print(f"Created batch: {batch_id}")
    
    # Monitor progress
    async def progress_monitor():
        """Monitor and print progress updates"""
        for i in range(60):  # Monitor for up to 60 seconds
            status = processor.get_batch_status(batch_id)
            if status:
                print(f"Progress: {status['progress']:.2f}% | "
                      f"Stage: {status['current_stage']} | "
                      f"Active: {status['scenarios_in_progress']} | "
                      f"Completed: {status['completed_scenarios']}/{status['total_scenarios']}")
                
                if status['status'] in ['completed', 'failed']:
                    print(f"Batch {status['status']}!")
                    break
            
            await asyncio.sleep(1)
    
    # Start batch and monitor progress concurrently
    batch_task = asyncio.create_task(processor.run_batch(batch_id))
    monitor_task = asyncio.create_task(progress_monitor())
    
    # Wait for completion
    try:
        await asyncio.gather(batch_task, monitor_task)
        print("Test completed successfully!")
    except Exception as e:
        print(f"Test failed: {e}")
    
    # Final status
    final_status = processor.get_batch_status(batch_id)
    if final_status:
        print(f"\nFinal Status:")
        print(json.dumps(final_status, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(test_progress_tracking()) 