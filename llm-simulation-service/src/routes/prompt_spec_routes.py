"""
Routes for prompt specification management
"""
from flask import Blueprint, request, jsonify
from typing import Dict, Any
from src.prompt_specification import PromptSpecificationManager
from src.logging_utils import get_logger

# Create blueprint
prompt_spec_bp = Blueprint('prompt_specs', __name__)

# Initialize manager and logger
prompt_manager = PromptSpecificationManager()
logger = get_logger()

@prompt_spec_bp.route('/prompt-specs', methods=['GET'])
def list_prompt_specifications():
    """List all available prompt specifications"""
    try:
        specifications = prompt_manager.list_available_specifications()
        
        logger.log_info(f"Listed {len(specifications)} prompt specifications")
        
        return jsonify({
            'specifications': specifications,
            'total_count': len(specifications)
        }), 200
    
    except Exception as e:
        logger.log_error("Failed to list prompt specifications", exception=e)
        return jsonify({'error': f'Failed to list specifications: {str(e)}'}), 500

@prompt_spec_bp.route('/prompt-specs/<spec_name>', methods=['GET'])
def get_prompt_specification(spec_name: str):
    """Get the contents of a specific prompt specification"""
    try:
        # Validate spec name
        if not spec_name or not spec_name.strip():
            return jsonify({'error': 'Specification name is required'}), 400
        
        # Check if specification exists
        if not prompt_manager.specification_exists(spec_name):
            return jsonify({'error': f'Prompt specification not found: {spec_name}'}), 404
        
        # Get specification contents
        contents = prompt_manager.get_specification_contents(spec_name)
        
        logger.log_info(f"Retrieved prompt specification: {spec_name}")
        
        return jsonify(contents), 200
    
    except Exception as e:
        logger.log_error(f"Failed to get prompt specification: {spec_name}", exception=e)
        return jsonify({'error': f'Failed to get specification: {str(e)}'}), 500

@prompt_spec_bp.route('/prompt-specs/<spec_name>', methods=['POST'])
def create_prompt_specification(spec_name: str):
    """Create or update a prompt specification"""
    try:
        # Validate spec name
        if not spec_name or not spec_name.strip():
            return jsonify({'error': 'Specification name is required'}), 400
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON data is required'}), 400
        
        # Check if specification already exists
        exists = prompt_manager.specification_exists(spec_name)
        
        # Save specification
        prompt_manager.save_specification(spec_name, data)
        
        logger.log_info(f"{'Updated' if exists else 'Created'} prompt specification: {spec_name}")
        
        return jsonify({
            'message': f"Prompt specification {'updated' if exists else 'created'} successfully",
            'specification_name': spec_name,
            'action': 'updated' if exists else 'created'
        }), 200 if exists else 201
    
    except ValueError as e:
        logger.log_error(f"Validation error for prompt specification: {spec_name}", exception=e)
        return jsonify({'error': f'Validation error: {str(e)}'}), 400
    
    except Exception as e:
        logger.log_error(f"Failed to save prompt specification: {spec_name}", exception=e)
        return jsonify({'error': f'Failed to save specification: {str(e)}'}), 500

@prompt_spec_bp.route('/prompt-specs/<spec_name>', methods=['PUT'])
def update_prompt_specification(spec_name: str):
    """Update an existing prompt specification (requires specification to exist)"""
    try:
        # Validate spec name
        if not spec_name or not spec_name.strip():
            return jsonify({'error': 'Specification name is required'}), 400
        
        # Check if specification exists
        if not prompt_manager.specification_exists(spec_name):
            return jsonify({'error': f'Prompt specification not found: {spec_name}'}), 404
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON data is required'}), 400
        
        # Save specification
        prompt_manager.save_specification(spec_name, data)
        
        logger.log_info(f"Updated prompt specification: {spec_name}")
        
        return jsonify({
            'message': 'Prompt specification updated successfully',
            'specification_name': spec_name
        }), 200
    
    except ValueError as e:
        logger.log_error(f"Validation error for prompt specification: {spec_name}", exception=e)
        return jsonify({'error': f'Validation error: {str(e)}'}), 400
    
    except Exception as e:
        logger.log_error(f"Failed to update prompt specification: {spec_name}", exception=e)
        return jsonify({'error': f'Failed to update specification: {str(e)}'}), 500

