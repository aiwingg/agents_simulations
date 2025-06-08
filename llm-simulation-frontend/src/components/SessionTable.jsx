import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Chip,
  Typography,
  Box,
} from '@mui/material';
import {
  Visibility,
} from '@mui/icons-material';

const SessionTable = ({ sessions = [], onSessionClick }) => {
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

  if (sessions.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography variant="body2" color="text.secondary">
          No session results available
        </Typography>
      </Box>
    );
  }

  return (
    <TableContainer component={Paper} sx={{ maxHeight: 600 }}>
      <Table stickyHeader>
        <TableHead>
          <TableRow>
            <TableCell>Session ID</TableCell>
            <TableCell>Scenario</TableCell>
            <TableCell>Score</TableCell>
            <TableCell>Turns</TableCell>
            <TableCell>Duration</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {sessions.slice(0, 100).map((session, index) => (
            <TableRow key={session.session_id || index} hover>
              <TableCell>
                <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                  {session.session_id?.slice(0, 8) || 'N/A'}...
                </Typography>
              </TableCell>
              <TableCell>{session.scenario || 'N/A'}</TableCell>
              <TableCell>
                <Chip
                  label={session.score || 'N/A'}
                  color={getScoreColor(session.score)}
                  size="small"
                />
              </TableCell>
              <TableCell>{session.total_turns || 'N/A'}</TableCell>
              <TableCell>
                {session.duration_seconds ? `${session.duration_seconds.toFixed(1)}s` : 'N/A'}
              </TableCell>
              <TableCell>
                <Chip
                  label={session.status || 'unknown'}
                  color={session.status === 'completed' ? 'success' : 'default'}
                  size="small"
                  variant="outlined"
                />
              </TableCell>
              <TableCell>
                <IconButton
                  size="small"
                  onClick={() => onSessionClick && onSessionClick(session)}
                  disabled={!session.conversation_history}
                >
                  <Visibility />
                </IconButton>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {sessions.length > 100 && (
        <Box sx={{ p: 2, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            Showing first 100 sessions. Full virtualization will be implemented in Phase 5.
          </Typography>
        </Box>
      )}
    </TableContainer>
  );
};

export default SessionTable;

