## Importing libraries and files
import os
import yaml
import asyncio

from crewai.tools import BaseTool

from crewai_tools import SerperDevTool

from langchain_community.document_loaders import PyPDFLoader

from dotenv import load_dotenv

load_dotenv()

# Load configuration from YAML file
with open("config/tools.yaml", "r") as config_file:
    config = yaml.safe_load(config_file)

## Creating search tool
search_tool = SerperDevTool()


## Creating custom pdf reader tool
class BloodTestReportTool(BaseTool):
    def __init__(self, file_path="data/sample.pdf"):
        tool_config = config["blood_test_report_tool"]
        self.name = tool_config["name"]
        self.description = tool_config["description"]
        super().__init__(name=self.name, description=self.description)
        self.file_path = file_path or tool_config["default_file_path"]

    async def _arun(self, file_path=None):
        path = file_path if file_path else self.file_path
        return await self.read_data_tool(path)

    def _run(self, file_path=None):
        path = file_path if file_path else self.file_path
        return asyncio.run(self.read_data_tool(path))

    async def read_data_tool(self, path="data/sample.pdf"):
        """Tool to read data from a pdf file from a path

        Args:
            path (str, optional): Path of the pdf file. Defaults to 'data/sample.pdf'.

        Returns:
            str: Full Blood Test report file
        """
        try:
            # Check if file exists
            if not os.path.exists(path):
                return f"Error: File not found at {path}"

            docs = PyPDFLoader(file_path=path).load()

            full_report = ""
            for data in docs:
                # Clean and format the report data
                content = data.page_content

                # Remove extra whitespaces and format properly
                while "\n\n" in content:
                    content = content.replace("\n\n", "\n")

                full_report += content + "\n"

            return full_report
        except Exception as e:
            return f"Error reading PDF file: {str(e)}"


## Base Analysis Tool - Parent class for analysis tools with common functionality
class BaseAnalysisTool(BaseTool):
    def __init__(self, config_key):
        tool_config = config[config_key]
        self.name = tool_config["name"]
        self.description = tool_config["description"]
        self.header = tool_config["header"]
        self.default_indicators = tool_config["default_indicators"]
        self.default_recommendation = tool_config["default_recommendation"]
        self.general_guidance = tool_config["general_guidance"]
        super().__init__(name=self.name, description=self.description)

    async def _arun(self, blood_report_data):
        return await self.analyze_data(blood_report_data)

    def _run(self, blood_report_data):
        return asyncio.run(self.analyze_data(blood_report_data))

    async def analyze_data(self, blood_report_data):
        """Analyze blood report data and provide specific recommendations

        Args:
            blood_report_data (str): The blood report data to analyze

        Returns:
            str: Formatted analysis results
        """
        try:
            # Handle empty or invalid data
            if not blood_report_data or len(blood_report_data.strip()) < 10:
                return f"{self.header}\n\nError: Insufficient data in blood report. Please ensure a valid blood test report was provided.\n\n{self.general_guidance}"

            # Clean the data (common functionality)
            processed_data = self._clean_data(blood_report_data)

            # Analyze data - to be implemented by child classes
            analysis_results = self._analyze_specific_data(processed_data)

            # Format response (common functionality)
            response = self._format_response(analysis_results)

            return response
        except Exception as e:
            return f"{self.header}\n\nError analyzing data: {str(e)}\n\n{self.general_guidance}"

    def _clean_data(self, data):
        """Common data cleaning functionality

        Args:
            data (str): The raw blood report data

        Returns:
            str: Cleaned and processed data
        """
        # Clean up the data format
        processed_data = data
        processed_data = processed_data.replace("  ", " ").strip()

        # Convert to lowercase for easier searching
        processed_data_lower = processed_data.lower()

        # Return both the original cleaned data and lowercase version
        return processed_data

    def _analyze_specific_data(self, processed_data):
        """To be implemented by child classes"""
        raise NotImplementedError("Child classes must implement this method")

    def _format_response(self, analysis_results):
        """Common response formatting"""
        response = f"{self.header}\n\n"

        # If no specific markers found, use default recommendation
        if not analysis_results:
            analysis_results = {"general": self.default_recommendation}

        for key, value in analysis_results.items():
            response += f"- {key.capitalize()}: {value}\n"

        response += f"\nGeneral dietary guidance:\n{self.general_guidance}"

        return response


## Creating Nutrition Analysis Tool
class NutritionTool(BaseAnalysisTool):
    def __init__(self):
        super().__init__("nutrition_tool")

    def _analyze_specific_data(self, processed_data):
        # Analyze blood test data for nutrition recommendations
        nutrition_analysis = {}

        # Extract and analyze common nutritional indicators
        for indicator, recommendation in self.default_indicators.items():
            if indicator in processed_data.lower():
                nutrition_analysis[indicator] = recommendation

        return nutrition_analysis


## Creating Exercise Planning Tool
class ExerciseTool(BaseAnalysisTool):
    def __init__(self):
        super().__init__("exercise_tool")

    def _analyze_specific_data(self, processed_data):
        # Exercise plan generation logic based on blood markers
        exercise_plan = {}

        # Extract and analyze common exercise-related indicators
        for indicator, description in {
            "cholesterol": "cardiovascular",
            "glucose": "metabolic",
            "blood pressure": "blood_pressure",
            "bp": "blood_pressure",
            "bone": "bone_health",
            "calcium": "bone_health",
        }.items():
            if indicator in processed_data.lower():
                exercise_plan[description] = self.default_indicators[description]

        return exercise_plan

    def _format_response(self, analysis_results):
        """Override to customize exercise response formatting"""
        response = f"{self.header}\n\n"

        # If no specific markers found, use default recommendation
        if not analysis_results:
            analysis_results = {"general": self.default_recommendation}

        for key, value in analysis_results.items():
            response += f"- {key.capitalize()}: {value}\n"

        response += f"\nGeneral exercise guidance:\n{self.general_guidance}"

        return response
