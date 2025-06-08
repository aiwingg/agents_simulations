# LLM Simulation & Evaluation Service - Frontend

A modern React-based frontend for the LLM Simulation & Evaluation Service, providing an intuitive interface for batch launching, live progress tracking, session inspection, and A/B comparison with responsive data visualization.

## Features

### 🚀 **Batch Management**
- **Drag & Drop File Upload**: Upload scenario JSON files with validation
- **Live Progress Tracking**: Real-time progress bars and status updates
- **WebSocket Integration**: Live updates with polling fallback
- **Cost & Token Monitoring**: Track usage and costs in real-time

### 📊 **Data Visualization**
- **Virtualized Tables**: Handle 10k+ sessions with smooth performance
- **Interactive Charts**: Histograms and statistics using Recharts
- **A/B Comparison**: Side-by-side batch comparison with statistical analysis
- **Export Capabilities**: JSON, CSV, and filtered data export

### 🎨 **User Experience**
- **Material-UI Design**: Professional, responsive interface
- **Error Handling**: Global error boundary with graceful degradation
- **Network Status**: Offline/online detection and notifications
- **Mobile Responsive**: Works seamlessly on all device sizes

### 🔍 **Session Inspection**
- **Transcript Modal**: Chat-style conversation view with search
- **JSON View**: Raw session data with syntax highlighting
- **Copy & Download**: Easy data extraction and sharing
- **Filtering & Sorting**: Advanced table operations

## Quick Start

### Prerequisites
- Node.js 20+ and pnpm
- Backend service running (see `../llm-simulation-service/`)

### Development Setup

1. **Install Dependencies**
   ```bash
   pnpm install
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your API URL
   ```

3. **Start Development Server**
   ```bash
   pnpm run dev
   ```

4. **Open Browser**
   Navigate to `http://localhost:5174`

### Production Build

1. **Build Application**
   ```bash
   pnpm run build
   ```

2. **Preview Build**
   ```bash
   pnpm run preview
   ```

## Docker Deployment

### Single Container
```bash
# Build frontend image
docker build -t llm-simulation-frontend .

# Run container
docker run -p 80:80 \
  -e VITE_API_URL=http://your-backend-url:5000 \
  llm-simulation-frontend
```

### Full Stack with Docker Compose
```bash
# Set environment variables
export OPENAI_API_KEY=your_openai_key

# Start both frontend and backend
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Environment Configuration

### Development (.env.local)
```bash
VITE_API_URL=http://localhost:5000
VITE_WS_BASE_URL=ws://localhost:5000
VITE_ENABLE_DEBUG_MODE=true
```

### Production (.env.production)
```bash
VITE_API_URL=https://api.your-domain.com
VITE_WS_BASE_URL=wss://api.your-domain.com
VITE_ENABLE_DEBUG_MODE=false
```

## API Integration

The frontend communicates with the backend via:

### REST Endpoints
- `POST /batches` - Launch new simulation batch
- `GET /batches/{id}` - Get batch status and progress
- `GET /batches/{id}/results` - Fetch session results
- `GET /batches` - List all batches for comparison

### WebSocket Events
- `batch_progress` - Real-time progress updates
- `session_completed` - Individual session completion
- `batch_completed` - Batch completion notification

## Performance Features

### Virtualization
- **React Virtual**: Efficiently renders 10k+ table rows
- **Lazy Loading**: Components load on demand
- **Memoization**: Optimized re-rendering with React.memo

### Optimization
- **Code Splitting**: Automatic route-based splitting
- **Asset Optimization**: Compressed images and fonts
- **Caching**: Aggressive caching for static assets

## Architecture

```
src/
├── components/          # Reusable UI components
│   ├── ErrorBoundary.jsx
│   ├── FileUpload.jsx
│   ├── Layout.jsx
│   ├── NetworkStatus.jsx
│   ├── TranscriptModal.jsx
│   └── VirtualizedSessionTable.jsx
├── pages/              # Route components
│   ├── BatchDetailPage.jsx
│   ├── ComparePage.jsx
│   ├── LaunchPage.jsx
│   └── NotFoundPage.jsx
├── services/           # API and external services
│   └── api.js
└── App.jsx            # Main application component
```

## Browser Support

- **Modern Browsers**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Mobile**: iOS Safari 14+, Chrome Mobile 90+
- **Features**: ES2020, WebSockets, File API, Drag & Drop

## Development

### Available Scripts
- `pnpm run dev` - Start development server
- `pnpm run build` - Build for production
- `pnpm run preview` - Preview production build
- `pnpm run lint` - Run ESLint
- `pnpm run format` - Format code with Prettier

### Code Style
- **ESLint**: Enforced code quality rules
- **Prettier**: Consistent code formatting
- **Material-UI**: Component library and design system

## Troubleshooting

### Common Issues

**Build Fails**
```bash
# Clear cache and reinstall
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

**API Connection Issues**
- Check `VITE_API_URL` in environment file
- Verify backend service is running
- Check CORS configuration on backend

**Performance Issues**
- Enable React DevTools Profiler
- Check virtualization is working in large tables
- Monitor memory usage in browser DevTools

### Debug Mode
Enable debug mode for additional logging:
```bash
VITE_ENABLE_DEBUG_MODE=true pnpm run dev
```

## Contributing

1. Follow the existing code style and patterns
2. Add tests for new components
3. Update documentation for new features
4. Ensure responsive design works on all devices

## License

MIT License - see LICENSE file for details.

---

**Built with React, Material-UI, and modern web technologies** 🚀

