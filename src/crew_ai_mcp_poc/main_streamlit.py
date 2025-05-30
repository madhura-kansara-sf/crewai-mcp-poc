import streamlit as st
from crewai import Crew, Task
from crew_ai_mcp_poc.crew import build_crew, run_extraction_task
from crew_ai_mcp_poc.tools.mcp_adapter import get_mcp_tools

def get_tool(tools, name):
    return next((tool for tool in tools if tool.name == name), None)

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

# ---------- SESSION STATE SETUP ----------
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.crew = build_crew()
    st.session_state.tools = get_mcp_tools().tools
    st.session_state.pending_fields = []
    st.session_state.flight_selected = False
    st.session_state.stage = "welcome"  # Start with welcome
    st.session_state.chat_history = []
    st.session_state.last_question = ""
    st.session_state.user_input = ""
    st.session_state.booking_started = False

# ---------- UI START ----------
st.title("✈️ Travel Booking Assistant")

# Display chat history
for role, message in st.session_state.chat_history:
    st.chat_message(role).write(message)

# ---------- WELCOME STAGE ----------
if st.session_state.stage == "welcome":
    if not st.session_state.booking_started:
        st.chat_message("assistant").write("Hi! I'm your Travel Booking Assistant.")
        st.session_state.chat_history.append(("assistant", "Hi! I'm your Travel Booking Assistant."))
        
        if st.button("Start New Booking"):
            st.session_state.booking_started = True
            st.session_state.chat_history.append(("user", "Yes, start new booking"))
            st.session_state.chat_history.append(("assistant", "Great! Let's get started with your travel booking..."))
            st.session_state.stage = "questions"
            st.rerun()
        
        if st.button("No, Maybe Later"):
            st.chat_message("assistant").write("No problem! Come back anytime.")
            st.session_state.chat_history.append(("assistant", "No problem! Come back anytime."))
            st.stop()

# ---------- QUESTION/ANSWER LOOP ----------
elif st.session_state.stage == "questions":
    # Step 1: Ask first or next question
    if st.session_state.last_question == "":
        question = run_tool(st.session_state.tools, "get_next_question", {})
        if question:
            st.session_state.last_question = question
            st.session_state.chat_history.append(("assistant", question))
            st.chat_message("assistant").write(question)
        else:
            st.error("Unable to generate the next question.")
            st.session_state.stage = "flights"

    # Step 2: Show input box and wait for user response
    user_input = st.chat_input("Your answer:")
    if user_input:
        # Handle exit commands
        if user_input.strip().lower() in ["exit", "quit"]:
            st.chat_message("assistant").write("Goodbye! Your session is saved. You can continue later.")
            st.session_state.chat_history.append(("assistant", "Goodbye! Your session is saved. You can continue later."))
            st.stop()
            
        st.session_state.chat_history.append(("user", user_input))

        # Step 3: Extract fields
        with st.spinner("🧠 Extracting field from your input..."):
            result = run_extraction_task(user_input, st.session_state.tools)
            # st.write("Result:", result)
            st.session_state.pending_fields = run_tool(st.session_state.tools, "get_pending_fields", {}) or []

        # Step 4: Continue or move to next stage
        if not st.session_state.pending_fields:
            st.success("All fields are collected! Let's move to booking options...")
            st.session_state.stage = "flights"
            st.rerun()
        else:
            # st.info(f"Pending fields left: {st.session_state.pending_fields}")
            question = run_tool(st.session_state.tools, "get_next_question", {})
            if question:
                st.session_state.last_question = question
                st.session_state.chat_history.append(("assistant", question))
                st.chat_message("assistant").write(question)

