import React, { useState, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  LinearProgress,
  Alert,
} from '@mui/material';
import {
  CloudUpload,
  CheckCircle,
  Error,
} from '@mui/icons-material';

const FileUpload = ({ onFileUpload, onError, accept = '.json', maxSize = 10 * 1024 * 1024 }) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);

  const validateScenarios = (scenarios) => {
    if (!Array.isArray(scenarios)) {
      throw new Error('Scenarios must be an array');
    }

    if (scenarios.length === 0) {
      throw new Error('Scenarios array cannot be empty');
    }

    scenarios.forEach((scenario, index) => {
      if (!scenario.name) {
        throw new Error(`Scenario ${index + 1} is missing a name`);
      }
      if (!scenario.variables || typeof scenario.variables !== 'object') {
        throw new Error(`Scenario ${index + 1} is missing variables object`);
      }
    });

    return true;
  };

  const processFile = useCallback(async (file) => {
    setIsProcessing(true);
    setUploadedFile(null);

    try {
      // Check file size
      if (file.size > maxSize) {
        throw new Error(`File size exceeds ${Math.round(maxSize / 1024 / 1024)}MB limit`);
      }

      // Check file type
      if (accept && !file.name.toLowerCase().endsWith('.json')) {
        throw new Error('Please upload a JSON file');
      }

      // Read file content
      const text = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result);
        reader.onerror = () => reject(new Error('Failed to read file'));
        reader.readAsText(file);
      });

      // Parse JSON
      let scenarios;
      try {
        scenarios = JSON.parse(text);
      } catch (err) {
        throw new Error('Invalid JSON format');
      }

      // Validate scenarios structure
      validateScenarios(scenarios);

      setUploadedFile(file);
      onFileUpload(file, scenarios);
    } catch (err) {
      onError(err.message);
    } finally {
      setIsProcessing(false);
    }
  }, [onFileUpload, onError, accept, maxSize]);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      processFile(files[0]);
    }
  }, [processFile]);

  const handleFileSelect = useCallback((e) => {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
      processFile(files[0]);
    }
  }, [processFile]);

  return (
    <Box>
      <Paper
        sx={{
          p: 4,
          border: 2,
          borderStyle: 'dashed',
          borderColor: isDragOver ? 'primary.main' : 'grey.300',
          bgcolor: isDragOver ? 'primary.50' : 'grey.50',
          textAlign: 'center',
          cursor: 'pointer',
          transition: 'all 0.2s ease-in-out',
          '&:hover': {
            borderColor: 'primary.main',
            bgcolor: 'primary.50',
          },
        }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => document.getElementById('file-input').click()}
      >
        <input
          id="file-input"
          type="file"
          accept={accept}
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />

        {isProcessing ? (
          <Box>
            <Typography variant="h6" gutterBottom>
              Processing file...
            </Typography>
            <LinearProgress sx={{ mt: 2 }} />
          </Box>
        ) : uploadedFile ? (
          <Box>
            <CheckCircle color="success" sx={{ fontSize: 48, mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              File uploaded successfully
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {uploadedFile.name} ({Math.round(uploadedFile.size / 1024)} KB)
            </Typography>
            <Button
              variant="outlined"
              size="small"
              sx={{ mt: 2 }}
              onClick={(e) => {
                e.stopPropagation();
                setUploadedFile(null);
              }}
            >
              Upload Different File
            </Button>
          </Box>
        ) : (
          <Box>
            <CloudUpload sx={{ fontSize: 48, color: 'grey.400', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              Drop your scenarios file here
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              or click to browse files
            </Typography>
            <Button variant="outlined" component="span">
              Choose File
            </Button>
            <Typography variant="caption" display="block" sx={{ mt: 2 }} color="text.secondary">
              Supports JSON files up to {Math.round(maxSize / 1024 / 1024)}MB
            </Typography>
          </Box>
        )}
      </Paper>
    </Box>
  );
};

export default FileUpload;

