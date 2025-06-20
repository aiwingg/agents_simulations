import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Paper,
  Divider,
  Tooltip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
} from '@mui/material';
import {
  ExpandMore,
  ContentCopy,
  Visibility,
  Person,
  SmartToy,
  Gavel,
  Build,
  SwapHoriz,
} from '@mui/icons-material';
import { toast } from 'sonner';

const PromptSpecViewer = ({ spec, onClose }) => {
  const [expandedAgent, setExpandedAgent] = useState(false);
  const [viewingFullPrompt, setViewingFullPrompt] = useState(null);

  if (!spec) return null;

  const handleAccordionChange = (agent) => (event, isExpanded) => {
    setExpandedAgent(isExpanded ? agent : false);
  };

  const copyToClipboard = (text, label) => {
    navigator.clipboard.writeText(text).then(() => {
      toast.success(`${label} copied to clipboard`);
    }).catch(() => {
      toast.error('Failed to copy to clipboard');
    });
  };

  const truncatePrompt = (prompt, maxLength = 200) => {
    if (prompt.length <= maxLength) return prompt;
    return prompt.substring(0, maxLength) + '...';
  };

  const getAgentIcon = (agentKey) => {
    switch (agentKey) {
      case 'agent':
        return <Person />;
      case 'client':
        return <SmartToy />;
      case 'evaluator':
        return <Gavel />;
      default:
        return <Person />;
    }
  };

  const getAgentColor = (agentKey) => {
    switch (agentKey) {
      case 'agent':
        return 'primary';
      case 'client':
        return 'secondary';
      case 'evaluator':
        return 'success';
      default:
        return 'default';
    }
  };

  return (
    <>
      <Card elevation={3}>
        <CardContent sx={{ p: 3 }}>
          {/* Header */}
          <Box sx={{ mb: 3 }}>
            <Typography variant="h5" gutterBottom>
              {spec.name}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <Chip label={`v${spec.version}`} size="small" color="primary" />
              <Typography variant="body2" color="text.secondary">
                {spec.description}
              </Typography>
            </Box>
            <Typography variant="body2" color="text.secondary">
              {Object.keys(spec.agents).length} agents configured
            </Typography>
          </Box>

          <Divider sx={{ mb: 3 }} />

          {/* Agents */}
          <Box>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
              <Build sx={{ mr: 1 }} />
              Agent Configurations
            </Typography>

            {Object.entries(spec.agents).map(([agentKey, agent]) => (
              <Accordion
                key={agentKey}
                expanded={expandedAgent === agentKey}
                onChange={handleAccordionChange(agentKey)}
                sx={{ mb: 2 }}
              >
                <AccordionSummary
                  expandIcon={<ExpandMore />}
                  sx={{
                    bgcolor: 'grey.50',
                    '&:hover': { bgcolor: 'grey.100' },
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                    <Chip
                      icon={getAgentIcon(agentKey)}
                      label={agent.name || agentKey}
                      color={getAgentColor(agentKey)}
                      size="small"
                    />
                    <Typography variant="body2" color="text.secondary">
                      {agent.description}
                    </Typography>
                    <Box sx={{ ml: 'auto', display: 'flex', gap: 1 }}>
                      {agent.tools && agent.tools.length > 0 && (
                        <Chip
                          label={`${agent.tools.length} tools`}
                          size="small"
                          variant="outlined"
                        />
                      )}
                      {agent.handoffs && Object.keys(agent.handoffs).length > 0 && (
                        <Chip
                          icon={<SwapHoriz />}
                          label={`${Object.keys(agent.handoffs).length} handoffs`}
                          size="small"
                          variant="outlined"
                          color="info"
                        />
                      )}
                    </Box>
                  </Box>
                </AccordionSummary>

                <AccordionDetails>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {/* Prompt Preview */}
                    <Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="subtitle2">System Prompt</Typography>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <Tooltip title="View full prompt">
                            <IconButton
                              size="small"
                              onClick={() => setViewingFullPrompt({ agentKey, agent })}
                            >
                              <Visibility />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Copy prompt">
                            <IconButton
                              size="small"
                              onClick={() => copyToClipboard(agent.prompt, `${agent.name} prompt`)}
                            >
                              <ContentCopy />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </Box>
                      <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                        <Typography
                          variant="body2"
                          sx={{
                            fontFamily: 'monospace',
                            whiteSpace: 'pre-wrap',
                            fontSize: '0.8rem',
                          }}
                        >
                          {truncatePrompt(agent.prompt)}
                        </Typography>
                      </Paper>
                    </Box>

                    {/* Tools */}
                    {agent.tools && agent.tools.length > 0 && (
                      <Box>
                        <Typography variant="subtitle2" gutterBottom>
                          Available Tools
                        </Typography>
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                          {agent.tools.map((tool) => (
                            <Chip
                              key={tool}
                              label={tool}
                              size="small"
                              variant="outlined"
                              sx={{ fontFamily: 'monospace' }}
                            />
                          ))}
                        </Box>
                      </Box>
                    )}

                    {/* Handoffs */}
                    {agent.handoffs && Object.keys(agent.handoffs).length > 0 && (
                      <Box>
                        <Typography variant="subtitle2" gutterBottom>
                          Handoff Capabilities
                        </Typography>
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                          {Object.entries(agent.handoffs).map(([targetAgent, description]) => (
                            <Paper key={targetAgent} sx={{ p: 2, bgcolor: 'blue.50' }}>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                                <SwapHoriz color="info" />
                                <Typography variant="body2" fontWeight="medium">
                                  handoff_{targetAgent}
                                </Typography>
                              </Box>
                              <Typography variant="body2" color="text.secondary">
                                {description}
                              </Typography>
                            </Paper>
                          ))}
                        </Box>
                      </Box>
                    )}
                  </Box>
                </AccordionDetails>
              </Accordion>
            ))}
          </Box>
        </CardContent>
      </Card>

      {/* Full Prompt Dialog */}
      <Dialog
        open={!!viewingFullPrompt}
        onClose={() => setViewingFullPrompt(null)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {viewingFullPrompt?.agent.name} - System Prompt
        </DialogTitle>
        <DialogContent>
          <Paper sx={{ p: 2, bgcolor: 'grey.50', maxHeight: 400, overflow: 'auto' }}>
            <Typography
              variant="body2"
              sx={{
                fontFamily: 'monospace',
                whiteSpace: 'pre-wrap',
                fontSize: '0.8rem',
              }}
            >
              {viewingFullPrompt?.agent.prompt}
            </Typography>
          </Paper>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() =>
              copyToClipboard(
                viewingFullPrompt?.agent.prompt,
                `${viewingFullPrompt?.agent.name} prompt`
              )
            }
            startIcon={<ContentCopy />}
          >
            Copy
          </Button>
          <Button onClick={() => setViewingFullPrompt(null)}>Close</Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default PromptSpecViewer; 