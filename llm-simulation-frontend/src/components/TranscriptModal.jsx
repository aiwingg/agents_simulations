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
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Collapse,
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
  Build,
  Code,
  ExpandMore,
  Assessment,
  PlayArrow,
  CheckCircle,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { toast } from 'sonner';

const TranscriptModal = ({ open, onClose, session }) => {
  const [viewMode, setViewMode] = useState('chat'); // 'chat' or 'json'
  const [searchTerm, setSearchTerm] = useState('');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showToolDetails, setShowToolDetails] = useState({});

  // Enhanced filter for conversation history including tool calls and results
  const filteredHistory = useMemo(() => {
    if (!session?.conversation_history || !searchTerm) {
      return session?.conversation_history || [];
    }
    
    return session.conversation_history.filter(entry => {
      // Search in content
      const contentMatch = entry.content?.toLowerCase().includes(searchTerm.toLowerCase());
      
      // Search in speaker
      const speakerMatch = entry.speaker?.toLowerCase().includes(searchTerm.toLowerCase());
      
      // Search in tool calls
      const toolCallsMatch = entry.tool_calls?.some(call => 
        call.function?.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        call.function?.arguments?.toLowerCase().includes(searchTerm.toLowerCase())
      );
      
      // Search in tool results
      const toolResultsMatch = entry.tool_results?.some(result => 
        JSON.stringify(result).toLowerCase().includes(searchTerm.toLowerCase())
      );
      
      return contentMatch || speakerMatch || toolCallsMatch || toolResultsMatch;
    });
  }, [session?.conversation_history, searchTerm]);

  // Helper function to determine if speaker is an agent
  const isAgentSpeaker = (speaker) => {
    return speaker && speaker.startsWith('agent_');
  };

  // Helper function to get display name for speaker
  const getSpeakerDisplayName = (entry) => {
    if (!entry) return 'Unknown';
    if (entry.speaker_display) return entry.speaker_display;
    const speaker = typeof entry === 'string' ? entry : entry.speaker;
    if (!speaker) return 'Unknown';
    if (speaker === 'client') return 'Client';
    if (speaker.startsWith('agent_')) {
      const agentType = speaker.replace('agent_', '');
      return agentType === 'agent' ? 'Agent' : `${agentType.charAt(0).toUpperCase() + agentType.slice(1)} Agent`;
    }
    return speaker.charAt(0).toUpperCase() + speaker.slice(1);
  };

  const toggleToolDetails = (entryIndex) => {
    setShowToolDetails(prev => ({
      ...prev,
      [entryIndex]: !prev[entryIndex]
    }));
  };

  const renderToolCalls = (toolCalls, entryIndex) => {
    if (!toolCalls || toolCalls.length === 0) return null;

    return (
      <Box sx={{ mt: 2 }}>
        <Button
          size="small"
          startIcon={<Build />}
          onClick={() => toggleToolDetails(entryIndex)}
          sx={{ mb: 1 }}
          variant="outlined"
          color="primary"
        >
          {toolCalls.length} Tool Call{toolCalls.length > 1 ? 's' : ''} Used
        </Button>
        
        <Collapse in={showToolDetails[entryIndex]}>
          <Box sx={{ ml: 2 }}>
            {toolCalls.map((call, index) => (
              <Card key={index} sx={{ mb: 1, bgcolor: 'primary.50' }}>
                <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <PlayArrow sx={{ mr: 1, color: 'primary.main' }} />
                    <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                      {call.function?.name || 'Unknown Tool'}
                    </Typography>
                    <Chip 
                      label="Tool Call" 
                      size="small" 
                      color="primary" 
                      variant="outlined" 
                      sx={{ ml: 1 }} 
                    />
                  </Box>
                  {call.function?.arguments && (
                    <Paper sx={{ p: 1, bgcolor: 'background.paper', mt: 1 }}>
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                        Arguments:
                      </Typography>
                      <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                        {call.function.arguments}
                      </Typography>
                    </Paper>
                  )}
                </CardContent>
              </Card>
            ))}
          </Box>
        </Collapse>
      </Box>
    );
  };

  const renderToolResults = (toolResults, entryIndex) => {
    if (!toolResults || toolResults.length === 0) return null;

    return (
      <Box sx={{ mt: 2 }}>
        <Button
          size="small"
          startIcon={<CheckCircle />}
          onClick={() => toggleToolDetails(`results_${entryIndex}`)}
          sx={{ mb: 1 }}
          variant="outlined"
          color="success"
        >
          {toolResults.length} Tool Result{toolResults.length > 1 ? 's' : ''}
        </Button>
        
        <Collapse in={showToolDetails[`results_${entryIndex}`]}>
          <Box sx={{ ml: 2 }}>
            {toolResults.map((result, index) => (
              <Card key={index} sx={{ mb: 1, bgcolor: 'success.50' }}>
                <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <CheckCircle sx={{ mr: 1, color: 'success.main' }} />
                    <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                      Tool Response #{index + 1}
                    </Typography>
                    <Chip 
                      label="Result" 
                      size="small" 
                      color="success" 
                      variant="outlined" 
                      sx={{ ml: 1 }} 
                    />
                  </Box>
                  <Paper sx={{ p: 1, bgcolor: 'background.paper', mt: 1 }}>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                      {typeof result === 'object' ? JSON.stringify(result, null, 2) : String(result)}
                    </Typography>
                  </Paper>
                </CardContent>
              </Card>
            ))}
          </Box>
        </Collapse>
      </Box>
    );
  };

  const renderEvaluatorComment = () => {
    if (!session?.comment) return null;

    return (
      <Card sx={{ mb: 2, bgcolor: 'warning.50', border: '1px solid', borderColor: 'warning.200' }}>
        <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            <Assessment sx={{ mr: 1, color: 'warning.main' }} />
            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
              Evaluator's Comment
            </Typography>
            <Chip 
              label={`Score: ${session.score}/3`}
              size="small" 
              color={session.score === 3 ? 'success' : session.score === 2 ? 'warning' : 'error'} 
              sx={{ ml: 1 }} 
            />
          </Box>
          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', fontStyle: 'italic' }}>
            {session.comment}
          </Typography>
        </CardContent>
      </Card>
    );
  };

  const handleCopyTranscript = () => {
    if (!session?.conversation_history) {
      toast.error('No conversation history to copy');
      return;
    }

    let text = '';
    
    // Add evaluator comment if present
    if (session.comment) {
      text += `EVALUATOR'S COMMENT (Score: ${session.score}/3):\n${session.comment}\n\n`;
      text += '='.repeat(50) + '\nCONVERSATION TRANSCRIPT\n' + '='.repeat(50) + '\n\n';
    }

    text += session.conversation_history
      .map((entry, index) => {
        let entryText = `${index + 1}. ${getSpeakerDisplayName(entry).toUpperCase()}: ${entry.content || '[No content]'}`;
        
        // Add tool calls information
        if (entry.tool_calls && entry.tool_calls.length > 0) {
          entryText += '\n   🔧 TOOL CALLS:';
          entry.tool_calls.forEach((call, callIndex) => {
            entryText += `\n      ${callIndex + 1}. ${call.function?.name || 'Unknown Tool'}`;
            if (call.function?.arguments) {
              entryText += `\n         Arguments: ${call.function.arguments}`;
            }
          });
        }
        
        // Add tool results information
        if (entry.tool_results && entry.tool_results.length > 0) {
          entryText += '\n   📋 TOOL RESULTS:';
          entry.tool_results.forEach((result, resultIndex) => {
            entryText += `\n      ${resultIndex + 1}. ${typeof result === 'object' ? JSON.stringify(result, null, 2) : String(result)}`;
          });
        }
        
        return entryText;
      })
      .join('\n\n');

    navigator.clipboard.writeText(text).then(() => {
      toast.success('Enhanced transcript copied to clipboard');
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

    let text = '';
    
    // Add evaluator comment if present
    if (session.comment) {
      text += `EVALUATOR'S COMMENT (Score: ${session.score}/3):\n${session.comment}\n\n`;
      text += '='.repeat(50) + '\nCONVERSATION TRANSCRIPT\n' + '='.repeat(50) + '\n\n';
    }

    text += session.conversation_history
      .map((entry, index) => {
        let entryText = `${index + 1}. ${getSpeakerDisplayName(entry).toUpperCase()}: ${entry.content || '[No content]'}`;
        
        // Add tool calls information
        if (entry.tool_calls && entry.tool_calls.length > 0) {
          entryText += '\n   🔧 TOOL CALLS:';
          entry.tool_calls.forEach((call, callIndex) => {
            entryText += `\n      ${callIndex + 1}. ${call.function?.name || 'Unknown Tool'}`;
            if (call.function?.arguments) {
              entryText += `\n         Arguments: ${call.function.arguments}`;
            }
          });
        }
        
        // Add tool results information
        if (entry.tool_results && entry.tool_results.length > 0) {
          entryText += '\n   📋 TOOL RESULTS:';
          entry.tool_results.forEach((result, resultIndex) => {
            entryText += `\n      ${resultIndex + 1}. ${typeof result === 'object' ? JSON.stringify(result, null, 2) : String(result)}`;
          });
        }
        
        return entryText;
      })
      .join('\n\n');

    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `enhanced_transcript_${session.session_id?.slice(0, 8) || 'session'}.txt`;
    link.click();
    URL.revokeObjectURL(url);
    toast.success('Enhanced transcript downloaded');
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
              placeholder="Search in conversation, tool calls, and results..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Search />
                  </InputAdornment>
                ),
              }}
              sx={{ minWidth: 300 }}
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
              {/* Evaluator Comment */}
              {renderEvaluatorComment()}
              
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
                        ml: isAgentSpeaker(entry.speaker) ? 0 : 4,
                        mr: isAgentSpeaker(entry.speaker) ? 4 : 0,
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
                              bgcolor: isAgentSpeaker(entry.speaker) ? 'primary.main' : 'secondary.main'
                            }}
                          >
                            {isAgentSpeaker(entry.speaker) ? <Support /> : <Person />}
                          </Avatar>
                          <Box sx={{ flex: 1 }}>
                            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                              {getSpeakerDisplayName(entry)}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              Turn {entry.turn || index + 1}
                              {entry.timestamp && (
                                <> • {new Date(entry.timestamp).toLocaleTimeString()}</>
                              )}
                            </Typography>
                          </Box>
                          {/* Tool Indicators */}
                          <Box sx={{ display: 'flex', gap: 0.5 }}>
                            {entry.tool_calls && entry.tool_calls.length > 0 && (
                              <Chip 
                                icon={<Build />}
                                label={entry.tool_calls.length}
                                size="small" 
                                color="primary" 
                                variant="outlined"
                              />
                            )}
                            {entry.tool_results && entry.tool_results.length > 0 && (
                              <Chip 
                                icon={<CheckCircle />}
                                label={entry.tool_results.length}
                                size="small" 
                                color="success" 
                                variant="outlined"
                              />
                            )}
                          </Box>
                        </Box>
                        
                        {/* Message Content */}
                        {entry.content && (
                          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', mb: entry.tool_calls || entry.tool_results ? 1 : 0 }}>
                            {entry.content}
                          </Typography>
                        )}
                        
                        {/* Tool Calls */}
                        {renderToolCalls(entry.tool_calls, index)}
                        
                        {/* Tool Results */}
                        {renderToolResults(entry.tool_results, index)}
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