# ---------- FLIGHT SELECTION ----------
elif st.session_state.stage == "flights":
    st.subheader("✈️ Flight Options")

    booking_task = get_task_by_description(st.session_state.crew, "mock flight options")
    if booking_task:
        with st.spinner("Suggesting flight options..."):
            booking_result = Crew(
                agents=[booking_task.agent],
                tasks=[booking_task],
                tools=st.session_state.tools,
            ).kickoff()

        st.session_state.chat_history.append(("assistant", f"Options:\n{booking_result.raw}"))
        st.markdown("Here are some flight options:\n\n" + str(booking_result.raw))

        selected = st.selectbox("Please select a flight option:", ["1", "2", "3"], key="flight_selector")
        if st.button("Select Flight"):
            with st.spinner("Updating selected flight in context..."):
                # Create an ad-hoc task to update MCP using agent
                flight_update_task = Task(
                    description=f"The user selected flight option {selected}. Use the `set_selected_flight` tool to update MCP context.",
                    expected_output="Context updated with the selected flight.",
                    agent=booking_task.agent,
                    tools=st.session_state.tools
                )

                flight_update_result = Crew(
                    agents=[booking_task.agent],
                    tasks=[flight_update_task],
                    tools=st.session_state.tools,
                ).kickoff(inputs={"selected_option": selected})

                st.success(f"Flight saved: {flight_update_result}")
                st.session_state.chat_history.append(("user", f"Selected flight option {selected}"))
                st.session_state.chat_history.append(("assistant", f"Flight saved: {flight_update_result}"))
                st.session_state.stage = "summary"
                st.rerun()
    else:
        st.error("No booking task found. Check task configuration.")

# ---------- BOOKING SUMMARY & CONFIRMATION LOOP ----------
elif st.session_state.stage == "summary":
    st.subheader("📋 Booking Summary")

    summary_task = get_task_by_description(st.session_state.crew, "travel summary agent")
    if not summary_task:
        st.error("No summary task found. Check task config.")
    else:
        with st.spinner("Generating booking summary..."):
            context = run_tool(st.session_state.tools, "get_context", {})
            context_str = str(context)
            summary_result = Crew(
                agents=[summary_task.agent],
                tasks=[Task(
                    description=(
                        f"Here is the booking context:\n\n{context_str}\n\n"
                        "Summarize the full booking in JSON, including selected flight details, and ask for confirmation."
                    ),
                    expected_output="Full human readable clean summary including selected flight details + prompt to confirm or edit.",
                    agent=summary_task.agent,
                    tools=st.session_state.tools,
                )]
            ).kickoff()

        st.session_state.chat_history.append(("assistant", f"Booking Summary:\n{summary_result.raw}"))
        st.markdown("**Booking Summary:**\n\n" + str(summary_result.raw))

        # User confirmation choice
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Confirm Booking", type="primary"):
                st.success("✅ Booking confirmed. Travel request is sent for approval.")
                st.session_state.chat_history.append(("user", "Confirmed booking"))
                st.session_state.chat_history.append(("assistant", "Booking confirmed. Travel request is sent for approval."))
                st.balloons()
                st.stop()
        
        with col2:
            if st.button("✏️ Edit Booking"):
                st.info("What would you like to edit?")
                st.session_state.chat_history.append(("user", "I want to edit"))
                st.session_state.chat_history.append(("assistant", "What would you like to edit?"))
                # Reset to questions stage for editing
                st.session_state.stage = "questions"
                st.session_state.last_question = ""
                st.rerun()

# ---------- SIDEBAR WITH SESSION INFO ----------
with st.sidebar:
    st.header("Session Info")
    # st.write(f"**Current Stage:** {st.session_state.stage.title()}")
    # st.write(f"**Pending Fields:** {len(st.session_state.pending_fields)}")
    
    if st.button("🔄 Reset Session"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    if st.button("💾 Show Context"):
        if st.session_state.tools:
            context = run_tool(st.session_state.tools, "get_context", {})
            st.json(context)

# ---------- FOOTER ----------
st.markdown("---")
st.markdown("*Travel Booking Assistant powered by CrewAI*")