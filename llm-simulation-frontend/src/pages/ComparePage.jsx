import React, { useState, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Divider,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Compare,
  Download,
  Refresh,
  Add,
  Remove,
} from '@mui/icons-material';
import { useQuery, useQueries } from '@tanstack/react-query';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { toast } from 'sonner';

// Import services
import { listBatches, getBatchResults, getBatchSummary } from '../services/api';

const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#00ff00'];

// Helper function to clean NaN values from objects
const cleanNaNValues = (obj) => {
  const cleaned = {};
  Object.keys(obj).forEach(key => {
    const value = obj[key];
    if (typeof value === 'number') {
      cleaned[key] = Number.isNaN(value) || !Number.isFinite(value) ? 0 : value;
    } else {
      cleaned[key] = value;
    }
  });
  return cleaned;
};

const ComparePage = () => {
  const [searchParams] = useSearchParams();
  const initialBatchId = searchParams.get('batch');
  
  const [selectedBatches, setSelectedBatches] = useState(
    initialBatchId ? [initialBatchId] : []
  );
  const [comparisonData, setComparisonData] = useState([]);

  // Query for available batches
  const {
    data: batches,
    isLoading: isLoadingBatches,
    error: batchesError,
    refetch: refetchBatches,
  } = useQuery({
    queryKey: ['batches'],
    queryFn: listBatches,
  });

  // Query for batch results and summaries using useQueries for dynamic queries
  const batchResultQueries = useQueries({
    queries: (selectedBatches || []).map(batchId => ({
      queryKey: ['batchResults', batchId],
      queryFn: () => getBatchResults(batchId),
      enabled: !!batchId,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    }))
  });

  const batchSummaryQueries = useQueries({
    queries: (selectedBatches || []).map(batchId => ({
      queryKey: ['batchSummary', batchId],
      queryFn: () => getBatchSummary(batchId),
      enabled: !!batchId,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    }))
  });

  // Combine results and summaries for easier access
  const batchQueries = (selectedBatches || []).map((batchId, index) => ({
    results: batchResultQueries[index] || { data: null, error: null },
    summary: batchSummaryQueries[index] || { data: null, error: null },
  }));

  // Process comparison data
  const processedData = useMemo(() => {
    try {
    const data = [];
    
      (selectedBatches || []).forEach((batchId, index) => {
        if (!batchId) {
          console.warn('Empty batchId at index', index);
          return;
        }

        const resultsQuery = batchQueries?.[index]?.results;
        const summaryQuery = batchQueries?.[index]?.summary;
      
        console.log(`Processing batch ${batchId}:`, {
          resultsQuery: resultsQuery?.data ? 'has data' : 'no data',
          summaryQuery: summaryQuery?.data ? 'has data' : 'no data',
          resultsError: resultsQuery?.error,
          summaryError: summaryQuery?.error
        });
        
        // Only process if both queries succeeded and have data
        if (resultsQuery?.data && summaryQuery?.data && 
            !resultsQuery.error && !summaryQuery.error) {
        const results = resultsQuery.data.results || [];
        const summary = summaryQuery.data;
          
          // Ensure results is an array before processing
          if (!Array.isArray(results)) {
            console.warn(`Results for batch ${batchId} is not an array:`, results);
            return;
          }
        
        // Calculate score distribution
        const scoreDistribution = {
            score_1: (results || []).filter(r => r && r.score === 1).length,
            score_2: (results || []).filter(r => r && r.score === 2).length,
            score_3: (results || []).filter(r => r && r.score === 3).length,
        };
        
        data.push({
            batchId: batchId?.slice?.(0, 8) || 'unknown',
          fullBatchId: batchId,
            totalSessions: results.length || 0,
            meanScore: Number.isNaN(summary?.score_statistics?.mean) ? 0 : (summary?.score_statistics?.mean || 0),
            medianScore: Number.isNaN(summary?.score_statistics?.median) ? 0 : (summary?.score_statistics?.median || 0),
            successRate: Number.isNaN(summary?.success_rate) ? 0 : (summary?.success_rate || 0),
          scoreDistribution,
          results,
          summary,
        });
      }
    });
    
    return data;
    } catch (error) {
      console.error('Error processing comparison data:', error);
      return [];
    }
  }, [selectedBatches, batchQueries]);

  // Prepare chart data
  const chartData = useMemo(() => {
    if (!processedData || processedData.length === 0) {
      return { histogramData: [], metricsData: [] };
    }

    const histogramData = [
      cleanNaNValues({ score: 'Score 1', ...processedData.reduce((acc, batch) => ({ 
        ...acc, 
        [batch.batchId]: batch.scoreDistribution?.score_1 || 0
      }), {}) }),
      cleanNaNValues({ score: 'Score 2', ...processedData.reduce((acc, batch) => ({ 
        ...acc, 
        [batch.batchId]: batch.scoreDistribution?.score_2 || 0
      }), {}) }),
      cleanNaNValues({ score: 'Score 3', ...processedData.reduce((acc, batch) => ({ 
        ...acc, 
        [batch.batchId]: batch.scoreDistribution?.score_3 || 0
      }), {}) }),
    ];

    const metricsData = processedData.map(batch => cleanNaNValues({
      batch: batch.batchId || 'Unknown',
      meanScore: batch.meanScore || 0,
      medianScore: batch.medianScore || 0,
      successRate: (batch.successRate || 0) * 100,
    }));

    // Debug logging for chart data
    console.log('Chart data debug:', {
      histogramData,
      metricsData,
      processedData: processedData.map(batch => ({
        batchId: batch.batchId,
        meanScore: batch.meanScore,
        successRate: batch.successRate,
        scoreDistribution: batch.scoreDistribution
      }))
    });

    // Additional validation
    metricsData.forEach((item, index) => {
      Object.keys(item).forEach(key => {
        if (typeof item[key] === 'number' && (Number.isNaN(item[key]) || !Number.isFinite(item[key]))) {
          console.error(`Found invalid number in metricsData[${index}].${key}:`, item[key]);
        }
      });
    });

    return { histogramData, metricsData };
  }, [processedData]);

  const handleAddBatch = (batchId) => {
    if (!selectedBatches.includes(batchId) && selectedBatches.length < 5) {
      setSelectedBatches([...selectedBatches, batchId]);
    }
  };

  const handleRemoveBatch = (batchId) => {
    setSelectedBatches((selectedBatches || []).filter(id => id !== batchId));
  };

  const handleExportComparison = () => {
    const exportData = {
      comparison_date: new Date().toISOString(),
      batches: processedData,
      charts: chartData,
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `batch_comparison_${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    URL.revokeObjectURL(url);
    toast.success('Comparison data exported');
  };

  const availableBatches = batches?.batches?.filter(batch => 
    batch.status === 'completed' && !(selectedBatches || []).includes(batch.batch_id)
  ) || [];

  // Debug logging
  console.log('ComparePage Debug:', {
    batches,
    selectedBatches,
    batchQueries: batchQueries?.length,
    availableBatches: availableBatches?.length,
    processedData: processedData?.length
  });

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Compare Simulation Runs
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Compare results between different batch runs to analyze performance
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Refresh batches">
            <IconButton onClick={() => refetchBatches()}>
              <Refresh />
            </IconButton>
          </Tooltip>
          {processedData.length > 0 && (
            <Button
              variant="outlined"
              startIcon={<Download />}
              onClick={handleExportComparison}
            >
              Export Comparison
            </Button>
          )}
        </Box>
      </Box>

      {/* Batch Selection */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Select Batches to Compare
          </Typography>
          
          {/* Selected Batches */}
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Selected Batches ({selectedBatches.length}/5)
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {selectedBatches.map(batchId => (
                <Chip
                  key={batchId}
                  label={`${batchId.slice(0, 8)}...`}
                  onDelete={() => handleRemoveBatch(batchId)}
                  color="primary"
                  variant="outlined"
                />
              ))}
              {selectedBatches.length === 0 && (
                <Typography variant="body2" color="text.secondary">
                  No batches selected
                </Typography>
              )}
            </Box>
          </Box>

          {/* Add Batch */}
          {availableBatches.length > 0 && selectedBatches.length < 5 && (
            <Box>
              <FormControl size="small" sx={{ minWidth: 300 }}>
                <InputLabel>Add Batch</InputLabel>
                <Select
                  label="Add Batch"
                  value=""
                  onChange={(e) => handleAddBatch(e.target.value)}
                >
                  {availableBatches.map(batch => (
                    <MenuItem key={batch.batch_id} value={batch.batch_id}>
                      {batch.batch_id.slice(0, 8)}... - {batch.prompt_version} 
                      ({batch.total_scenarios} scenarios)
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>
          )}

          {isLoadingBatches && (
            <Typography variant="body2" color="text.secondary">
              Loading available batches...
            </Typography>
          )}

          {batchesError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              Failed to load batches: {batchesError.message}
            </Alert>
          )}

          {/* Show failed batch queries */}
          {selectedBatches.length > 0 && (
            <Box sx={{ mt: 2 }}>
              {batchQueries.map((queries, index) => {
                const batchId = selectedBatches[index];
                const hasErrors = queries.results.error || queries.summary.error;
                if (hasErrors) {
                  return (
                    <Alert key={batchId} severity="warning" sx={{ mb: 1 }}>
                      <Typography variant="body2">
                        Batch {batchId.slice(0, 8)}... failed to load: 
                        {queries.results.error ? ' Results error. ' : ''}
                        {queries.summary.error ? ' Summary error. ' : ''}
                        <Button 
                          size="small" 
                          onClick={() => handleRemoveBatch(batchId)}
                          sx={{ ml: 1 }}
                        >
                          Remove
                        </Button>
                      </Typography>
                    </Alert>
                  );
                }
                return null;
              })}
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Comparison Results */}
      {processedData.length > 0 ? (
        <>
          {/* Summary Statistics */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Summary Statistics
              </Typography>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Batch ID</TableCell>
                      <TableCell align="right">Total Sessions</TableCell>
                      <TableCell align="right">Mean Score</TableCell>
                      <TableCell align="right">Median Score</TableCell>
                      <TableCell align="right">Success Rate</TableCell>
                      <TableCell align="right">Score 1</TableCell>
                      <TableCell align="right">Score 2</TableCell>
                      <TableCell align="right">Score 3</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {processedData.map((batch, index) => (
                      <TableRow key={batch.fullBatchId}>
                        <TableCell>
                          <Chip 
                            label={batch.batchId} 
                            size="small" 
                            style={{ backgroundColor: COLORS[index % COLORS.length], color: 'white' }}
                          />
                        </TableCell>
                        <TableCell align="right">{batch.totalSessions}</TableCell>
                        <TableCell align="right">{batch.meanScore.toFixed(2)}</TableCell>
                        <TableCell align="right">{batch.medianScore.toFixed(2)}</TableCell>
                        <TableCell align="right">{(batch.successRate * 100).toFixed(1)}%</TableCell>
                        <TableCell align="right">{batch.scoreDistribution.score_1}</TableCell>
                        <TableCell align="right">{batch.scoreDistribution.score_2}</TableCell>
                        <TableCell align="right">{batch.scoreDistribution.score_3}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>

          {/* Charts */}
          {chartData.histogramData && chartData.histogramData.length > 0 && processedData.length > 0 ? (
          <Grid container spacing={3}>
            {/* Score Distribution Histogram */}
            <Grid item xs={12} lg={8}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Score Distribution Comparison
                  </Typography>
                  <ResponsiveContainer width="100%" height={400}>
                    <BarChart data={chartData.histogramData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="score" />
                        <YAxis domain={[0, 'dataMax']} />
                      <RechartsTooltip />
                      <Legend />
                      {processedData.map((batch, index) => (
                        <Bar
                          key={batch.fullBatchId}
                          dataKey={batch.batchId}
                          fill={COLORS[index % COLORS.length]}
                          name={`Batch ${batch.batchId}`}
                        />
                      ))}
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </Grid>

              {/* Simple Metrics Table instead of horizontal chart */}
            <Grid item xs={12} lg={4}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Performance Metrics
                  </Typography>
                    {processedData.map((batch, index) => (
                      <Paper key={batch.fullBatchId} sx={{ p: 2, mb: 2, backgroundColor: COLORS[index % COLORS.length] + '20' }}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 'bold', color: COLORS[index % COLORS.length] }}>
                          Batch {batch.batchId}
                        </Typography>
                        <Box sx={{ mt: 1 }}>
                          <Typography variant="body2">
                            Mean Score: <strong>{batch.meanScore.toFixed(2)}</strong>
                          </Typography>
                          <Typography variant="body2">
                            Success Rate: <strong>{(batch.successRate * 100).toFixed(1)}%</strong>
                          </Typography>
                          <Typography variant="body2">
                            Total Sessions: <strong>{batch.totalSessions}</strong>
                          </Typography>
                        </Box>
                      </Paper>
                    ))}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
          ) : (
            <Card>
              <CardContent sx={{ textAlign: 'center', py: 4 }}>
                <Typography variant="h6" color="text.secondary">
                  Charts will appear when batch data is loaded
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  {selectedBatches.length === 0 
                    ? 'Please select batches to compare' 
                    : 'Loading batch data for visualization...'
                  }
                </Typography>
              </CardContent>
            </Card>
          )}
        </>
      ) : selectedBatches.length > 0 ? (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <Typography variant="h6" gutterBottom>
              Loading Comparison Data...
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Please wait while we fetch the batch results for comparison
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <Compare sx={{ fontSize: 80, color: 'grey.400', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              Select Batches to Compare
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Choose 2 or more completed batches to see side-by-side comparison
              with histograms and statistical analysis.
            </Typography>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default ComparePage;

