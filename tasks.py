## Importing libraries and files
import yaml

from crewai import Task

from agents import doctor, verifier, nutritionist, exercise_specialist
from tools import search_tool, BloodTestReportTool, NutritionTool, ExerciseTool

# Load configuration from YAML file
with open("config/tasks.yaml", "r") as config_file:
    task_config = yaml.safe_load(config_file)

## Creating a task to help solve user's query
help_patients = Task(
    description=task_config["help_patients"]["description"],
    expected_output=task_config["help_patients"]["expected_output"],
    agent=doctor,
    tools=[BloodTestReportTool(), search_tool],
    async_execution=False,
)

## Creating a nutrition analysis task
nutrition_analysis = Task(
    description=task_config["nutrition_analysis"]["description"],
    expected_output=task_config["nutrition_analysis"]["expected_output"],
    agent=nutritionist,
    tools=[BloodTestReportTool(), NutritionTool()],
    async_execution=False,
)

## Creating an exercise planning task
exercise_planning = Task(
    description=task_config["exercise_planning"]["description"],
    expected_output=task_config["exercise_planning"]["expected_output"],
    agent=exercise_specialist,
    tools=[BloodTestReportTool(), ExerciseTool()],
    async_execution=False,
)


verification = Task(
    description=task_config["verification"]["description"],
    expected_output=task_config["verification"]["expected_output"],
    agent=verifier,
    tools=[BloodTestReportTool(), search_tool],
    async_execution=False,
)
