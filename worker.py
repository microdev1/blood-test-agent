"""
Worker module for processing blood test analyses in the background.
"""

import os
import json
import multiprocessing
from datetime import datetime
from redis import Redis
from rq import Worker, Queue
from sqlalchemy.orm import Session

from database import get_engine, get_session_factory, Analysis
from analysis import run_crew  # Import the analysis function from analysis module

# Initialize database session
engine = get_engine()
SessionLocal = get_session_factory(engine)


def process_analysis(analysis_id, query, file_path):
    """
    Process a blood test analysis in the background

    Args:
        analysis_id (str): The unique ID for this analysis
        query (str): The user's query
        file_path (str): Path to the uploaded blood test PDF

    Returns:
        dict: Result of the analysis
    """
    try:
        # Create database session
        db = SessionLocal()

        try:
            analysis = (
                db.query(Analysis).filter(Analysis.analysis_id == analysis_id).first()
            )

            # Update status to processing
            if analysis:
                analysis.status = "processing"  # Fixed field name to match main.py
                db.commit()

            # Run the analysis
            result = run_crew(query=query, file_path=file_path)

            # Update the analysis record
            if analysis:
                analysis.analysis_result = str(
                    result
                )  # Fixed field name to match main.py
                analysis.status = "completed"  # Fixed field name to match main.py
                db.commit()

            # Cleanup file after processing
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"Cleaned up temporary file: {file_path}")
                except Exception as e:
                    print(f"Error cleaning up file {file_path}: {str(e)}")

            return {
                "status": "success",
                "analysis_id": analysis_id,
                "result": str(result),
            }

        except Exception as e:
            # Update status to failed
            analysis = (
                db.query(Analysis).filter(Analysis.analysis_id == analysis_id).first()
            )
            if analysis:
                analysis.status = "failed"  # Fixed field name to match main.py
                analysis.analysis_result = (
                    f"Error: {str(e)}"  # Fixed field name to match main.py
                )
                db.commit()

            # Cleanup file in case of error
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass  # Ignore cleanup errors

            return {"status": "error", "analysis_id": analysis_id, "error": str(e)}

        finally:
            db.close()

    except Exception as e:
        print(f"Worker process error: {str(e)}")
        return {"status": "error", "analysis_id": analysis_id, "error": str(e)}


def start_worker():
    """Start the RQ worker"""
    redis_conn = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    queue = Queue("blood_test_analyses", connection=redis_conn)
    worker = Worker([queue], connection=redis_conn)
    worker.work()


def main():
    """Main entry point for starting workers"""
    # Determine the number of worker processes to start
    num_workers = int(os.getenv("WORKER_COUNT", multiprocessing.cpu_count()))
    print(f"Starting {num_workers} worker processes...")

    # Start worker processes
    processes = []
    for i in range(num_workers):
        p = multiprocessing.Process(target=start_worker)
        p.start()
        processes.append(p)
        print(f"Started worker {i+1}")

    # Wait for all processes to complete
    for p in processes:
        p.join()


if __name__ == "__main__":
    main()
