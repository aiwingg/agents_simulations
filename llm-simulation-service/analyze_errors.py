#!/usr/bin/env python3
"""
Error Analysis Script for LLM Simulation Service
Analyzes error logs to identify common conversation failure patterns
"""
import os
import re
import json
from collections import defaultdict, Counter
from datetime import datetime
from src.config import Config

def analyze_error_logs():
    """Analyze error logs to find patterns in conversation failures"""
    
    # Ensure logs directory exists
    Config.ensure_directories()
    
    if not os.path.exists(Config.LOGS_DIR):
        print(f"Logs directory not found: {Config.LOGS_DIR}")
        return
    
    # Find error log files
    error_files = [f for f in os.listdir(Config.LOGS_DIR) if f.startswith('error_') and f.endswith('.log')]
    
    if not error_files:
        print("No error log files found")
        return
    
    print(f"Found {len(error_files)} error log files")
    
    # Analyze patterns
    error_patterns = defaultdict(int)
    timeout_info = []
    turn_limit_info = []
    api_errors = defaultdict(int)
    conversation_errors = []
    
    for error_file in error_files:
        file_path = os.path.join(Config.LOGS_DIR, error_file)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Parse error lines
            for line in content.split('\n'):
                if not line.strip():
                    continue
                    
                # Count different error types
                if 'timeout' in line.lower():
                    error_patterns['timeout'] += 1
                    # Extract timeout details
                    if 'actual:' in line:
                        match = re.search(r'timeout after (\d+) seconds \(actual: ([\d.]+)s\)', line)
                        if match:
                            expected = int(match.group(1))
                            actual = float(match.group(2))
                            timeout_info.append({'expected': expected, 'actual': actual})
                
                elif 'max turns limit' in line.lower():
                    error_patterns['turn_limit'] += 1
                    # Extract turn limit details
                    match = re.search(r'max turns limit \((\d+)\)', line)
                    if match:
                        max_turns = int(match.group(1))
                        turn_limit_info.append({'max_turns': max_turns})
                
                elif 'openai api' in line.lower():
                    error_patterns['openai_api'] += 1
                    if 'rate limit' in line.lower():
                        api_errors['rate_limit'] += 1
                    elif 'timeout' in line.lower():
                        api_errors['api_timeout'] += 1
                    elif 'quota' in line.lower():
                        api_errors['quota_exceeded'] += 1
                    else:
                        api_errors['other_api_error'] += 1
                
                elif 'conversation failed' in line.lower():
                    error_patterns['conversation_failed'] += 1
                    conversation_errors.append(line)
                
                elif 'tool call failed' in line.lower():
                    error_patterns['tool_failure'] += 1
                
                elif 'missing variable' in line.lower():
                    error_patterns['missing_variable'] += 1
    
    # Print analysis results
    print("\n" + "="*60)
    print("ERROR ANALYSIS RESULTS")
    print("="*60)
    
    print("\n1. ERROR TYPE DISTRIBUTION:")
    for error_type, count in sorted(error_patterns.items(), key=lambda x: x[1], reverse=True):
        print(f"   {error_type.replace('_', ' ').title()}: {count}")
    
    if timeout_info:
        print(f"\n2. TIMEOUT ANALYSIS ({len(timeout_info)} timeouts):")
        avg_timeout = sum(t['actual'] for t in timeout_info) / len(timeout_info)
        max_timeout = max(t['actual'] for t in timeout_info)
        print(f"   Average timeout duration: {avg_timeout:.1f} seconds")
        print(f"   Maximum timeout duration: {max_timeout:.1f} seconds")
        expected_timeouts = Counter(t['expected'] for t in timeout_info)
        print(f"   Timeout limits being hit: {dict(expected_timeouts)}")
    
    if turn_limit_info:
        print(f"\n3. TURN LIMIT ANALYSIS ({len(turn_limit_info)} turn limits):")
        turn_limits = Counter(t['max_turns'] for t in turn_limit_info)
        print(f"   Turn limits being hit: {dict(turn_limits)}")
    
    if api_errors:
        print(f"\n4. OPENAI API ERROR BREAKDOWN ({sum(api_errors.values())} total):")
        for error_type, count in sorted(api_errors.items(), key=lambda x: x[1], reverse=True):
            print(f"   {error_type.replace('_', ' ').title()}: {count}")
    
    if conversation_errors:
        print(f"\n5. CONVERSATION FAILURE EXAMPLES (showing first 3):")
        for i, error in enumerate(conversation_errors[:3]):
            print(f"   {i+1}. {error.strip()}")
    
    # Recommendations
    print(f"\n6. RECOMMENDATIONS:")
    
    total_errors = sum(error_patterns.values())
    if error_patterns.get('timeout', 0) > total_errors * 0.3:
        print("   ⚠️  High timeout rate - consider increasing TIMEOUT_SEC")
    
    if error_patterns.get('turn_limit', 0) > total_errors * 0.2:
        print("   ⚠️  Many conversations hitting turn limits - consider increasing MAX_TURNS")
    
    if api_errors.get('rate_limit', 0) > 0:
        print("   ⚠️  OpenAI rate limiting detected - consider reducing CONCURRENCY")
    
    if api_errors.get('quota_exceeded', 0) > 0:
        print("   ⚠️  OpenAI quota exceeded - check billing/usage limits")
    
    if error_patterns.get('tool_failure', 0) > 0:
        print("   ⚠️  Tool failures detected - check webhook endpoints")
    
    if total_errors == 0:
        print("   ✅ No significant error patterns detected!")
    
    print(f"\nTotal errors analyzed: {total_errors}")
    print(f"Log files analyzed: {len(error_files)}")

if __name__ == '__main__':
    analyze_error_logs() 