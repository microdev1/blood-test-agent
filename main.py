import os
import json
import uuid
import asyncio

from datetime import datetime

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from crewai import Crew, Process
from agents import doctor, verifier, nutritionist, exercise_specialist
from tasks import help_patients, nutrition_analysis, exercise_planning, verification
from tools import BloodTestReportTool, NutritionTool, ExerciseTool, search_tool

app = FastAPI(title="Blood Test Report Analyser")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


# Error handling middleware
@app.middleware("http")
async def error_handling_middleware(request, call_next):
    """Middleware for consistent error handling across the application"""
    try:
        return await call_next(request)
    except Exception as e:
        # Log the error
        print(f"Unhandled error: {str(e)}")

        # Return a consistent error response
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "detail": "An unexpected error occurred. Please try again later.",
                "type": type(e).__name__,
            },
        )


def run_crew(query: str, file_path: str = "data/sample.pdf"):
    """To run the whole crew

    Args:
        query (str): The user's query about their blood test
        file_path (str): Path to the blood test report PDF

    Returns:
        str: The analysis result from the crew
    """
    try:
        # Ensure file exists
        if not os.path.exists(file_path):
            return f"Error: Blood test report not found at {file_path}"

        # Create a BloodTestReportTool with the specified file path
        blood_test_tool = BloodTestReportTool(file_path=file_path)
        nutrition_tool = NutritionTool()
        exercise_tool = ExerciseTool()

        # Update agent tools
        doctor.tools = [blood_test_tool, search_tool]
        verifier.tools = [blood_test_tool, search_tool]
        nutritionist.tools = [blood_test_tool, nutrition_tool, search_tool]
        exercise_specialist.tools = [blood_test_tool, exercise_tool, search_tool]

        medical_crew = Crew(
            agents=[doctor, verifier, nutritionist, exercise_specialist],
            tasks=[help_patients, nutrition_analysis, exercise_planning, verification],
            process=Process.sequential,
            verbose=True,
        )

        result = medical_crew.kickoff({"query": query, "file_path": file_path})

        # Save the result to outputs directory
        save_analysis_result(result, query, file_path)

        return result
    except Exception as e:
        error_message = f"Error running crew analysis: {str(e)}"
        print(error_message)
        return error_message


def save_analysis_result(result, query: str, file_path: str):
    """Save analysis results to the outputs directory

    Args:
        result: The analysis result from CrewOutput
        query (str): The user query
        file_path (str): Path to the analyzed blood test report
    """
    try:
        # Ensure outputs directory exists
        os.makedirs("outputs", exist_ok=True)

        # Create a timestamp for the filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create a unique filename based on the original filename
        base_filename = os.path.basename(file_path)
        filename_no_ext = os.path.splitext(base_filename)[0]

        # Create output file path
        output_path = f"outputs/{filename_no_ext}_{timestamp}.json"

        # Create output data
        output_data = {
            "query": query,
            "file_analyzed": file_path,
            "analysis_date": datetime.now().isoformat(),
            "analysis_result": str(result),
        }

        # Write to file
        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2)

        print(f"Analysis result saved to {output_path}")
    except Exception as e:
        print(f"Error saving analysis result: {str(e)}")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Blood Test Report Analyser API is running"}


@app.post("/analyze")
async def analyze_blood_report(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    query: str = Form(default="Summarise my Blood Test Report"),
):
    """Analyze blood test report and provide comprehensive health recommendations

    Args:
        background_tasks: FastAPI background tasks
        file: The uploaded blood test report PDF file
        query: The user's specific query about their blood test

    Returns:
        JSON response with analysis results
    """

    # Validate file extension
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail="Invalid file format. Only PDF files are supported."
        )

    # Generate unique filename to avoid conflicts
    file_id = str(uuid.uuid4())
    file_path = f"data/blood_test_report_{file_id}.pdf"

    try:
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)

        # Save uploaded file
        with open(file_path, "wb") as f:
            content = await file.read()
            if len(content) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Uploaded file is empty. Please upload a valid PDF file.",
                )
            f.write(content)

        # Validate query
        if query == "" or query is None:
            query = "Summarise my Blood Test Report"

        # Process the blood report with all specialists
        response = run_crew(query=query.strip(), file_path=file_path)

        # Schedule file cleanup as a background task
        background_tasks.add_task(cleanup_file, file_path)

        return {
            "status": "success",
            "query": query,
            "analysis": str(response),
            "file_processed": file.filename,
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        # Clean up file in case of error
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass  # Ignore cleanup errors

        raise HTTPException(
            status_code=500, detail=f"Error processing blood report: {str(e)}"
        )


@app.get("/analyses")
async def get_analyses():
    """Get a list of past blood test analyses

    Returns:
        List of analysis metadata
    """
    try:
        # Ensure outputs directory exists
        if not os.path.exists("outputs"):
            return {"analyses": []}

        analyses = []
        for filename in os.listdir("outputs"):
            if filename.endswith(".json"):
                file_path = os.path.join("outputs", filename)
                try:
                    with open(file_path, "r") as f:
                        data = json.load(f)
                        analyses.append(
                            {
                                "id": os.path.splitext(filename)[0],
                                "query": data.get("query", "Unknown"),
                                "file_analyzed": data.get("file_analyzed", "Unknown"),
                                "analysis_date": data.get("analysis_date", "Unknown"),
                            }
                        )
                except:
                    # Skip corrupted files
                    continue

        # Sort by date, newest first
        analyses.sort(key=lambda x: x["analysis_date"], reverse=True)

        return {"analyses": analyses}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving analyses: {str(e)}"
        )


@app.get("/analyses/{analysis_id}")
async def get_analysis(analysis_id: str):
    """Get a specific analysis by ID

    Args:
        analysis_id: The ID of the analysis to retrieve

    Returns:
        The full analysis data
    """
    try:
        file_path = f"outputs/{analysis_id}.json"

        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404, detail=f"Analysis with ID {analysis_id} not found"
            )

        with open(file_path, "r") as f:
            data = json.load(f)

        return data
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving analysis: {str(e)}"
        )


@app.delete("/analyses/{analysis_id}")
async def delete_analysis(analysis_id: str):
    """Delete a specific analysis by ID

    Args:
        analysis_id: The ID of the analysis to delete

    Returns:
        Success message
    """
    try:
        file_path = f"outputs/{analysis_id}.json"

        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404, detail=f"Analysis with ID {analysis_id} not found"
            )

        os.remove(file_path)

        return {
            "status": "success",
            "message": f"Analysis {analysis_id} deleted successfully",
        }
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting analysis: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Extended health check endpoint with system information

    Returns:
        Health status and system information
    """
    return {
        "status": "healthy",
        "message": "Blood Test Report Analyser API is running",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat(),
    }


async def cleanup_file(file_path: str):
    """Clean up uploaded file after processing

    Args:
        file_path (str): Path to the file to clean up
    """
    # Add a small delay to ensure processing is complete
    await asyncio.sleep(5)

    # Clean up uploaded file
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            print(f"Error cleaning up file {file_path}: {str(e)}")
            pass  # Ignore cleanup errors


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
