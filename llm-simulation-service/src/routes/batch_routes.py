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
    """Launch a new batch of conversation simulations"""
    try:
        data = request.get_json()
        
        if not data or 'scenarios' not in data:
            return jsonify({'error': 'Missing scenarios in request body'}), 400
        
        scenarios = data['scenarios']
        if not isinstance(scenarios, list) or len(scenarios) == 0:
            return jsonify({'error': 'Scenarios must be a non-empty list'}), 400
        
        # Optional parameters with defaults
        prompt_version = data.get('prompt_version', 'v1.0')
        prompt_spec_name = data.get('prompt_spec_name', 'default_prompts')
        use_tools = data.get('use_tools', True)
        use_autogen = data.get('use_autogen', False)
        
        # Validate prompt_spec_name
        if not isinstance(prompt_spec_name, str) or not prompt_spec_name.strip():
            return jsonify({'error': 'prompt_spec_name must be a non-empty string'}), 400
        
        # Log the incoming request
        logger.log_info(f"Launching batch with {len(scenarios)} scenarios", extra_data={
            'total_scenarios': len(scenarios),
            'prompt_version': prompt_version,
            'prompt_spec_name': prompt_spec_name,
            'use_tools': use_tools,
            'use_autogen': use_autogen
        })
        
        # Get or create batch processor instance
        processor = get_batch_processor()
        
        # Create batch job
        batch_id = processor.create_batch_job(
            scenarios=scenarios, 
            prompt_version=prompt_version,
            prompt_spec_name=prompt_spec_name,
            use_tools=use_tools,
            use_autogen=use_autogen
        )
        
        # Start batch processing in background
        def run_batch_async():
            """Run batch in background thread"""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(processor.run_batch(batch_id))
                logger.log_info(f"Background batch completed", extra_data={
                    'batch_id': batch_id,
                    'result_status': result.get('status', 'unknown')
                })
            except Exception as e:
                logger.log_error(f"Background batch failed", exception=e, extra_data={'batch_id': batch_id})
            finally:
                loop.close()
        
        # Start background thread
        import threading
        thread = threading.Thread(target=run_batch_async, daemon=True)
        thread.start()
        
        return jsonify({
            'batch_id': batch_id,
            'status': 'launched',
            'total_scenarios': len(scenarios),
            'prompt_version': prompt_version,
            'prompt_spec_name': prompt_spec_name,
            'use_tools': use_tools,
            'use_autogen': use_autogen
        }), 200
        
    except Exception as e:
        logger.log_error("Failed to launch batch", exception=e)
        return jsonify({'error': f'Failed to launch batch: {str(e)}'}), 500

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

