# LLM Agents Simulation & Evaluation Service

A comprehensive platform for simulating and evaluating conversations between LLM agents and customers, designed for testing and improving conversational AI systems.

## 🚀 Features

- **Batch Conversation Simulation**: Run multiple conversation scenarios in parallel
- **Real-time Progress Tracking**: Monitor simulation progress with live updates
- **Conversation Evaluation**: Automated scoring and evaluation of conversation quality
- **Result Analytics**: Comprehensive statistics and summary reports
- **Persistent Storage**: All results persist across server restarts
- **Export Capabilities**: Download results in CSV and NDJSON formats
- **Modern Web Interface**: React-based frontend with real-time updates
- **RESTful API**: Complete API for integration with other systems

## 🏗️ Architecture

The platform consists of two main components:

### Backend (`llm-simulation-service`)
- **Flask-based REST API** with comprehensive endpoints
- **Async batch processing** with configurable concurrency
- **OpenAI GPT integration** for conversation simulation and evaluation
- **Persistent storage system** with JSON-based metadata
- **Comprehensive logging** and error handling

### Frontend (`llm-simulation-frontend`)
- **React + Vite** for fast development and building
- **TanStack Query** for efficient data fetching and caching
- **Real-time updates** with polling for live progress tracking
- **Interactive charts** using Chart.js for result visualization
- **Responsive design** with modern UI components

## 📋 Prerequisites

- **Python 3.8+** with pip
- **Node.js 16+** with pnpm
- **OpenAI API Key** for GPT integration

## 🛠️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/aiwingg/agents_simulations.git
cd agents_simulations
```

### 2. Backend Setup

```bash
cd llm-simulation-service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Frontend Setup

```bash
cd ../llm-simulation-frontend

# Install dependencies
pnpm install

# Create environment file
cp .env.local.example .env.local

# Edit .env.local if needed (default API URL is http://localhost:5001)
```

## 🚀 Running the Application

### Start Backend (Terminal 1)

```bash
cd llm-simulation-service
source venv/bin/activate
python src/main.py
```

The backend will start on `http://localhost:5001`

### Start Frontend (Terminal 2)

```bash
cd llm-simulation-frontend
pnpm dev
```

The frontend will start on `http://localhost:5175`

## 📖 Usage

1. **Open the web interface** at `http://localhost:5175`
2. **Configure scenarios** by adding conversation variables
3. **Launch batch simulations** with your desired parameters
4. **Monitor progress** in real-time through the dashboard
5. **View results** with detailed conversation logs and evaluations
6. **Compare batches** using the comparison tools
7. **Export data** in CSV or NDJSON formats

## 🔧 Configuration

### Backend Configuration (.env)

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
HOST=0.0.0.0
PORT=5001
DEBUG=True
CONCURRENCY=5
RESULTS_DIR=results
```

### Frontend Configuration (.env.local)

```env
VITE_API_BASE_URL=http://localhost:5001
```

## 📊 API Endpoints

### Batch Management
- `POST /api/batches` - Launch new batch simulation
- `GET /api/batches` - List all batches
- `GET /api/batches/{id}` - Get batch status
- `GET /api/batches/{id}/results` - Get batch results
- `GET /api/batches/{id}/summary` - Get batch summary statistics
- `GET /api/batches/{id}/cost` - Get cost estimates

### System
- `GET /api/health` - Health check endpoint
- `GET /` - Service information

## 🗂️ Project Structure

```
agents_simulations/
├── llm-simulation-service/          # Backend Flask API
│   ├── src/
│   │   ├── main.py                  # Application entry point
│   │   ├── config.py                # Configuration management
│   │   ├── batch_processor.py       # Batch processing logic
│   │   ├── conversation_engine.py   # Conversation simulation
│   │   ├── evaluator.py             # Evaluation system
│   │   ├── persistent_storage.py    # Persistence layer
│   │   ├── result_storage.py        # Result management
│   │   ├── openai_wrapper.py        # OpenAI API integration
│   │   └── routes/                  # API route definitions
│   ├── requirements.txt             # Python dependencies
│   ├── results/                     # Generated results storage
│   └── venv/                        # Python virtual environment
│
├── llm-simulation-frontend/         # Frontend React application
│   ├── src/
│   │   ├── components/              # React components
│   │   ├── pages/                   # Page components
│   │   ├── hooks/                   # Custom React hooks
│   │   ├── services/                # API service layer
│   │   └── main.jsx                 # Application entry point
│   ├── package.json                 # Node.js dependencies
│   └── dist/                        # Built frontend assets
│
├── .gitignore                       # Git ignore rules
└── README.md                        # This file
```

## 🔄 Persistence System

The application features a robust persistence system:

- **Batch Metadata**: Stored in JSON files under `results/batches/`
- **Conversation Results**: Saved in CSV and NDJSON formats
- **Automatic Recovery**: Batches are restored on server restart
- **Progress Tracking**: Real-time status updates persist across restarts

## 🎯 Use Cases

- **Conversational AI Testing**: Evaluate chatbot performance across scenarios
- **Training Data Generation**: Create conversation datasets for model training
- **A/B Testing**: Compare different prompt versions or model configurations
- **Quality Assurance**: Automated testing of conversational flows
- **Performance Benchmarking**: Measure response quality and consistency

## 🐛 Troubleshooting

### Common Issues

1. **Port 5000 Conflicts on macOS**: The backend uses port 5001 to avoid AirPlay conflicts
2. **OpenAI API Limits**: Adjust `CONCURRENCY` setting to respect rate limits
3. **Node.js/Rollup Issues**: Clear `node_modules` and reinstall if build fails
4. **Missing Dependencies**: Ensure all requirements are installed in virtual environment

### Logs

- **Backend logs**: Console output or `server.log` file
- **Frontend logs**: Browser developer console
- **API requests**: Network tab in browser developer tools

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with OpenAI GPT models for conversation simulation
- Uses modern web technologies (React, Flask, Vite)
- Inspired by the need for robust conversational AI testing tools

## 📞 Support

For questions, issues, or contributions, please open an issue on GitHub or contact the maintainers.

---

**Happy Testing! 🎉** 