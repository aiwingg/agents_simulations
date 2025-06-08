import React, { useState, useMemo } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Paper,
  Chip,
  IconButton,
  ToggleButton,
  ToggleButtonGroup,
  Divider,
  Avatar,
  Card,
  CardContent,
  Tooltip,
  TextField,
  InputAdornment,
} from '@mui/material';
import {
  Close,
  ContentCopy,
  Person,
  Support,
  Search,
  Download,
  Fullscreen,
  FullscreenExit,
} from '@mui/icons-material';
import { toast } from 'sonner';

const TranscriptModal = ({ open, onClose, session }) => {
  const [viewMode, setViewMode] = useState('chat'); // 'chat' or 'json'
  const [searchTerm, setSearchTerm] = useState('');
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Filter conversation history based on search term
  const filteredHistory = useMemo(() => {
    if (!session?.conversation_history || !searchTerm) {
      return session?.conversation_history || [];
    }
    
    return session.conversation_history.filter(entry =>
      entry.content.toLowerCase().includes(searchTerm.toLowerCase()) ||
      entry.speaker.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [session?.conversation_history, searchTerm]);

  const handleCopyTranscript = () => {
    if (!session?.conversation_history) {
      toast.error('No conversation history to copy');
      return;
    }

    const text = session.conversation_history
      .map((entry, index) => `${index + 1}. ${entry.speaker.toUpperCase()}: ${entry.content}`)
      .join('\n\n');

    navigator.clipboard.writeText(text).then(() => {
      toast.success('Transcript copied to clipboard');
    }).catch(() => {
      toast.error('Failed to copy transcript');
    });
  };

  const handleCopyJSON = () => {
    if (!session) {
      toast.error('No session data to copy');
      return;
    }

    navigator.clipboard.writeText(JSON.stringify(session, null, 2)).then(() => {
      toast.success('JSON data copied to clipboard');
    }).catch(() => {
      toast.error('Failed to copy JSON data');
    });
  };

  const handleDownloadTranscript = () => {
    if (!session?.conversation_history) {
      toast.error('No conversation history to download');
      return;
    }

    const text = session.conversation_history
      .map((entry, index) => `${index + 1}. ${entry.speaker.toUpperCase()}: ${entry.content}`)
      .join('\n\n');

    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `transcript_${session.session_id?.slice(0, 8) || 'session'}.txt`;
    link.click();
    URL.revokeObjectURL(url);
    toast.success('Transcript downloaded');
  };

  const handleDownloadJSON = () => {
    if (!session) {
      toast.error('No session data to download');
      return;
    }

    const blob = new Blob([JSON.stringify(session, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `session_${session.session_id?.slice(0, 8) || 'data'}.json`;
    link.click();
    URL.revokeObjectURL(url);
    toast.success('Session data downloaded');
  };

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  if (!session) {
    return null;
  }

  const dialogProps = isFullscreen 
    ? { maxWidth: false, fullWidth: true, PaperProps: { sx: { height: '100vh', maxHeight: '100vh' } } }
    : { maxWidth: 'lg', fullWidth: true, PaperProps: { sx: { height: '80vh' } } };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      {...dialogProps}
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', pb: 1 }}>
        <Box>
          <Typography variant="h6">
            Session Transcript
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
            <Chip 
              label={session.scenario} 
              size="small" 
              color="primary" 
              variant="outlined" 
            />
            <Chip 
              label={`Score: ${session.score}`} 
              size="small" 
              color={session.score === 3 ? 'success' : session.score === 2 ? 'warning' : 'error'} 
            />
            <Chip 
              label={`${session.total_turns} turns`} 
              size="small" 
              variant="outlined" 
            />
            {session.duration_seconds && (
              <Chip 
                label={`${session.duration_seconds.toFixed(1)}s`} 
                size="small" 
                variant="outlined" 
              />
            )}
          </Box>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Tooltip title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}>
            <IconButton onClick={toggleFullscreen}>
              {isFullscreen ? <FullscreenExit /> : <Fullscreen />}
            </IconButton>
          </Tooltip>
          <IconButton onClick={onClose}>
            <Close />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent dividers sx={{ p: 0, display: 'flex', flexDirection: 'column' }}>
        {/* Controls */}
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider', display: 'flex', alignItems: 'center', gap: 2 }}>
          <ToggleButtonGroup
            value={viewMode}
            exclusive
            onChange={(e, newMode) => newMode && setViewMode(newMode)}
            size="small"
          >
            <ToggleButton value="chat">
              Chat View
            </ToggleButton>
            <ToggleButton value="json">
              Raw JSON
            </ToggleButton>
          </ToggleButtonGroup>

          {viewMode === 'chat' && (
            <TextField
              size="small"
              placeholder="Search in conversation..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Search />
                  </InputAdornment>
                ),
              }}
              sx={{ minWidth: 250 }}
            />
          )}

          <Box sx={{ flexGrow: 1 }} />

          <Tooltip title={viewMode === 'chat' ? 'Download transcript' : 'Download JSON'}>
            <IconButton 
              size="small" 
              onClick={viewMode === 'chat' ? handleDownloadTranscript : handleDownloadJSON}
            >
              <Download />
            </IconButton>
          </Tooltip>
        </Box>

        {/* Content */}
        <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
          {viewMode === 'chat' ? (
            <Box>
              {filteredHistory.length > 0 ? (
                <>
                  {searchTerm && (
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="body2" color="text.secondary">
                        Found {filteredHistory.length} of {session.conversation_history.length} messages
                      </Typography>
                    </Box>
                  )}
                  {filteredHistory.map((entry, index) => (
                    <Card 
                      key={index} 
                      sx={{ 
                        mb: 2, 
                        ml: entry.speaker === 'agent' ? 0 : 4,
                        mr: entry.speaker === 'agent' ? 4 : 0,
                      }}
                      elevation={1}
                    >
                      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                          <Avatar 
                            sx={{ 
                              width: 32, 
                              height: 32, 
                              mr: 1,
                              bgcolor: entry.speaker === 'agent' ? 'primary.main' : 'secondary.main'
                            }}
                          >
                            {entry.speaker === 'agent' ? <Support /> : <Person />}
                          </Avatar>
                          <Box>
                            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                              {entry.speaker === 'agent' ? 'Agent' : 'Client'}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              Turn {index + 1}
                            </Typography>
                          </Box>
                        </Box>
                        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                          {entry.content}
                        </Typography>
                      </CardContent>
                    </Card>
                  ))}
                </>
              ) : searchTerm ? (
                <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
                  No messages found matching "{searchTerm}"
                </Typography>
              ) : (
                <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
                  No conversation history available
                </Typography>
              )}
            </Box>
          ) : (
            <Paper sx={{ p: 2, bgcolor: 'grey.50', height: '100%', overflow: 'auto' }}>
              <pre style={{ 
                whiteSpace: 'pre-wrap', 
                fontSize: '12px', 
                fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
                margin: 0,
                lineHeight: 1.5,
                color: '#333',
              }}>
                {JSON.stringify(session, null, 2)}
              </pre>
            </Paper>
          )}
        </Box>
      </DialogContent>

      <DialogActions sx={{ p: 2 }}>
        <Button
          startIcon={<ContentCopy />}
          onClick={viewMode === 'chat' ? handleCopyTranscript : handleCopyJSON}
          variant="outlined"
        >
          Copy {viewMode === 'chat' ? 'Transcript' : 'JSON'}
        </Button>
        <Button onClick={onClose} variant="contained">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default TranscriptModal;

