#!/usr/bin/env python3
"""
Script to read and display conversation logs in readable format
"""
import json
import sys
import os

def read_conversation_log(filename):
    """Read and display conversation log in readable format"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f'=== COMPLETE CONVERSATION LOG: {filename} ===')
        print()
        
        for line in lines:
            if line.strip():
                try:
                    data = json.loads(line.strip())
                    
                    if 'event_type' in data and data['event_type'] == 'conversation_complete':
                        print(f"🏁 CONVERSATION COMPLETE:")
                        print(f"   Total Turns: {data['total_turns']}")
                        print(f"   Score: {data.get('final_score', 'N/A')}")
                        print(f"   Comment: {data.get('evaluator_comment', 'N/A')}")
                        print(f"   Status: {data['status']}")
                        print()
                    else:
                        role = data['role'].upper()
                        turn = data['turn_number']
                        content = data['content']
                        timestamp = data['timestamp']
                        
                        print(f"Turn {turn} - {role}:")
                        print(f"  {content}")
                        
                        if data.get('tool_calls'):
                            print(f"  🔧 TOOL CALLS: {len(data['tool_calls'])} tools used")
                        
                        if data.get('tool_results'):
                            print(f"  📋 TOOL RESULTS: {len(data['tool_results'])} results")
                            
                        print(f"  ⏰ Time: {timestamp}")
                        print()
                except json.JSONDecodeError as e:
                    print(f"Error parsing line: {e}")
                    print(f"Line content: {line}")
                    
    except FileNotFoundError:
        print(f"Log file not found: {filename}")
    except Exception as e:
        print(f"Error reading log file: {e}")

def read_app_log(filename):
    """Read and display app log with tool calls"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f'=== APP LOG WITH TOOL CALLS: {filename} ===')
        print()
        
        for line in lines:
            if 'Tool call:' in line or 'Tool executed:' in line or 'Client ended call:' in line:
                print(line.strip())
                
    except FileNotFoundError:
        print(f"App log file not found: {filename}")
    except Exception as e:
        print(f"Error reading app log file: {e}")

if __name__ == "__main__":
    # Get the latest log files
    logs_dir = "logs"
    
    # Find the most recent conversation log
    conversation_files = [f for f in os.listdir(logs_dir) if f.startswith('conversations_') and f.endswith('.jsonl')]
    if conversation_files:
        latest_conversation = sorted(conversation_files)[-1]
        read_conversation_log(os.path.join(logs_dir, latest_conversation))
        
        # Find corresponding app log
        timestamp = latest_conversation.split('_')[1].split('.')[0]  # Extract timestamp
        app_log = f"app_{timestamp}.log"
        if os.path.exists(os.path.join(logs_dir, app_log)):
            print("\n" + "="*60 + "\n")
            read_app_log(os.path.join(logs_dir, app_log))
    else:
        print("No conversation log files found") 