"""
REST API routes for batch simulation service
"""
import asyncio
import os
from flask import Blueprint, request, jsonify, send_file
from werkzeug.exceptions import BadRequest, NotFound
from src.config import Config
from src.batch_processor import BatchProcessor
from src.result_storage import ResultStorage
from src.logging_utils import get_logger

# Create blueprint for batch routes
batch_bp = Blueprint('batch', __name__)

# Global batch processor instance
batch_processor = None
result_storage = ResultStorage()
logger = get_logger()

def get_batch_processor():
    """Get or create batch processor instance"""
    global batch_processor
    if batch_processor is None:
        # Validate configuration
        Config.validate()
        batch_processor = BatchProcessor(Config.OPENAI_API_KEY, Config.CONCURRENCY)
    return batch_processor

@batch_bp.route('/batches', methods=['POST'])
def launch_batch():
    """Launch a new batch simulation job"""
    try:
        # Validate request
        if not request.is_json:
            raise BadRequest("Request must be JSON")
        
        data = request.get_json()
        scenarios = data.get('scenarios', [])
        
        if not scenarios:
            raise BadRequest("No scenarios provided")
        
        if not isinstance(scenarios, list):
            raise BadRequest("Scenarios must be a list")
        
        # Validate scenarios
        for i, scenario in enumerate(scenarios):
            if not isinstance(scenario, dict):
                raise BadRequest(f"Scenario {i} must be an object")
            
            if 'name' not in scenario:
                raise BadRequest(f"Scenario {i} missing 'name' field")
            
            if 'variables' not in scenario:
                raise BadRequest(f"Scenario {i} missing 'variables' field")
        
        # Create batch job
        processor = get_batch_processor()
        
        # Add prompt_version and use_tools to the batch data
        prompt_version = data.get('prompt_version', 'v1.0')
        use_tools = data.get('use_tools', True)
        batch_id = processor.create_batch_job(scenarios, prompt_version, use_tools)
        
        # Start batch processing in background
        def run_batch_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Define progress callback to update batch status
                async def progress_callback(batch_id: str, completed_count: int):
                    # Progress is handled within BatchProcessor._update_progress
                    # This callback can be used for additional logging if needed
                    logger.log_info(f"Batch {batch_id} progress: {completed_count} scenarios completed")
                
                result = loop.run_until_complete(processor.run_batch(batch_id, progress_callback))
                
                # Save results when batch completes
                if result.get('status') == 'completed':
                    results = result.get('results', [])
                    
                    # Save in both formats
                    result_storage.save_batch_results_ndjson(batch_id, results)
                    result_storage.save_batch_results_csv(batch_id, results)
                    
                    # Generate and save summary
                    summary = result_storage.generate_summary_report(batch_id, results)
                    result_storage.save_summary_report(summary)
                    
                    logger.log_info(f"Batch {batch_id} completed and results saved")
                
            except Exception as e:
                logger.log_error(f"Background batch processing failed", exception=e, extra_data={'batch_id': batch_id})
            finally:
                loop.close()
        
        # Start background thread
        import threading
        thread = threading.Thread(target=run_batch_async)
        thread.daemon = True
        thread.start()
        
        logger.log_info(f"Launched batch job", extra_data={
            'batch_id': batch_id,
            'scenario_count': len(scenarios)
        })
        
        return jsonify({
            'batch_id': batch_id,
            'status': 'launched',
            'total_scenarios': len(scenarios)
        }), 201
        
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.log_error("Failed to launch batch", exception=e)
        return jsonify({'error': 'Internal server error'}), 500

@batch_bp.route('/batches/<batch_id>', methods=['GET'])
def get_batch_status(batch_id: str):
    """Get status of a batch job"""
    try:
        processor = get_batch_processor()
        status = processor.get_batch_status(batch_id)
        
        if status is None:
            raise NotFound(f"Batch {batch_id} not found")
        
        return jsonify(status), 200
        
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.log_error("Failed to get batch status", exception=e, extra_data={'batch_id': batch_id})
        return jsonify({'error': 'Internal server error'}), 500

