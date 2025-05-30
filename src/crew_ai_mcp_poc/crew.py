from crewai import Agent, Task, Crew, Process
from crew_ai_mcp_poc.tools.mcp_adapter import get_mcp_tools
import yaml
import os

# Load YAMLs
def load_yaml(file_path):
    with open(file_path, "r") as f:
        return yaml.safe_load(f)

def build_crew():
    base_path = os.path.dirname(__file__)
    agents_config = load_yaml(os.path.join(base_path, "config", "agents.yaml"))
    tasks_config = load_yaml(os.path.join(base_path, "config", "tasks.yaml"))

    tools = get_mcp_tools().tools
    if not tools:
        raise ValueError("No MCP tools loaded. Ensure the MCP server is running.")

    # Instantiate Agents
    agents = {}
    for name, cfg in agents_config.items():
        agents[name] = Agent(
            role=cfg['role'],
            goal=cfg['goal'],
            backstory=cfg['backstory'],
            tools=tools,
            verbose=True,
            allow_delegation=False
        )

    # Instantiate Tasks and tag with their YAML key
    task_map = {}
    for key, t in tasks_config.items():
        task = Task(
            description=t['description'],
            expected_output=t['expected_output'],
            agent=agents[get_agent_by_task(key)],
            async_execution=False
        )
        task_map[key] = task

    crew = Crew(
        agents=list(agents.values()),
        tasks=list(task_map.values()),
        process=Process.sequential
    )
    return crew

def get_agent_by_task(task_key):
    if "extract" in task_key:
        return "extraction_agent"
    elif "question" in task_key:
        return "question_agent"
    elif "edit" in task_key:
        return "edit_handler_agent"
    elif "summary" in task_key:
        return "summary_agent"
    elif "booking" in task_key:
        return "flight_options_agent"
    return "question_agent"

def run_extraction_task(user_input, tools):
    extractor = Agent(
        role="Field Extraction Agent",
        goal="Extract structured travel booking data from user input.",
        backstory="Expert in reading user input and extracting valid values and updating MCP context accordingly.",
        tools=tools,
        llm = os.getenv("MODEL"),
        verbose=True,
    )

    task = Task(
        description=(
            f"You are given the following user input:\n\n"
            f"\"{user_input}\"\n\n"
            "Extract values from user input. Validate the field against which the question was asked "
            "and use the 'update_field' tool to update it with the correct value.\n"
            "If the input is invalid, then don't extract the value and skip updating."
            "If user says 'book a flight from A to B on date X', then understand that flight corresponds to " \
            "the 'travel mode' field in MCP context and its value should always be considered as 'air'. \n"
            "Always understand the context of the response and update the relevant field in MCP context.\n"
            "If the field is already set, then update it with the new value only if it is different from the existing one.\n"
        ),
        expected_output="A field updated in context via MCP, or no update if nothing relevant found.",
        agent=extractor
    )

    crew = Crew(agents=[extractor], tasks=[task])
    result = crew.kickoff()
    return result
