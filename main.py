import os
import uuid
import asyncio

from datetime import datetime

from fastapi import (
    FastAPI,
    File,
    UploadFile,
    Form,
    HTTPException,
    BackgroundTasks,
    Depends,
)

from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from redis import Redis
from rq import Queue

from sqlalchemy.orm import Session

from analysis import run_crew  # Import run_crew from analysis.py
from database import init_db, get_engine, get_session_factory, Analysis
from worker import process_analysis

# Initialize database
engine = init_db()
SessionLocal = get_session_factory(engine)

# Initialize Redis Queue
redis_conn = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
analysis_queue = Queue("blood_test_analyses", connection=redis_conn)

app = FastAPI(title="Blood Test Report Analyser")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Database dependency
def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Blood Test Report Analyser API is running"}


@app.post("/analyze")
async def analyze_blood_report(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    query: str = Form(default="Summarise my Blood Test Report"),
    db: Session = Depends(get_db),
):
    """Analyze blood test report and provide comprehensive health recommendations

    Args:
        background_tasks: FastAPI background tasks
        file: The uploaded blood test report PDF file
        query: The user's specific query about their blood test
        db: Database session

    Returns:
        JSON response with analysis results
    """

    # Validate file extension
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail="Invalid file format. Only PDF files are supported."
        )

    # Generate unique IDs
    analysis_id = str(uuid.uuid4())
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

        # Create a database record for this analysis
        new_analysis = Analysis(
            analysis_id=analysis_id,
            query=query,
            file_analyzed=file.filename,
            analysis_date=datetime.now(),
            status="pending",
            analysis_result="Processing...",
        )

        db.add(new_analysis)
        db.commit()

        # Queue the analysis task
        job = analysis_queue.enqueue(
            process_analysis,
            analysis_id=analysis_id,
            query=query.strip(),
            file_path=file_path,
            job_timeout="1h",  # Allow up to 1 hour for processing
        )

        return {
            "status": "processing",
            "message": "Your blood test report is being analyzed",
            "analysis_id": analysis_id,
            "query": query,
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
async def get_analyses(db: Session = Depends(get_db)):
    """Get a list of all blood test analyses

    Returns:
        List of analysis metadata
    """
    try:
        # Query all analyses from database
        db_analyses = db.query(Analysis).order_by(Analysis.analysis_date.desc()).all()

        # Convert to response format
        analyses = [
            {
                "id": analysis.analysis_id,
                "query": analysis.query,
                "file_analyzed": analysis.file_analyzed,
                "analysis_date": analysis.analysis_date.isoformat(),
                "status": analysis.status,
            }
            for analysis in db_analyses
        ]

        return {"analyses": analyses}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving analyses: {str(e)}"
        )


@app.get("/analyses/{analysis_id}")
async def get_analysis(analysis_id: str, db: Session = Depends(get_db)):
    """Get a specific analysis by ID

    Args:
        analysis_id: The ID of the analysis to retrieve
        db: Database session

    Returns:
        The full analysis data
    """
    try:
        # Query the analysis from database
        analysis = (
            db.query(Analysis).filter(Analysis.analysis_id == analysis_id).first()
        )

        if not analysis:
            raise HTTPException(
                status_code=404, detail=f"Analysis with ID {analysis_id} not found"
            )

        # Return the analysis data
        return {
            "analysis_id": analysis.analysis_id,
            "query": analysis.query,
            "file_analyzed": analysis.file_analyzed,
            "analysis_date": analysis.analysis_date.isoformat(),
            "analysis_result": analysis.analysis_result,
            "status": analysis.status,
        }
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving analysis: {str(e)}"
        )


@app.delete("/analyses/{analysis_id}")
async def delete_analysis(analysis_id: str, db: Session = Depends(get_db)):
    """Delete a specific analysis by ID

    Args:
        analysis_id: The ID of the analysis to delete
        db: Database session

    Returns:
        Success message
    """
    try:
        # Query the analysis
        analysis = (
            db.query(Analysis).filter(Analysis.analysis_id == analysis_id).first()
        )

        if not analysis:
            raise HTTPException(
                status_code=404, detail=f"Analysis with ID {analysis_id} not found"
            )

        # Delete from database
        db.delete(analysis)
        db.commit()

        # Cancel job if still in queue
        job = analysis_queue.fetch_job(analysis_id)
        if job:
            job.cancel()
            job.delete()

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


@app.get("/analyses/status/{analysis_id}")
async def get_analysis_status(analysis_id: str, db: Session = Depends(get_db)):
    """Get the status of a specific analysis by ID

    Args:
        analysis_id: The ID of the analysis to check
        db: Database session

    Returns:
        Status of the analysis
    """
    try:
        # Check if analysis exists in database
        analysis = (
            db.query(Analysis).filter(Analysis.analysis_id == analysis_id).first()
        )

        if not analysis:
            raise HTTPException(
                status_code=404, detail=f"Analysis with ID {analysis_id} not found"
            )

        # Get job from Redis if it's still in the queue
        job = analysis_queue.fetch_job(analysis_id)

        # Return status information
        return {
            "analysis_id": analysis_id,
            "status": analysis.status,
            "query": analysis.query,
            "file_analyzed": analysis.file_analyzed,
            "analysis_date": analysis.analysis_date.isoformat(),
            "queue_position": job.get_position() if job else None,
            "is_finished": (
                job.is_finished if job else (analysis.status in ["completed", "failed"])
            ),
            "is_failed": job.is_failed if job else (analysis.status == "failed"),
        }

    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving analysis status: {str(e)}"
        )


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