@batch_bp.route('/batches/<batch_id>/results', methods=['GET'])
def get_batch_results(batch_id: str):
    """Get results of a completed batch job"""
    try:
        processor = get_batch_processor()
        
        # Check if batch exists
        status = processor.get_batch_status(batch_id)
        if status is None:
            raise NotFound(f"Batch {batch_id} not found")
        
        # Check if batch is completed
        if status['status'] != 'completed':
            return jsonify({
                'error': 'Batch not completed',
                'current_status': status['status']
            }), 400
        
        # Get format preference
        format_type = request.args.get('format', 'json').lower()
        
        if format_type == 'csv':
            # Find CSV file for this batch
            result_files = result_storage.list_result_files(batch_id)
            csv_files = [f for f in result_files if f['filename'].endswith('.csv')]
            
            if not csv_files:
                return jsonify({'error': 'CSV results not found'}), 404
            
            # Return most recent CSV file
            csv_file = csv_files[0]
            return send_file(
                csv_file['filepath'],
                as_attachment=True,
                download_name=f"batch_{batch_id}_results.csv",
                mimetype='text/csv'
            )
            
        elif format_type == 'ndjson':
            # Find NDJSON file for this batch
            result_files = result_storage.list_result_files(batch_id)
            ndjson_files = [f for f in result_files if f['filename'].endswith('.ndjson')]
            
            if not ndjson_files:
                return jsonify({'error': 'NDJSON results not found'}), 404
            
            # Return most recent NDJSON file
            ndjson_file = ndjson_files[0]
            return send_file(
                ndjson_file['filepath'],
                as_attachment=True,
                download_name=f"batch_{batch_id}_results.ndjson",
                mimetype='application/x-ndjson'
            )
            
        else:
            # Return JSON results directly
            results = processor.get_batch_results(batch_id)
            if results is None:
                return jsonify({'error': 'Results not found'}), 404
            
            return jsonify({
                'batch_id': batch_id,
                'results': results,
                'total_results': len(results)
            }), 200
        
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.log_error("Failed to get batch results", exception=e, extra_data={'batch_id': batch_id})
        return jsonify({'error': 'Internal server error'}), 500

@batch_bp.route('/batches/<batch_id>/summary', methods=['GET'])
def get_batch_summary(batch_id: str):
    """Get summary statistics for a batch"""
    try:
        processor = get_batch_processor()
        
        # Check if batch exists and is completed
        status = processor.get_batch_status(batch_id)
        if status is None:
            raise NotFound(f"Batch {batch_id} not found")
        
        if status['status'] != 'completed':
            return jsonify({
                'error': 'Batch not completed',
                'current_status': status['status']
            }), 400
        
        # Get results and generate summary
        results = processor.get_batch_results(batch_id)
        if results is None:
            return jsonify({'error': 'Results not found'}), 404
        
        summary = result_storage.generate_summary_report(batch_id, results)
        
        return jsonify(summary), 200
        
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.log_error("Failed to get batch summary", exception=e, extra_data={'batch_id': batch_id})
        return jsonify({'error': 'Internal server error'}), 500

@batch_bp.route('/batches/<batch_id>/cost', methods=['GET'])
def get_batch_cost(batch_id: str):
    """Get cost estimate for a batch"""
    try:
        processor = get_batch_processor()
        
        # Check if batch exists
        status = processor.get_batch_status(batch_id)
        if status is None:
            raise NotFound(f"Batch {batch_id} not found")
        
        cost_estimate = result_storage.get_cost_estimate(batch_id)
        
        return jsonify(cost_estimate), 200
        
    except NotFound as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.log_error("Failed to get batch cost", exception=e, extra_data={'batch_id': batch_id})
        return jsonify({'error': 'Internal server error'}), 500

@batch_bp.route('/batches', methods=['GET'])
def list_batches():
    """List all batch jobs"""
    try:
        processor = get_batch_processor()
        
        # Get all active jobs
        batches = []
        for batch_id in processor.active_jobs:
            status = processor.get_batch_status(batch_id)
            if status:
                batches.append(status)
        
        # Sort by creation time (newest first)
        batches.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'batches': batches,
            'total_count': len(batches)
        }), 200
        
    except Exception as e:
        logger.log_error("Failed to list batches", exception=e)
        return jsonify({'error': 'Internal server error'}), 500

@batch_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Basic health check
        health_status = {
            'status': 'healthy',
            'service': 'LLM Simulation Service',
            'version': '1.0.0',
            'timestamp': Config.ensure_directories() or 'ok'  # This will create dirs and return None, so we use 'ok'
        }
        
        # Check OpenAI API key
        if not Config.OPENAI_API_KEY:
            health_status['status'] = 'unhealthy'
            health_status['error'] = 'OpenAI API key not configured'
            return jsonify(health_status), 503
        
        return jsonify(health_status), 200
        
    except Exception as e:
        logger.log_error("Health check failed", exception=e)
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503

