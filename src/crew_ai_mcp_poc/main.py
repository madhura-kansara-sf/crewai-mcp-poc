import os
from crewai import Crew, Task
from crew_ai_mcp_poc.crew import build_crew, run_extraction_task
from crew_ai_mcp_poc.tools.mcp_adapter import get_mcp_tools

def get_tool(tools, name):
    return next(tool for tool in tools if tool.name == name)

def run_tool(tools, tool_name, input_dict):
    tool = get_tool(tools, tool_name)
    if tool is None:
        raise ValueError(f"Tool '{tool_name}' not found.")
    try:
        return tool.run(input_dict)
    except IndexError:
        return None

def get_task_by_description(crew, phrase):
    return next((t for t in crew.tasks if phrase.lower() in t.description.lower()), None)

def main():
    print(" Hi! I'm your Travel Booking Assistant.")
    confirm = input("Would you like to start a new booking? (yes/no) You: ").strip().lower()

    if confirm != "yes":
        print("No problem! Come back anytime.")
        return

    print("Great! Let's get started with your travel booking...\n")

    crew = build_crew()
    tools = get_mcp_tools().tools

    while True:
        question = run_tool(tools, "get_next_question", {})
        if not question:
            print("Unable to generate the next question.")
            break

        print(f"Bot: {question}")
        user_input = input("You: ")

        if user_input.strip().lower() in ["exit", "quit"]:
            print("Goodbye! Your session is saved. You can continue later.")
            break

        print("Extracting field from your input...")
        result = run_extraction_task(user_input, tools)
        print("Result:", result)

        pending = run_tool(tools, "get_pending_fields", {}) or []

        if not pending:
            print("All fields are collected! Let's move to booking options...\n")

            # 1. Suggest mock options using existing task
            booking_task = get_task_by_description(crew, "mock flight options")
            if booking_task:
                print("Suggesting flight options...")
                booking_result = Crew(
                    agents=[booking_task.agent],
                    tasks=[booking_task],
                    tools=tools,
                ).kickoff()
                print("Options:\n", booking_result)

                # 2. Ask user to pick flight
                selected = input("Please select a flight option (1/2/3): ").strip()

                # 3. Create an ad-hoc task to update MCP using agent
                print("Updating selected flight in context...")
                flight_update_task = Task(
                    description=f"The user selected flight option {selected}. Use the `set_selected_flight` tool to update MCP context.",
                    expected_output="Context updated with the selected flight.",
                    agent=booking_task.agent,
                    tools=tools
                )

                flight_update_result = Crew(
                    agents=[booking_task.agent],
                    tasks=[flight_update_task],
                    tools=tools,
                ).kickoff(inputs={"selected_option": selected})

                print("Flight saved:", flight_update_result)

            # 3. Summary + confirmation loop
            while True:
                summary_task = get_task_by_description(crew, "travel summary agent")
                if not summary_task:
                    print(" No summary task found. Check task config.")

                else:
                    print(" Generating booking summary...")
                    context = run_tool(tools, "get_context", {})
                    context_str = str(context)
                    summary_result = Crew(
                        agents=[summary_task.agent],
                        tasks=[Task(
                            description=(
                                f"Here is the booking context:\n\n{context_str}\n\n"
                                "Summarize the full booking in JSON, including selected flight details, and ask for confirmation."
                ),
                            expected_output="Full summary JSON including selected flight details + prompt to confirm or edit.",
                            agent=summary_task.agent,
                            tools=tools,
                        )]
                    ).kickoff()
                    print(" Booking Summary:\n", summary_result)

                # 4. User confirms or edits
                confirm = input("\n Confirm this booking? (yes/edit): ").strip().lower()
                if confirm == "yes":
                    print(" Booking confirmed. Travel request is sent for approval.")
                    return
                else:
                    print(" What would you like to edit?")
                    break  # Go back to question-answer loop
        else:
            print(" Pending fields left:", pending)


if __name__ == "__main__":
    main()
