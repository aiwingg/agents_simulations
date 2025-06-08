import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  Alert,
  CircularProgress,
  Paper,
  Divider,
} from '@mui/material';
import {
  CloudUpload,
  PlayArrow,
  Description,
} from '@mui/icons-material';
import { toast } from 'sonner';

// Import components
import FileUpload from '../components/FileUpload';
import { launchBatch } from '../services/api';

const LaunchPage = () => {
  const navigate = useNavigate();
  const [scenarios, setScenarios] = useState(null);
  const [promptVersion, setPromptVersion] = useState('v1');
  const [isLaunching, setIsLaunching] = useState(false);
  const [error, setError] = useState(null);

  const handleFileUpload = (file, parsedScenarios) => {
    setScenarios(parsedScenarios);
    setError(null);
    toast.success(`Loaded ${parsedScenarios.length} scenarios from ${file.name}`);
  };

  const handleFileError = (errorMessage) => {
    setError(errorMessage);
    setScenarios(null);
    toast.error(errorMessage);
  };

  const handleLaunch = async () => {
    if (!scenarios || scenarios.length === 0) {
      toast.error('Please upload a scenarios file first');
      return;
    }

    if (!promptVersion.trim()) {
      toast.error('Please enter a prompt version');
      return;
    }

    setIsLaunching(true);
    setError(null);

    try {
      const response = await launchBatch({
        scenarios: scenarios,
        prompt_version: promptVersion.trim(),
      });

      toast.success(`Batch launched successfully! ID: ${response.batch_id}`);
      navigate(`/batch/${response.batch_id}`);
    } catch (err) {
      const errorMessage = err.response?.data?.error || err.message || 'Failed to launch batch';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsLaunching(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ mb: 4, textAlign: 'center' }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Launch Simulation Batch
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Upload your scenarios file and configure the simulation parameters
        </Typography>
      </Box>

      {/* Main Card */}
      <Card elevation={2}>
        <CardContent sx={{ p: 4 }}>
          {/* File Upload Section */}
          <Box sx={{ mb: 4 }}>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
              <CloudUpload sx={{ mr: 1 }} />
              Upload Scenarios
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Upload a JSON file containing your simulation scenarios
            </Typography>
            <FileUpload
              onFileUpload={handleFileUpload}
              onError={handleFileError}
              accept=".json"
              maxSize={10 * 1024 * 1024} // 10MB
            />
          </Box>

          <Divider sx={{ my: 3 }} />

          {/* Configuration Section */}
          <Box sx={{ mb: 4 }}>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
              <Description sx={{ mr: 1 }} />
              Configuration
            </Typography>
            <TextField
              fullWidth
              label="Prompt Version"
              value={promptVersion}
              onChange={(e) => setPromptVersion(e.target.value)}
              placeholder="e.g., v1, v2.1, experimental"
              helperText="Enter a version identifier for this prompt configuration"
              sx={{ mt: 2 }}
            />
          </Box>

          {/* Scenarios Preview */}
          {scenarios && (
            <Box sx={{ mb: 4 }}>
              <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                <Typography variant="subtitle2" gutterBottom>
                  Scenarios Preview
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {scenarios.length} scenarios loaded
                </Typography>
                {scenarios.slice(0, 3).map((scenario, index) => (
                  <Typography key={index} variant="body2" sx={{ mt: 1 }}>
                    • {scenario.name}
                  </Typography>
                ))}
                {scenarios.length > 3 && (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    ... and {scenarios.length - 3} more
                  </Typography>
                )}
              </Paper>
            </Box>
          )}

          {/* Error Display */}
          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}

          {/* Launch Button */}
          <Box sx={{ textAlign: 'center' }}>
            <Button
              variant="contained"
              size="large"
              startIcon={isLaunching ? <CircularProgress size={20} /> : <PlayArrow />}
              onClick={handleLaunch}
              disabled={!scenarios || isLaunching}
              sx={{ minWidth: 200 }}
            >
              {isLaunching ? 'Launching...' : 'Launch Batch'}
            </Button>
          </Box>
        </CardContent>
      </Card>

      {/* Help Section */}
      <Card sx={{ mt: 3 }} elevation={1}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Quick Start Guide
          </Typography>
          <Typography variant="body2" paragraph>
            1. <strong>Upload Scenarios:</strong> Drag and drop or click to upload a JSON file containing your simulation scenarios
          </Typography>
          <Typography variant="body2" paragraph>
            2. <strong>Set Version:</strong> Enter a prompt version identifier to track different configurations
          </Typography>
          <Typography variant="body2" paragraph>
            3. <strong>Launch:</strong> Click "Launch Batch" to start the simulation
          </Typography>
          <Typography variant="body2" color="text.secondary">
            The simulation will run in the background and you can monitor progress on the batch detail page.
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
};

export default LaunchPage;