@prompt_spec_bp.route('/prompt-specs/<spec_name>', methods=['DELETE'])
def delete_prompt_specification(spec_name: str):
    """Delete a prompt specification"""
    try:
        # Validate spec name
        if not spec_name or not spec_name.strip():
            return jsonify({'error': 'Specification name is required'}), 400
        
        # Prevent deletion of default specification
        if spec_name == 'default_prompts':
            return jsonify({'error': 'Cannot delete the default prompt specification'}), 403
        
        # Check if specification exists
        if not prompt_manager.specification_exists(spec_name):
            return jsonify({'error': f'Prompt specification not found: {spec_name}'}), 404
        
        # Delete specification
        prompt_manager.delete_specification(spec_name)
        
        logger.log_info(f"Deleted prompt specification: {spec_name}")
        
        return jsonify({
            'message': 'Prompt specification deleted successfully',
            'specification_name': spec_name
        }), 200
    
    except ValueError as e:
        logger.log_error(f"Error deleting prompt specification: {spec_name}", exception=e)
        return jsonify({'error': str(e)}), 403
    
    except Exception as e:
        logger.log_error(f"Failed to delete prompt specification: {spec_name}", exception=e)
        return jsonify({'error': f'Failed to delete specification: {str(e)}'}), 500

@prompt_spec_bp.route('/prompt-specs/<spec_name>/validate', methods=['POST'])
def validate_prompt_specification(spec_name: str):
    """Validate a prompt specification without saving it"""
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON data is required'}), 400
        
        # Try to create specification object from data
        from src.prompt_specification import SystemPromptSpecification
        specification = SystemPromptSpecification.from_dict(data)
        
        # Validate the specification
        issues = prompt_manager.validate_specification(specification)
        
        is_valid = len(issues) == 0
        
        logger.log_info(f"Validated prompt specification: {spec_name} - {'Valid' if is_valid else 'Invalid'}")
        
        return jsonify({
            'valid': is_valid,
            'issues': issues,
            'specification_name': spec_name,
            'agents': list(specification.agents.keys())
        }), 200
    
    except Exception as e:
        logger.log_error(f"Failed to validate prompt specification: {spec_name}", exception=e)
        return jsonify({
            'valid': False,
            'issues': [f'Failed to validate: {str(e)}'],
            'specification_name': spec_name
        }), 400

@prompt_spec_bp.route('/prompt-specs/<spec_name>/duplicate', methods=['POST'])
def duplicate_prompt_specification(spec_name: str):
    """Duplicate an existing prompt specification with a new name"""
    try:
        # Validate source spec name
        if not spec_name or not spec_name.strip():
            return jsonify({'error': 'Source specification name is required'}), 400
        
        # Check if source specification exists
        if not prompt_manager.specification_exists(spec_name):
            return jsonify({'error': f'Source prompt specification not found: {spec_name}'}), 404
        
        # Get new name from request
        data = request.get_json()
        if not data or 'new_name' not in data:
            return jsonify({'error': 'new_name is required in request body'}), 400
        
        new_name = data['new_name']
        if not new_name or not new_name.strip():
            return jsonify({'error': 'new_name cannot be empty'}), 400
        
        # Check if target specification already exists
        if prompt_manager.specification_exists(new_name):
            return jsonify({'error': f'Target specification already exists: {new_name}'}), 409
        
        # Get source specification contents
        source_contents = prompt_manager.get_specification_contents(spec_name)
        
        # Update name and version in the duplicated content
        source_contents['name'] = data.get('display_name', f"{source_contents['name']} (Copy)")
        source_contents['version'] = data.get('version', '1.0.0')
        if 'description' in data:
            source_contents['description'] = data['description']
        
        # Save as new specification
        prompt_manager.save_specification(new_name, source_contents)
        
        logger.log_info(f"Duplicated prompt specification from {spec_name} to {new_name}")
        
        return jsonify({
            'message': 'Prompt specification duplicated successfully',
            'source_name': spec_name,
            'new_name': new_name
        }), 201
    
    except Exception as e:
        logger.log_error(f"Failed to duplicate prompt specification: {spec_name}", exception=e)
        return jsonify({'error': f'Failed to duplicate specification: {str(e)}'}), 500 