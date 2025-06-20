import React, { useState, useEffect } from 'react';
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
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Collapse,
  Skeleton,
} from '@mui/material';
import {
  CloudUpload,
  PlayArrow,
  Description,
  Settings,
  ExpandMore,
  ExpandLess,
} from '@mui/icons-material';
import { toast } from 'sonner';

// Import components
import FileUpload from '../components/FileUpload';
import PromptSpecViewer from '../components/PromptSpecViewer';
import { launchBatch, listPromptSpecs, getPromptSpec } from '../services/api';

const LaunchPage = () => {
  const navigate = useNavigate();
  const [scenarios, setScenarios] = useState(null);
  const [promptSpecs, setPromptSpecs] = useState([]);
  const [selectedSpecName, setSelectedSpecName] = useState('');
  const [selectedSpec, setSelectedSpec] = useState(null);
  const [isLoadingSpecs, setIsLoadingSpecs] = useState(true);
  const [isLoadingSpecContent, setIsLoadingSpecContent] = useState(false);
  const [isLaunching, setIsLaunching] = useState(false);
  const [error, setError] = useState(null);
  const [showSpecViewer, setShowSpecViewer] = useState(false);

  // Load prompt specifications on component mount
  useEffect(() => {
    const loadPromptSpecs = async () => {
      try {
        setIsLoadingSpecs(true);
        const response = await listPromptSpecs();
        setPromptSpecs(response.specifications || []);
        
        // Auto-select default_prompts if available
        const defaultSpec = response.specifications?.find(spec => spec.name === 'default_prompts');
        if (defaultSpec) {
          setSelectedSpecName('default_prompts');
          await loadSpecContent('default_prompts');
        }
      } catch (err) {
        const errorMessage = err.response?.data?.error || err.message || 'Failed to load prompt specifications';
        setError(errorMessage);
        toast.error(errorMessage);
      } finally {
        setIsLoadingSpecs(false);
      }
    };

    loadPromptSpecs();
  }, []);

  const loadSpecContent = async (specName) => {
    if (!specName) return;
    
    try {
      setIsLoadingSpecContent(true);
      const spec = await getPromptSpec(specName);
      setSelectedSpec(spec);
      setShowSpecViewer(true);
    } catch (err) {
      const errorMessage = err.response?.data?.error || err.message || 'Failed to load specification content';
      toast.error(errorMessage);
      setSelectedSpec(null);
    } finally {
      setIsLoadingSpecContent(false);
    }
  };

  const handleSpecChange = async (event) => {
    const specName = event.target.value;
    setSelectedSpecName(specName);
    setSelectedSpec(null);
    setShowSpecViewer(false);
    
    if (specName) {
      await loadSpecContent(specName);
    }
  };

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

    if (!selectedSpecName) {
      toast.error('Please select a prompt specification');
      return;
    }

    setIsLaunching(true);
    setError(null);

    try {
      const response = await launchBatch({
        scenarios: scenarios,
        prompt_spec_name: selectedSpecName,
        prompt_version: selectedSpec?.version || 'v1.0',
        use_tools: true,
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
    <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ mb: 4, textAlign: 'center' }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Launch Simulation Batch
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Upload your scenarios file and configure the simulation parameters
        </Typography>
      </Box>

      <Box sx={{ display: 'flex', gap: 3 }}>
        {/* Left Column - Configuration */}
        <Box sx={{ flex: 1 }}>
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

              {/* Prompt Specification Section */}
              <Box sx={{ mb: 4 }}>
                <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                  <Settings sx={{ mr: 1 }} />
                  Prompt Specification
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Select the prompt configuration to use for this simulation
                </Typography>
                
                {isLoadingSpecs ? (
                  <Skeleton variant="rectangular" height={56} />
                ) : (
                  <FormControl fullWidth sx={{ mb: 2 }}>
                    <InputLabel>Prompt Specification</InputLabel>
                    <Select
                      value={selectedSpecName}
                      onChange={handleSpecChange}
                      label="Prompt Specification"
                    >
                      {promptSpecs.map((spec) => (
                        <MenuItem key={spec.name} value={spec.name}>
                          <Box>
                            <Typography variant="body1">
                              {spec.display_name || spec.name}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              v{spec.version} • {spec.agents?.length || 0} agents • {spec.description}
                            </Typography>
                          </Box>
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                )}

                {selectedSpec && (
                  <Button
                    variant="outlined"
                    onClick={() => setShowSpecViewer(!showSpecViewer)}
                    startIcon={showSpecViewer ? <ExpandLess /> : <ExpandMore />}
                    disabled={isLoadingSpecContent}
                    fullWidth
                  >
                    {isLoadingSpecContent ? 'Loading...' : (showSpecViewer ? 'Hide' : 'Show')} Specification Details
                  </Button>
                )}
              </Box>

              {/* Scenarios Preview */}
              {scenarios && (
                <>
                  <Divider sx={{ my: 3 }} />
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
                </>
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
                  disabled={!scenarios || !selectedSpecName || isLaunching}
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
                2. <strong>Select Specification:</strong> Choose the prompt configuration that defines agent behaviors and capabilities
              </Typography>
              <Typography variant="body2" paragraph>
                3. <strong>Review Configuration:</strong> Optionally view the specification details to understand the agent setup
              </Typography>
              <Typography variant="body2" paragraph>
                4. <strong>Launch:</strong> Click "Launch Batch" to start the simulation
              </Typography>
              <Typography variant="body2" color="text.secondary">
                The simulation will run in the background and you can monitor progress on the batch detail page.
              </Typography>
            </CardContent>
          </Card>
        </Box>

        {/* Right Column - Specification Viewer */}
        {selectedSpec && (
          <Box sx={{ flex: 1 }}>
            <Collapse in={showSpecViewer}>
              <PromptSpecViewer spec={selectedSpec} />
            </Collapse>
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default LaunchPage;

