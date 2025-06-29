## Importing libraries and files
import yaml

from dotenv import load_dotenv

load_dotenv()


from crewai import Agent

from tools import search_tool, BloodTestReportTool, NutritionTool, ExerciseTool

# Load configuration from YAML file
with open("config/agents.yaml", "r") as config_file:
    config = yaml.safe_load(config_file)


# Creating an Experienced Doctor agent
doctor = Agent(
    role=config["doctor"]["role"],
    goal=config["doctor"]["goal"],
    backstory=config["doctor"]["backstory"],
    verbose=True,
    tools=[BloodTestReportTool(), search_tool],
    max_iter=1,
    max_rpm=1,
    allow_delegation=True,  # Allow delegation to other specialists
)

# Creating a verifier agent
verifier = Agent(
    role=config["verifier"]["role"],
    goal=config["verifier"]["goal"],
    backstory=config["verifier"]["backstory"],
    verbose=True,
    tools=[BloodTestReportTool(), search_tool],
    max_iter=1,
    max_rpm=1,
    allow_delegation=True,
)


nutritionist = Agent(
    role=config["nutritionist"]["role"],
    goal=config["nutritionist"]["goal"],
    backstory=config["nutritionist"]["backstory"],
    verbose=True,
    tools=[BloodTestReportTool(), NutritionTool()],
    max_iter=1,
    max_rpm=1,
    allow_delegation=False,
)


exercise_specialist = Agent(
    role=config["exercise_specialist"]["role"],
    goal=config["exercise_specialist"]["goal"],
    backstory=config["exercise_specialist"]["backstory"],
    verbose=True,
    tools=[BloodTestReportTool(), ExerciseTool()],
    max_iter=1,
    max_rpm=1,
    allow_delegation=False,
)
