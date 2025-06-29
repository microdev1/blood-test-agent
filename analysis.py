"""
Analysis module that contains the run_crew function to avoid circular imports.
"""

import os
import json

from agents import doctor, verifier, nutritionist, exercise_specialist
from crewai import Crew, Process
from datetime import datetime

from tasks import help_patients, nutrition_analysis, exercise_planning, verification
from tools import BloodTestReportTool, NutritionTool, ExerciseTool, search_tool


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
    """Save analysis results to the database or outputs directory

    Args:
        result: The analysis result from CrewOutput
        query (str): The user query
        file_path (str): Path to the analyzed blood test report
    """
    try:
        # For compatibility with older code paths that don't use the queue,
        # save to the outputs directory
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
