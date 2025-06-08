import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Container,
  Box,
  Button,
  IconButton,
  Breadcrumbs,
  Link,
} from '@mui/material';
import {
  Home,
  PlayArrow,
  Compare,
  Assessment,
} from '@mui/icons-material';

const Layout = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const getBreadcrumbs = () => {
    const path = location.pathname;
    const breadcrumbs = [];

    if (path === '/') {
      breadcrumbs.push({ label: 'Launch', path: '/', active: true });
    } else if (path.startsWith('/batch/')) {
      const batchId = path.split('/')[2];
      breadcrumbs.push(
        { label: 'Launch', path: '/' },
        { label: `Batch ${batchId.slice(0, 8)}...`, path: path, active: true }
      );
    } else if (path === '/compare') {
      breadcrumbs.push(
        { label: 'Launch', path: '/' },
        { label: 'Compare Runs', path: '/compare', active: true }
      );
    }

    return breadcrumbs;
  };

  const breadcrumbs = getBreadcrumbs();

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {/* App Bar */}
      <AppBar position="static" elevation={1}>
        <Toolbar>
          <Assessment sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            LLM Simulation & Evaluation Service
          </Typography>
          
          {/* Navigation Buttons */}
          <Button
            color="inherit"
            startIcon={<Home />}
            onClick={() => navigate('/')}
            sx={{ mr: 1 }}
          >
            Launch
          </Button>
          <Button
            color="inherit"
            startIcon={<Compare />}
            onClick={() => navigate('/compare')}
          >
            Compare
          </Button>
        </Toolbar>
      </AppBar>

      {/* Breadcrumbs */}
      {breadcrumbs.length > 1 && (
        <Box sx={{ bgcolor: 'grey.100', py: 1 }}>
          <Container maxWidth="xl">
            <Breadcrumbs>
              {breadcrumbs.map((crumb, index) => (
                <Link
                  key={index}
                  color={crumb.active ? 'text.primary' : 'inherit'}
                  href="#"
                  onClick={(e) => {
                    e.preventDefault();
                    if (!crumb.active) {
                      navigate(crumb.path);
                    }
                  }}
                  sx={{
                    textDecoration: 'none',
                    cursor: crumb.active ? 'default' : 'pointer',
                    fontWeight: crumb.active ? 600 : 400,
                  }}
                >
                  {crumb.label}
                </Link>
              ))}
            </Breadcrumbs>
          </Container>
        </Box>
      )}

      {/* Main Content */}
      <Box component="main" sx={{ flexGrow: 1, py: 3 }}>
        <Container maxWidth="xl">
          {children}
        </Container>
      </Box>

      {/* Footer */}
      <Box
        component="footer"
        sx={{
          py: 2,
          px: 2,
          mt: 'auto',
          backgroundColor: 'grey.100',
          borderTop: '1px solid',
          borderColor: 'grey.300',
        }}
      >
        <Container maxWidth="xl">
          <Typography variant="body2" color="text.secondary" align="center">
            LLM Simulation & Evaluation Service - Built with React & Material-UI
          </Typography>
        </Container>
      </Box>
    </Box>
  );
};

export default Layout;

