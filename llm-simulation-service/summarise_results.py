#!/usr/bin/env python3
"""
Helper script for summarizing simulation results
Usage: python summarise_results.py <results_file> [--format csv|json] [--output output_file]
"""
import argparse
import json
import sys
import os
from typing import Dict, List, Any
import pandas as pd
import matplotlib.pyplot as plt
from src.result_storage import ResultStorage

def load_results(filepath: str) -> List[Dict[str, Any]]:
    """Load results from file"""
    storage = ResultStorage()
    return storage.load_results_from_file(filepath)

def generate_histogram(scores: List[int], output_path: str = None):
    """Generate score distribution histogram"""
    plt.figure(figsize=(8, 6))
    plt.hist(scores, bins=[0.5, 1.5, 2.5, 3.5], alpha=0.7, edgecolor='black')
    plt.xlabel('Score')
    plt.ylabel('Frequency')
    plt.title('Score Distribution')
    plt.xticks([1, 2, 3])
    plt.grid(True, alpha=0.3)
    
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Histogram saved to: {output_path}")
    else:
        plt.show()
    
    plt.close()

def print_summary_stats(results: List[Dict[str, Any]]):
    """Print summary statistics to console"""
    if not results:
        print("No results to summarize")
        return
    
    df = pd.DataFrame(results)
    
    print("=== SIMULATION RESULTS SUMMARY ===\n")
    
    # Basic counts
    total = len(results)
    successful = len(df[df['status'] == 'completed'])
    failed = len(df[df['status'] == 'failed'])
    
    print(f"Total scenarios: {total}")
    print(f"Successful: {successful} ({successful/total*100:.1f}%)")
    print(f"Failed: {failed} ({failed/total*100:.1f}%)")
    print()
    
    # Score statistics
    scores = df['score'].dropna()
    if len(scores) > 0:
        print("=== SCORE STATISTICS ===")
        print(f"Mean score: {scores.mean():.2f}")
        print(f"Median score: {scores.median():.2f}")
        print(f"Standard deviation: {scores.std():.2f}")
        print(f"Min score: {scores.min()}")
        print(f"Max score: {scores.max()}")
        print()
        
        print("=== SCORE DISTRIBUTION ===")
        score_counts = scores.value_counts().sort_index()
        for score in [1, 2, 3]:
            count = score_counts.get(score, 0)
            percentage = count / len(scores) * 100
            print(f"Score {score}: {count} ({percentage:.1f}%)")
        print()
    
    # Turn statistics
    turns = df['total_turns'].dropna()
    if len(turns) > 0:
        print("=== CONVERSATION LENGTH STATISTICS ===")
        print(f"Mean turns: {turns.mean():.1f}")
        print(f"Median turns: {turns.median():.1f}")
        print(f"Min turns: {turns.min()}")
        print(f"Max turns: {turns.max()}")
        print()
    
    # Duration statistics
    durations = df['duration_seconds'].dropna()
    if len(durations) > 0:
        print("=== DURATION STATISTICS ===")
        print(f"Mean duration: {durations.mean():.1f} seconds")
        print(f"Median duration: {durations.median():.1f} seconds")
        print(f"Total duration: {durations.sum():.1f} seconds")
        print(f"Min duration: {durations.min():.1f} seconds")
        print(f"Max duration: {durations.max():.1f} seconds")
        print()
    
    # Scenario breakdown
    if 'scenario' in df.columns:
        print("=== PERFORMANCE BY SCENARIO ===")
        scenario_stats = df.groupby('scenario').agg({
            'score': ['mean', 'count'],
            'total_turns': 'mean'
        }).round(2)
        
        for scenario in scenario_stats.index:
            mean_score = scenario_stats.loc[scenario, ('score', 'mean')]
            count = scenario_stats.loc[scenario, ('score', 'count')]
            mean_turns = scenario_stats.loc[scenario, ('total_turns', 'mean')]
            
            print(f"{scenario}:")
            print(f"  Count: {count}")
            print(f"  Mean score: {mean_score:.2f}")
            print(f"  Mean turns: {mean_turns:.1f}")
            print()

def save_summary_json(results: List[Dict[str, Any]], output_path: str):
    """Save summary as JSON file"""
    storage = ResultStorage()
    summary = storage.generate_summary_report("summary", results)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"Summary saved to: {output_path}")

def save_summary_csv(results: List[Dict[str, Any]], output_path: str):
    """Save summary as CSV file"""
    if not results:
        print("No results to save")
        return
    
    df = pd.DataFrame(results)
    
    # Select key columns for CSV summary
    summary_columns = ['session_id', 'scenario', 'score', 'total_turns', 'duration_seconds', 'status']
    available_columns = [col for col in summary_columns if col in df.columns]
    
    summary_df = df[available_columns]
    summary_df.to_csv(output_path, index=False)
    
    print(f"Summary CSV saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Summarize simulation results')
    parser.add_argument('results_file', help='Path to results file (NDJSON or CSV)')
    parser.add_argument('--format', choices=['csv', 'json'], help='Output format for summary')
    parser.add_argument('--output', help='Output file path')
    parser.add_argument('--histogram', help='Save histogram to this path')
    parser.add_argument('--quiet', action='store_true', help='Suppress console output')
    
    args = parser.parse_args()
    
    # Check if results file exists
    if not os.path.exists(args.results_file):
        print(f"Error: Results file not found: {args.results_file}")
        sys.exit(1)
    
    try:
        # Load results
        results = load_results(args.results_file)
        
        if not args.quiet:
            print_summary_stats(results)
        
        # Generate histogram if requested
        if args.histogram:
            scores = [r.get('score', 1) for r in results if r.get('score')]
            if scores:
                generate_histogram(scores, args.histogram)
            else:
                print("No scores available for histogram")
        
        # Save summary if requested
        if args.output and args.format:
            if args.format == 'json':
                save_summary_json(results, args.output)
            elif args.format == 'csv':
                save_summary_csv(results, args.output)
        
    except Exception as e:
        print(f"Error processing results: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

