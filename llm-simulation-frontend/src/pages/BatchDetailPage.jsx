import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Grid,
  Chip,
  Button,
  Alert,
  CircularProgress,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Refresh,
  Download,
  Visibility,
  Compare,
  Error as ErrorIcon,
  CheckCircle,
  Schedule,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';

// Import services and components
import { getBatchStatus, getBatchResults, getBatchSummary, BatchPoller } from '../services/api';
import VirtualizedSessionTable from '../components/VirtualizedSessionTable';
import TranscriptModal from '../components/TranscriptModal';

const BatchDetailPage = () => {
  const { id: batchId } = useParams();
  const navigate = useNavigate();
  const [poller, setPoller] = useState(null);
  const [selectedSession, setSelectedSession] = useState(null);
  const [isTranscriptModalOpen, setIsTranscriptModalOpen] = useState(false);

  // Query for batch status
  const {
    data: batchStatus,
    isLoading: isLoadingStatus,
    error: statusError,
    refetch: refetchStatus,
  } = useQuery({
    queryKey: ['batchStatus', batchId],
    queryFn: () => getBatchStatus(batchId),
    refetchInterval: (data) => {
      // Stop refetching if batch is completed or failed
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false;
      }
      // More aggressive polling for running batches to catch sub-progress updates
      if (data?.status === 'running') {
        return 1000; // Refetch every 1 second for running batches
      }
      return 2000; // Refetch every 2 seconds for other states
    },
    staleTime: 0, // Always consider data stale to ensure fresh updates
    refetchOnWindowFocus: true, // Refetch when user focuses the window
  });

  // Query for batch results (only when completed)
  const {
    data: batchResults,
    isLoading: isLoadingResults,
    error: resultsError,
  } = useQuery({
    queryKey: ['batchResults', batchId],
    queryFn: () => getBatchResults(batchId),
    enabled: batchStatus?.status === 'completed',
  });

  // Query for batch summary (only when completed)
  const {
    data: batchSummary,
    isLoading: isLoadingSummary,
  } = useQuery({
    queryKey: ['batchSummary', batchId],
    queryFn: () => getBatchSummary(batchId),
    enabled: batchStatus?.status === 'completed',
  });

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'running':
        return 'primary';
      case 'launched':
        return 'info';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle />;
      case 'failed':
        return <ErrorIcon />;
      case 'running':
        return <Schedule />;
      default:
        return <Schedule />;
    }
  };

  const handleDownloadResults = async (format) => {
    try {
      const blob = await getBatchResults(batchId, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `batch_${batchId}_results.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success(`Results downloaded as ${format.toUpperCase()}`);
    } catch (err) {
      toast.error(`Failed to download results: ${err.message}`);
    }
  };

  const handleSessionClick = (session) => {
    setSelectedSession(session);
    setIsTranscriptModalOpen(true);
  };

  const handleCompare = () => {
    navigate(`/compare?batch=${batchId}`);
  };

  if (isLoadingStatus) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (statusError) {
    return (
      <Alert severity="error" sx={{ mb: 3 }}>
        Failed to load batch status: {statusError.message}
      </Alert>
    );
  }

  if (!batchStatus) {
    return (
      <Alert severity="warning" sx={{ mb: 3 }}>
        Batch not found
      </Alert>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Batch {batchId.slice(0, 8)}...
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Monitor your simulation batch progress and results
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Refresh">
            <IconButton onClick={() => refetchStatus()}>
              <Refresh />
            </IconButton>
          </Tooltip>
          {batchStatus.status === 'completed' && (
            <Button
              variant="outlined"
              startIcon={<Compare />}
              onClick={handleCompare}
            >
              Compare
            </Button>
          )}
        </Box>
      </Box>

      {/* Status Overview */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                {getStatusIcon(batchStatus.status)}
                <Typography variant="h6" sx={{ ml: 1 }}>
                  Status
                </Typography>
                {batchStatus.status === 'running' && batchStatus.scenarios_in_progress > 0 && (
                  <Box sx={{ ml: 1, display: 'flex', alignItems: 'center' }}>
                    <CircularProgress size={16} thickness={6} />
                  </Box>
                )}
              </Box>
              <Chip
                label={batchStatus.status.toUpperCase()}
                color={getStatusColor(batchStatus.status)}
                variant="filled"
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Progress
              </Typography>
              <Typography variant="h4" color="primary">
                {Math.round(batchStatus.progress || 0)}%
              </Typography>
              <LinearProgress
                variant="determinate"
                value={batchStatus.progress || 0}
                sx={{ mt: 1 }}
              />
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                Last updated: {new Date().toLocaleTimeString()}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Precise: {batchStatus.progress?.toFixed(2) || 0}%
              </Typography>
              {batchStatus.status === 'running' && batchStatus.progress > 0 && (
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                  {(() => {
                    const elapsed = batchStatus.started_at ? 
                      (Date.now() - new Date(batchStatus.started_at).getTime()) / 1000 : 0;
                    const rate = batchStatus.progress / 100;
                    const estimatedTotal = rate > 0 ? elapsed / rate : 0;
                    const remaining = estimatedTotal - elapsed;
                    return remaining > 0 ? 
                      `ETA: ${Math.round(remaining / 60)}m ${Math.round(remaining % 60)}s` : 
                      'Calculating...';
                  })()}
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Scenarios
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {batchStatus.completed_scenarios || 0} / {batchStatus.total_scenarios || 0} completed
              </Typography>
              <Typography variant="body2" color="error">
                {batchStatus.failed_scenarios || 0} failed
              </Typography>
              {batchStatus.scenarios_in_progress > 0 && (
                <Typography variant="body2" color="primary">
                  {batchStatus.scenarios_in_progress} in progress
                </Typography>
              )}
              {batchStatus.current_stage && (
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                  Stage: {batchStatus.current_stage}
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Duration
              </Typography>
              <Typography variant="body2">
                Started: {batchStatus.started_at ? new Date(batchStatus.started_at).toLocaleTimeString() : 'N/A'}
              </Typography>
              {batchStatus.completed_at && (
                <Typography variant="body2">
                  Completed: {new Date(batchStatus.completed_at).toLocaleTimeString()}
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Summary Statistics (when completed) */}
      {batchStatus.status === 'completed' && batchSummary && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Summary Statistics
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={6} md={2}>
                <Typography variant="body2" color="text.secondary">
                  Mean Score
                </Typography>
                <Typography variant="h6">
                  {batchSummary.score_statistics?.mean?.toFixed(2) || 'N/A'}
                </Typography>
              </Grid>
              <Grid item xs={6} md={2}>
                <Typography variant="body2" color="text.secondary">
                  Median Score
                </Typography>
                <Typography variant="h6">
                  {batchSummary.score_statistics?.median?.toFixed(2) || 'N/A'}
                </Typography>
              </Grid>
              <Grid item xs={6} md={2}>
                <Typography variant="body2" color="text.secondary">
                  Success Rate
                </Typography>
                <Typography variant="h6">
                  {(batchSummary.success_rate * 100)?.toFixed(1) || 'N/A'}%
                </Typography>
              </Grid>
              <Grid item xs={6} md={2}>
                <Typography variant="body2" color="text.secondary">
                  Score 1
                </Typography>
                <Typography variant="h6">
                  {batchSummary.score_distribution?.score_1 || 0}
                </Typography>
              </Grid>
              <Grid item xs={6} md={2}>
                <Typography variant="body2" color="text.secondary">
                  Score 2
                </Typography>
                <Typography variant="h6">
                  {batchSummary.score_distribution?.score_2 || 0}
                </Typography>
              </Grid>
              <Grid item xs={6} md={2}>
                <Typography variant="body2" color="text.secondary">
                  Score 3
                </Typography>
                <Typography variant="h6">
                  {batchSummary.score_distribution?.score_3 || 0}
                </Typography>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Download Results */}
      {batchStatus.status === 'completed' && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Download Results
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              <Button
                variant="outlined"
                startIcon={<Download />}
                onClick={() => handleDownloadResults('json')}
              >
                JSON
              </Button>
              <Button
                variant="outlined"
                startIcon={<Download />}
                onClick={() => handleDownloadResults('csv')}
              >
                CSV
              </Button>
              <Button
                variant="outlined"
                startIcon={<Download />}
                onClick={() => handleDownloadResults('ndjson')}
              >
                NDJSON
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Session Results Table */}
      {batchStatus.status === 'completed' && batchResults && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Session Results
            </Typography>
            <VirtualizedSessionTable
              sessions={batchResults.results || []}
              onSessionClick={handleSessionClick}
              onExport={(filteredSessions) => {
                // Handle export of filtered sessions
                const dataStr = JSON.stringify(filteredSessions, null, 2);
                const dataBlob = new Blob([dataStr], { type: 'application/json' });
                const url = URL.createObjectURL(dataBlob);
                const link = document.createElement('a');
                link.href = url;
                link.download = `batch_${batchId}_filtered_sessions.json`;
                link.click();
                URL.revokeObjectURL(url);
                toast.success('Filtered sessions exported');
              }}
            />
          </CardContent>
        </Card>
      )}

      {/* Transcript Modal */}
      <TranscriptModal
        open={isTranscriptModalOpen}
        onClose={() => setIsTranscriptModalOpen(false)}
        session={selectedSession}
      />
    </Box>
  );
};

export default BatchDetailPage;

