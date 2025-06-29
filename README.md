# Blood Test Report Analyzer

A FastAPI application that analyzes blood test reports using AI agents.

## Project Setup

### Prerequisites
- Python 3.13+
- uv package manager

### Installation

1. Clone this repository
2. Install dependencies:
```sh
uv sync
```

## Running the Application

Start the FastAPI server:
```sh
python main.py
```

This will launch the application on `http://0.0.0.0:8000`

### API Endpoints

- **GET /** - Health check endpoint
- **POST /analyze** - Upload a blood test report PDF for analysis
  - Parameters:
    - `file`: The PDF file (required)
    - `query`: Analysis query (optional, defaults to "Summarise my Blood Test Report")

## Using the API

### Via Swagger UI
Access the Swagger UI at `http://0.0.0.0:8000/docs` to interact with the API.

### Via curl
```sh
curl -X POST http://0.0.0.0:8000/analyze \
  -F "file=@path/to/your/blood_test.pdf" \
  -F "query=Analyze my blood sugar levels"
```

## Project Structure

- `main.py` - FastAPI application and entry point
- `agents.py` - AI agent definitions
- `task.py` - Task definitions for the agents
- `tools.py` - Custom tools for the agents
- `data/` - Directory for storing uploaded blood test reports
- `outputs/` - Directory for analysis outputs
