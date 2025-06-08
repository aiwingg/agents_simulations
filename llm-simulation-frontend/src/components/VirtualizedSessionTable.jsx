import React, { useMemo, useState } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Chip,
  TextField,
  InputAdornment,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Toolbar,
  Tooltip,
  TableContainer,
  Table,
  TableHead,
  TableRow,
  TableCell,
} from '@mui/material';
import {
  Visibility,
  Search,
  FilterList,
  Download,
  Sort,
} from '@mui/icons-material';

const VirtualizedSessionTable = ({ sessions = [], onSessionClick, onExport }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [scoreFilter, setScoreFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sortBy, setSortBy] = useState('session_id');
  const [sortOrder, setSortOrder] = useState('asc');

  // Filter and sort sessions
  const filteredAndSortedSessions = useMemo(() => {
    let filtered = sessions.filter(session => {
      const matchesSearch = !searchTerm || 
        session.session_id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        session.scenario?.toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchesScore = scoreFilter === 'all' || session.score?.toString() === scoreFilter;
      const matchesStatus = statusFilter === 'all' || session.status === statusFilter;
      
      return matchesSearch && matchesScore && matchesStatus;
    });

    // Sort sessions
    filtered.sort((a, b) => {
      let aVal = a[sortBy];
      let bVal = b[sortBy];
      
      if (typeof aVal === 'string') {
        aVal = aVal?.toLowerCase() || '';
        bVal = bVal?.toLowerCase() || '';
      }
      
      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });

    return filtered;
  }, [sessions, searchTerm, scoreFilter, statusFilter, sortBy, sortOrder]);

  // Virtual table setup
  const parentRef = React.useRef();
  const rowVirtualizer = useVirtualizer({
    count: filteredAndSortedSessions.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 60, // Estimated row height
    overscan: 10, // Render extra rows for smooth scrolling
  });

  const getScoreColor = (score) => {
    switch (score) {
      case 3:
        return 'success';
      case 2:
        return 'warning';
      case 1:
        return 'error';
      default:
        return 'default';
    }
  };

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('asc');
    }
  };

  const formatDuration = (seconds) => {
    if (!seconds) return 'N/A';
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
  };

  if (sessions.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 8 }}>
        <Typography variant="h6" color="text.secondary" gutterBottom>
          No session results available
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Session results will appear here once the batch is completed
        </Typography>
      </Box>
    );
  }

  return (
    <Paper sx={{ height: 600, display: 'flex', flexDirection: 'column' }}>
      {/* Toolbar with filters and search */}
      <Toolbar sx={{ borderBottom: 1, borderColor: 'divider', gap: 2, flexWrap: 'wrap' }}>
        <TextField
          size="small"
          placeholder="Search sessions..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search />
              </InputAdornment>
            ),
          }}
          sx={{ minWidth: 200 }}
        />
        
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Score</InputLabel>
          <Select
            value={scoreFilter}
            label="Score"
            onChange={(e) => setScoreFilter(e.target.value)}
          >
            <MenuItem value="all">All Scores</MenuItem>
            <MenuItem value="3">Score 3</MenuItem>
            <MenuItem value="2">Score 2</MenuItem>
            <MenuItem value="1">Score 1</MenuItem>
          </Select>
        </FormControl>

        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Status</InputLabel>
          <Select
            value={statusFilter}
            label="Status"
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <MenuItem value="all">All Status</MenuItem>
            <MenuItem value="completed">Completed</MenuItem>
            <MenuItem value="failed">Failed</MenuItem>
            <MenuItem value="running">Running</MenuItem>
          </Select>
        </FormControl>

        <Box sx={{ flexGrow: 1 }} />
        
        <Typography variant="body2" color="text.secondary">
          {filteredAndSortedSessions.length} of {sessions.length} sessions
        </Typography>

        {onExport && (
          <Tooltip title="Export filtered results">
            <IconButton onClick={() => onExport(filteredAndSortedSessions)}>
              <Download />
            </IconButton>
          </Tooltip>
        )}
      </Toolbar>

      {/* Table Header */}
      <TableContainer sx={{ flexShrink: 0 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell 
                sx={{ cursor: 'pointer', userSelect: 'none' }}
                onClick={() => handleSort('session_id')}
              >
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  Session ID
                  <Sort sx={{ ml: 0.5, fontSize: 16 }} />
                </Box>
              </TableCell>
              <TableCell 
                sx={{ cursor: 'pointer', userSelect: 'none' }}
                onClick={() => handleSort('scenario')}
              >
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  Scenario
                  <Sort sx={{ ml: 0.5, fontSize: 16 }} />
                </Box>
              </TableCell>
              <TableCell 
                sx={{ cursor: 'pointer', userSelect: 'none' }}
                onClick={() => handleSort('score')}
              >
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  Score
                  <Sort sx={{ ml: 0.5, fontSize: 16 }} />
                </Box>
              </TableCell>
              <TableCell 
                sx={{ cursor: 'pointer', userSelect: 'none' }}
                onClick={() => handleSort('total_turns')}
              >
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  Turns
                  <Sort sx={{ ml: 0.5, fontSize: 16 }} />
                </Box>
              </TableCell>
              <TableCell 
                sx={{ cursor: 'pointer', userSelect: 'none' }}
                onClick={() => handleSort('duration_seconds')}
              >
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  Duration
                  <Sort sx={{ ml: 0.5, fontSize: 16 }} />
                </Box>
              </TableCell>
              <TableCell 
                sx={{ cursor: 'pointer', userSelect: 'none' }}
                onClick={() => handleSort('status')}
              >
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  Status
                  <Sort sx={{ ml: 0.5, fontSize: 16 }} />
                </Box>
              </TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
        </Table>
      </TableContainer>

      {/* Virtualized Table Body */}
      <Box
        ref={parentRef}
        sx={{
          flex: 1,
          overflow: 'auto',
          position: 'relative',
        }}
      >
        <div
          style={{
            height: `${rowVirtualizer.getTotalSize()}px`,
            width: '100%',
            position: 'relative',
          }}
        >
          {rowVirtualizer.getVirtualItems().map((virtualRow) => {
            const session = filteredAndSortedSessions[virtualRow.index];
            return (
              <div
                key={virtualRow.key}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: `${virtualRow.size}px`,
                  transform: `translateY(${virtualRow.start}px)`,
                  display: 'flex',
                  alignItems: 'center',
                  borderBottom: '1px solid #e0e0e0',
                  padding: '0 16px',
                  backgroundColor: virtualRow.index % 2 === 0 ? '#fafafa' : '#ffffff',
                  '&:hover': {
                    backgroundColor: '#f5f5f5',
                  },
                }}
              >
                {/* Session ID */}
                <Box sx={{ width: '15%', pr: 1 }}>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                    {session.session_id?.slice(0, 8) || 'N/A'}...
                  </Typography>
                </Box>

                {/* Scenario */}
                <Box sx={{ width: '20%', pr: 1 }}>
                  <Typography variant="body2" noWrap>
                    {session.scenario || 'N/A'}
                  </Typography>
                </Box>

                {/* Score */}
                <Box sx={{ width: '10%', pr: 1 }}>
                  <Chip
                    label={session.score || 'N/A'}
                    color={getScoreColor(session.score)}
                    size="small"
                  />
                </Box>

                {/* Turns */}
                <Box sx={{ width: '10%', pr: 1 }}>
                  <Typography variant="body2">
                    {session.total_turns || 'N/A'}
                  </Typography>
                </Box>

                {/* Duration */}
                <Box sx={{ width: '15%', pr: 1 }}>
                  <Typography variant="body2">
                    {formatDuration(session.duration_seconds)}
                  </Typography>
                </Box>

                {/* Status */}
                <Box sx={{ width: '15%', pr: 1 }}>
                  <Chip
                    label={session.status || 'unknown'}
                    color={session.status === 'completed' ? 'success' : 'default'}
                    size="small"
                    variant="outlined"
                  />
                </Box>

                {/* Actions */}
                <Box sx={{ width: '15%' }}>
                  <Tooltip title="View transcript">
                    <IconButton
                      size="small"
                      onClick={() => onSessionClick && onSessionClick(session)}
                      disabled={!session.conversation_history}
                    >
                      <Visibility />
                    </IconButton>
                  </Tooltip>
                </Box>
              </div>
            );
          })}
        </div>
      </Box>

      {/* Footer with performance info */}
      <Box sx={{ p: 1, borderTop: 1, borderColor: 'divider', bgcolor: 'grey.50' }}>
        <Typography variant="caption" color="text.secondary">
          Virtualized table rendering {rowVirtualizer.getVirtualItems().length} of {filteredAndSortedSessions.length} rows
        </Typography>
      </Box>
    </Paper>
  );
};

export default VirtualizedSessionTable;

