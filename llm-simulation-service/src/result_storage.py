"""
Result storage and reporting system
"""
import json
import csv
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
from src.config import Config
from src.logging_utils import get_logger

class ResultStorage:
    """Handles storage and export of simulation results"""

    def __init__(self, results_dir: Optional[str] = None):
        self.logger = get_logger()
        self.results_dir = results_dir or Config.RESULTS_DIR
        Config.ensure_directories()
        if results_dir:
            os.makedirs(self.results_dir, exist_ok=True)
    
    def save_batch_results_ndjson(self, batch_id: str, results: List[Dict[str, Any]]) -> str:
        """Save batch results in NDJSON format"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"batch_{batch_id}_{timestamp}.ndjson"
        filepath = os.path.join(self.results_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for result in results:
                    # Add metadata
                    result_with_metadata = {
                        'batch_id': batch_id,
                        'export_timestamp': datetime.now().isoformat(),
                        **result
                    }
                    f.write(json.dumps(result_with_metadata, ensure_ascii=False) + '\n')
            
            self.logger.log_info(f"Saved NDJSON results", extra_data={
                'batch_id': batch_id,
                'filepath': filepath,
                'result_count': len(results)
            })
            
            return filepath
            
        except Exception as e:
            self.logger.log_error(f"Failed to save NDJSON results", exception=e, extra_data={'batch_id': batch_id})
            raise e
    
    def save_batch_results_csv(self, batch_id: str, results: List[Dict[str, Any]],
                              prompt_version: str = "default") -> str:
        """Save batch results in CSV format as specified in PRD"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"batch_{batch_id}_{timestamp}.csv"
        filepath = os.path.join(self.results_dir, filename)
        
        try:
            # Prepare CSV data according to PRD format:
            # session_id,scenario,prompt_version,score,comment,turns,start_ts
            csv_data = []
            
            for result in results:
                csv_row = {
                    'session_id': result.get('session_id', ''),
                    'scenario': result.get('scenario', ''),
                    'prompt_version': prompt_version,
                    'score': result.get('score', 1),
                    'comment': result.get('comment', '').replace('\n', ' ').replace('\r', ' '),  # Clean newlines
                    'turns': result.get('total_turns', 0),
                    'start_ts': result.get('start_time', ''),
                    'status': result.get('status', 'unknown'),
                    'duration_seconds': result.get('duration_seconds', 0),
                    'evaluation_status': result.get('evaluation_status', 'unknown')
                }
                csv_data.append(csv_row)
            
            # Write CSV file
            if csv_data:
                fieldnames = ['session_id', 'scenario', 'prompt_version', 'score', 'comment', 
                            'turns', 'start_ts', 'status', 'duration_seconds', 'evaluation_status']
                
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(csv_data)
            
            self.logger.log_info(f"Saved CSV results", extra_data={
                'batch_id': batch_id,
                'filepath': filepath,
                'result_count': len(results)
            })
            
            return filepath
            
        except Exception as e:
            self.logger.log_error(f"Failed to save CSV results", exception=e, extra_data={'batch_id': batch_id})
            raise e

    def save_batch_results_json(self, batch_id: str, results: List[Dict[str, Any]]) -> str:
        """Save batch results in JSON format"""

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"batch_{batch_id}_{timestamp}.json"
        filepath = os.path.join(self.results_dir, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'batch_id': batch_id,
                    'export_timestamp': datetime.now().isoformat(),
                    'results': results
                }, f, ensure_ascii=False, indent=2)

            self.logger.log_info("Saved JSON results", extra_data={
                'batch_id': batch_id,
                'filepath': filepath,
                'result_count': len(results)
            })

            return filepath

        except Exception as e:
            self.logger.log_error("Failed to save JSON results", exception=e, extra_data={'batch_id': batch_id})
            raise e

    def save_single_result(self, filename: str, result: Dict[str, Any]) -> str:
        """Save a single scenario result to a JSON file"""

        filepath = os.path.join(self.results_dir, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            self.logger.log_info("Saved single result", extra_data={'filepath': filepath})

            return filepath

        except Exception as e:
            self.logger.log_error("Failed to save single result", exception=e, extra_data={'filepath': filepath})
            raise e
    
    def generate_summary_report(self, batch_id: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics for batch results"""
        
        if not results:
            return {
                'batch_id': batch_id,
                'total_scenarios': 0,
                'summary_stats': {},
                'generated_at': datetime.now().isoformat()
            }
        
        try:
            # Convert to DataFrame for easier analysis
            df = pd.DataFrame(results)
            
            # Basic statistics
            total_scenarios = len(results)
            successful_scenarios = len(df[df['status'] == 'completed']) if 'status' in df.columns else 0
            failed_scenarios = len(df[df['status'] == 'failed']) if 'status' in df.columns else 0
            
            # Score statistics
            scores = df['score'].dropna() if 'score' in df.columns else pd.Series(dtype=float)
            score_stats = {
                'mean': float(scores.mean()) if len(scores) > 0 else 0,
                'median': float(scores.median()) if len(scores) > 0 else 0,
                'std': float(scores.std()) if len(scores) > 0 else 0,
                'min': int(scores.min()) if len(scores) > 0 else 0,
                'max': int(scores.max()) if len(scores) > 0 else 0
            }
            
            # Score distribution
            score_distribution = {
                'score_1': int((scores == 1).sum()) if len(scores) > 0 else 0,
                'score_2': int((scores == 2).sum()) if len(scores) > 0 else 0,
                'score_3': int((scores == 3).sum()) if len(scores) > 0 else 0
            }
            
            # Turn statistics (handle missing total_turns column)
            if 'total_turns' in df.columns:
                turns = df['total_turns'].dropna()
                turn_stats = {
                    'mean': float(turns.mean()) if len(turns) > 0 else 0,
                    'median': float(turns.median()) if len(turns) > 0 else 0,
                    'min': int(turns.min()) if len(turns) > 0 else 0,
                    'max': int(turns.max()) if len(turns) > 0 else 0
                }
            else:
                turn_stats = {
                    'mean': 0,
                    'median': 0,
                    'min': 0,
                    'max': 0
                }
            
            # Duration statistics
            if 'duration_seconds' in df.columns:
                durations = df['duration_seconds'].dropna()
                duration_stats = {
                    'mean': float(durations.mean()) if len(durations) > 0 else 0,
                    'median': float(durations.median()) if len(durations) > 0 else 0,
                    'min': float(durations.min()) if len(durations) > 0 else 0,
                    'max': float(durations.max()) if len(durations) > 0 else 0,
                    'total': float(durations.sum()) if len(durations) > 0 else 0
                }
            else:
                duration_stats = {
                    'mean': 0,
                    'median': 0,
                    'min': 0,
                    'max': 0,
                    'total': 0
                }
            
            # Scenario performance (handle missing columns gracefully)
            agg_dict = {'score': ['mean', 'count']}
            if 'total_turns' in df.columns:
                agg_dict['total_turns'] = 'mean'
            if 'duration_seconds' in df.columns:
                agg_dict['duration_seconds'] = 'mean'
                
            scenario_agg = df.groupby('scenario').agg(agg_dict).round(2)
            
            # Flatten MultiIndex columns to avoid tuple keys in JSON
            scenario_agg.columns = ['_'.join(col).strip() if isinstance(col, tuple) else str(col) for col in scenario_agg.columns]
            scenario_stats = scenario_agg.to_dict()
            
            summary = {
                'batch_id': batch_id,
                'total_scenarios': total_scenarios,
                'successful_scenarios': successful_scenarios,
                'failed_scenarios': failed_scenarios,
                'success_rate': successful_scenarios / total_scenarios if total_scenarios > 0 else 0,
                'score_statistics': score_stats,
                'score_distribution': score_distribution,
                'turn_statistics': turn_stats,
                'duration_statistics': duration_stats,
                'scenario_performance': scenario_stats,
                'generated_at': datetime.now().isoformat()
            }
            
            self.logger.log_info(f"Generated summary report", extra_data={
                'batch_id': batch_id,
                'total_scenarios': total_scenarios,
                'mean_score': score_stats['mean']
            })
            
            return summary
            
        except Exception as e:
            self.logger.log_error(f"Failed to generate summary report", exception=e, extra_data={'batch_id': batch_id})
            raise e
    
    def save_summary_report(self, summary: Dict[str, Any]) -> str:
        """Save summary report to JSON file"""
        
        batch_id = summary.get('batch_id', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"summary_{batch_id}_{timestamp}.json"
        filepath = os.path.join(self.results_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            
            self.logger.log_info(f"Saved summary report", extra_data={
                'batch_id': batch_id,
                'filepath': filepath
            })
            
            return filepath
            
        except Exception as e:
            self.logger.log_error(f"Failed to save summary report", exception=e, extra_data={'batch_id': batch_id})
            raise e
    
    def load_results_from_file(self, filepath: str) -> List[Dict[str, Any]]:
        """Load results from NDJSON or CSV file"""
        
        try:
            if filepath.endswith('.ndjson'):
                results = []
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            results.append(json.loads(line))
                return results
                
            elif filepath.endswith('.csv'):
                df = pd.read_csv(filepath)
                return df.to_dict('records')
                
            else:
                raise ValueError(f"Unsupported file format: {filepath}")
                
        except Exception as e:
            self.logger.log_error(f"Failed to load results from file", exception=e, extra_data={'filepath': filepath})
            raise e
    
    def get_cost_estimate(self, batch_id: str) -> Dict[str, Any]:
        """Get cost estimate from token usage logs"""
        
        try:
            # Read token usage logs
            log_files = [f for f in os.listdir(Config.LOGS_DIR) if f.startswith('tokens_') and batch_id in f]
            
            total_cost = 0.0
            total_tokens = 0
            total_requests = 0
            
            for log_file in log_files:
                log_path = os.path.join(Config.LOGS_DIR, log_file)
                
                with open(log_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            try:
                                token_data = json.loads(line.split(' - ', 1)[1])  # Remove timestamp
                                total_cost += token_data.get('cost_estimate', 0)
                                total_tokens += token_data.get('total_tokens', 0)
                                total_requests += 1
                            except (json.JSONDecodeError, IndexError):
                                continue
            
            cost_report = {
                'batch_id': batch_id,
                'total_cost_usd': round(total_cost, 4),
                'total_tokens': total_tokens,
                'total_requests': total_requests,
                'average_cost_per_request': round(total_cost / total_requests, 4) if total_requests > 0 else 0,
                'generated_at': datetime.now().isoformat()
            }
            
            self.logger.log_info(f"Generated cost estimate", extra_data=cost_report)
            
            return cost_report
            
        except Exception as e:
            self.logger.log_error(f"Failed to generate cost estimate", exception=e, extra_data={'batch_id': batch_id})
            return {
                'batch_id': batch_id,
                'total_cost_usd': 0.0,
                'error': str(e),
                'generated_at': datetime.now().isoformat()
            }
    
    def list_result_files(self, batch_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available result files"""
        
        try:
            files = []
            
            for filename in os.listdir(self.results_dir):
                if batch_id and batch_id not in filename:
                    continue
                
                filepath = os.path.join(self.results_dir, filename)
                if os.path.isfile(filepath):
                    stat = os.stat(filepath)
                    
                    files.append({
                        'filename': filename,
                        'filepath': filepath,
                        'size_bytes': stat.st_size,
                        'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
            
            # Sort by creation time (newest first)
            files.sort(key=lambda x: x['created_at'], reverse=True)
            
            return files
            
        except Exception as e:
            self.logger.log_error(f"Failed to list result files", exception=e)
            return []

