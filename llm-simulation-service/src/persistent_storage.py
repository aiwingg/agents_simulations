"""
Persistent storage system for batch jobs and metadata
"""
import os
import json
import glob
from typing import Dict, List, Any, Optional
from datetime import datetime
from src.config import Config
from src.logging_utils import get_logger

class PersistentBatchStorage:
    """Handles persistent storage of batch metadata and status"""
    
    def __init__(self):
        self.logger = get_logger()
        self.batches_dir = os.path.join(Config.RESULTS_DIR, 'batches')
        self.ensure_directories()
    
    def ensure_directories(self):
        """Ensure required directories exist"""
        os.makedirs(self.batches_dir, exist_ok=True)
        self.logger.log_info(f"Batch storage directory: {self.batches_dir}")
    
    def save_batch_metadata(self, batch_data: Dict[str, Any]):
        """Save batch metadata to file"""
        batch_id = batch_data['batch_id']
        metadata_file = os.path.join(self.batches_dir, f"{batch_id}_metadata.json")
        
        # Prepare serializable data
        serializable_data = self._prepare_serializable_data(batch_data)
        
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_data, f, indent=2, ensure_ascii=False)
            
            self.logger.log_info(f"Saved batch metadata", extra_data={'batch_id': batch_id})
        except Exception as e:
            self.logger.log_error(f"Failed to save batch metadata", exception=e, extra_data={'batch_id': batch_id})
    
    def load_batch_metadata(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Load batch metadata from file"""
        metadata_file = os.path.join(self.batches_dir, f"{batch_id}_metadata.json")
        
        if not os.path.exists(metadata_file):
            return None
        
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert datetime strings back to datetime objects
            data = self._restore_datetime_objects(data)
            return data
        except Exception as e:
            self.logger.log_error(f"Failed to load batch metadata", exception=e, extra_data={'batch_id': batch_id})
            return None
    
    def load_all_batches(self) -> Dict[str, Dict[str, Any]]:
        """Load all batch metadata from storage"""
        batches = {}
        
        # Find all metadata files
        pattern = os.path.join(self.batches_dir, "*_metadata.json")
        metadata_files = glob.glob(pattern)
        
        for metadata_file in metadata_files:
            try:
                # Extract batch_id from filename
                filename = os.path.basename(metadata_file)
                batch_id = filename.replace('_metadata.json', '')
                
                batch_data = self.load_batch_metadata(batch_id)
                if batch_data:
                    batches[batch_id] = batch_data
                    
            except Exception as e:
                self.logger.log_error(f"Failed to load batch from {metadata_file}", exception=e)
        
        self.logger.log_info(f"Loaded {len(batches)} batches from storage")
        return batches
    
    def delete_batch_metadata(self, batch_id: str) -> bool:
        """Delete batch metadata file"""
        metadata_file = os.path.join(self.batches_dir, f"{batch_id}_metadata.json")
        
        try:
            if os.path.exists(metadata_file):
                os.remove(metadata_file)
                self.logger.log_info(f"Deleted batch metadata", extra_data={'batch_id': batch_id})
                return True
            return False
        except Exception as e:
            self.logger.log_error(f"Failed to delete batch metadata", exception=e, extra_data={'batch_id': batch_id})
            return False
    
    def list_batch_ids(self) -> List[str]:
        """Get list of all stored batch IDs"""
        pattern = os.path.join(self.batches_dir, "*_metadata.json")
        metadata_files = glob.glob(pattern)
        
        batch_ids = []
        for metadata_file in metadata_files:
            filename = os.path.basename(metadata_file)
            batch_id = filename.replace('_metadata.json', '')
            batch_ids.append(batch_id)
        
        return sorted(batch_ids, reverse=True)  # Most recent first
    
    def cleanup_old_batches(self, max_age_days: int = 30):
        """Clean up old batch metadata files"""
        cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)
        
        pattern = os.path.join(self.batches_dir, "*_metadata.json")
        metadata_files = glob.glob(pattern)
        
        deleted_count = 0
        for metadata_file in metadata_files:
            try:
                file_time = os.path.getmtime(metadata_file)
                if file_time < cutoff_time:
                    os.remove(metadata_file)
                    deleted_count += 1
                    
            except Exception as e:
                self.logger.log_error(f"Failed to delete old metadata file {metadata_file}", exception=e)
        
        if deleted_count > 0:
            self.logger.log_info(f"Cleaned up {deleted_count} old batch metadata files")
    
    def _prepare_serializable_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for JSON serialization"""
        serializable = {}
        
        for key, value in data.items():
            if isinstance(value, datetime):
                serializable[key] = value.isoformat()
            elif hasattr(value, '__dict__'):  # Handle dataclass or custom objects
                serializable[key] = self._prepare_serializable_data(value.__dict__)
            elif isinstance(value, dict):
                serializable[key] = self._prepare_serializable_data(value)
            elif isinstance(value, list):
                serializable[key] = [
                    self._prepare_serializable_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                # Handle enums and other objects
                if hasattr(value, 'value'):  # Enum
                    serializable[key] = value.value
                else:
                    serializable[key] = value
        
        return serializable
    
    def _restore_datetime_objects(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Restore datetime objects from ISO strings"""
        datetime_fields = ['created_at', 'started_at', 'completed_at']
        
        for field in datetime_fields:
            if field in data and data[field] is not None:
                try:
                    data[field] = datetime.fromisoformat(data[field])
                except (ValueError, TypeError):
                    data[field] = None
        
        return data 