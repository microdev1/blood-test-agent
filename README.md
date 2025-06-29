# Blood Test Report Analyzer

A sophisticated FastAPI application that leverages AI agents to analyze blood test reports and provide personalized health insights. The system uses CrewAI to coordinate specialized agents (including a doctor, verifier, nutritionist, and exercise specialist), processes tasks asynchronously with Redis Queue, and stores analysis data in a SQLite database.

## Features

- **AI-Powered Analysis**: Utilizes a crew of specialized AI agents to interpret blood test results
- **Personalized Health Insights**: Provides medical interpretations, nutritional advice, and exercise recommendations
- **Asynchronous Processing**: Handles analysis tasks in the background using Redis Queue
- **RESTful API**: Offers a comprehensive API for uploading reports and retrieving analyses
- **PDF Processing**: Extracts and processes data from PDF blood test reports

## Project Setup

### Prerequisites
- Python 3.13+
- Redis server installed and running
- uv package manager

### Installation

1. Clone this repository
2. Install dependencies:
```sh
uv sync
```

## Running the Application

1. **Start Redis Server**

   If you don't have Redis running already, start it:

   ```bash
   # On macOS (with Homebrew)
   brew services start redis

   # On Linux
   sudo service redis-server start
   ```

2. **Initialize the Database**

   The database will be automatically initialized when you start the application, but you can also initialize it manually:

   ```python
   from database import init_db
   init_db()
   ```

3. **Start Worker Processes**

   Start the background worker processes to handle analysis tasks:

   ```bash
   # Using the script entry point
   start-workers

   # Or run directly
   python worker.py
   ```

   This will start workers based on your CPU count. You can control the number of workers with the `WORKER_COUNT` environment variable.

4. **Start the FastAPI Application**

   In a separate terminal, start the FastAPI application:

   ```bash
   # Using the script entry point
   blood-test-analyser

   # Or run directly with uvicorn
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

   This will launch the application on `http://0.0.0.0:8000`

## API Endpoints

- **GET /** - Health check endpoint
- **POST /analyze** - Upload a blood test report PDF for analysis
  - Parameters:
    - `file`: The PDF file (required)
    - `query`: Analysis query (optional, defaults to "Summarise my Blood Test Report")
  - Returns an `analysis_id` that you can use to check the status
- **GET /analyses/status/{analysis_id}** - Check the status of an analysis
- **GET /analyses/{analysis_id}** - Get the results of a completed analysis
- **GET /analyses** - List all analyses
- **DELETE /analyses/{analysis_id}** - Delete an analysis

## System Architecture

### Components

1. **AI Agent Crew**
   - **Doctor Agent**: Interprets medical test results and provides clinical insights
   - **Verifier Agent**: Validates findings and ensures accuracy
   - **Nutritionist Agent**: Provides dietary recommendations based on blood markers
   - **Exercise Specialist**: Suggests physical activity plans based on health status

2. **Tools**
   - **BloodTestReportTool**: Extracts and processes data from PDF blood test reports
   - **NutritionTool**: Analyzes nutritional needs based on blood test results
   - **ExerciseTool**: Creates exercise recommendations based on health status
   - **SerperDevTool**: Performs web searches for additional medical information

3. **Backend Services**
   - **Redis Queue**: Manages asynchronous processing of analysis tasks
   - **SQLite Database**: Stores analysis results and metadata
   - **FastAPI Framework**: Provides the RESTful API interface

### Workflow

1. User uploads a blood test report PDF and optionally provides a specific query
2. The system stores the PDF and queues the analysis task
3. Worker processes pick up the task and execute the AI agent crew analysis
4. Results are stored in the database and made available through the API

## Using the API

### Via Swagger UI
Access the Swagger UI at `http://0.0.0.0:8000/docs` to interact with the API.

### Via curl
```sh
# Submit a blood test report for analysis
curl -X POST http://0.0.0.0:8000/analyze \
  -F "file=@path/to/your/blood_test.pdf" \
  -F "query=Analyze my blood sugar levels"

# Check analysis status
curl -X GET http://0.0.0.0:8000/analyses/status/{analysis_id}

# Get analysis results
curl -X GET http://0.0.0.0:8000/analyses/{analysis_id}

# List all analyses
curl -X GET http://0.0.0.0:8000/analyses

# Delete an analysis
curl -X DELETE http://0.0.0.0:8000/analyses/{analysis_id}
```

### Example Queries

- "Summarize my blood test results"
- "What do my cholesterol levels indicate?"
- "Analyze my iron levels and provide dietary recommendations"
- "Are my liver function tests normal? What improvements can I make?"
- "Evaluate my thyroid panel and suggest lifestyle changes"

## Customization and Development

### Configuration Files

The system uses YAML configuration files in the `config/` directory:

- **agents.yaml**: Defines the roles, goals, and backstories for AI agents
- **tasks.yaml**: Specifies the tasks each agent will perform
- **tools.yaml**: Configures the tools available to the agents

### Adding New Capabilities

1. **New Agents**: Add new specialized agents in `agents.py` and update `config/agents.yaml`
2. **New Tools**: Extend `tools.py` with custom tools that inherit from `BaseTool`
3. **New Tasks**: Create additional tasks in `tasks.py` and update `config/tasks.yaml`

### Environment Variables

- `REDIS_URL`: Redis connection string (default: "redis://localhost:6379")
- `WORKER_COUNT`: Number of worker processes to start (default: CPU count)
- `SERPER_API_KEY`: API key for the SerperDev search tool (if used)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [CrewAI](https://github.com/joaomdmoura/crewAI) for the agent orchestration framework
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [Redis Queue](https://python-rq.org/) for background job processing

## Environment Variables

- `REDIS_URL`: Redis server URL (default: `redis://localhost:6379`)
- `WORKER_COUNT`: Number of worker processes to start (default: CPU count)

## Architecture

- **FastAPI Application**: Handles HTTP requests and delegates analysis tasks to the queue
- **Redis Queue**: Manages the queue of analysis tasks
- **Worker Processes**: Process analysis tasks in the background
- **SQLite Database**: Stores analysis results and metadata

This architecture allows the application to handle multiple concurrent requests efficiently by offloading the CPU-intensive analysis tasks to background workers.

## Project Structure

- `main.py` - FastAPI application and entry point
- `agents.py` - AI agent definitions
- `tasks.py` - Task definitions for the agents
- `tools.py` - Custom tools for the agents
- `database.py` - Database setup and operations
- `start_workers.py` - Script to start worker processes
- `worker.py` - Worker process implementation
- `config/` - Configuration files for agents, tasks, and tools
- `data/` - Directory for storing uploaded blood test reports
- `outputs/` - Directory for analysis outputs
