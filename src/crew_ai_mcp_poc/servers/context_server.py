from mcp.server.fastmcp import FastMCP
from datetime import datetime

mcp = FastMCP("TravelContext")

# Global context dictionary to store state between calls
context = {
    "registererDetails": {
        "projectOrOpportunity": None,
        "billableTo": None
    },
    "travelPlan": {
        "travelType": None,
        "travelScope": None,
        "leavingFrom": None,
        "goingTo": None,
        "departureDate": None,
        # "departureTime": None,
        # "returnDate": None,
        # "returnTime": None,
        "travelMode": None,
        "companyProvidedAccommodationRequired": None,
        "travelPurpose": None,
        # "additionalDetails": None
    },
    "companyProvidedAccommodation": {
        "accommodationCity": None,
        "checkIn": None,
        "checkOut": None,
        "visitingOfficeOrLocation": None
    },
    "passengerDetails": {
        "passengerName": None,
        "relation": None
    },
    "approver": {
        "approverName": None
    },
    "selectedFlight": None
}

required_fields = [
    "registererDetails.projectOrOpportunity",
    "registererDetails.billableTo",
    "travelPlan.travelType",
    "travelPlan.travelScope",
    "travelPlan.leavingFrom",
    "travelPlan.goingTo",
    "travelPlan.departureDate",
    # "travelPlan.departureTime",
    # "travelPlan.returnDate",
    # "travelPlan.returnTime",
    "travelPlan.travelMode",
    "travelPlan.companyProvidedAccommodationRequired",
    "travelPlan.travelPurpose",
    # "travelPlan.additionalDetails",
    "passengerDetails.passengerName",
    "passengerDetails.relation",
    "approver.approverName"
]

accommodation_fields = [
    "companyProvidedAccommodation.accommodationCity",
    "companyProvidedAccommodation.checkIn",
    "companyProvidedAccommodation.checkOut",
    "companyProvidedAccommodation.visitingOfficeOrLocation"
]

def get_nested(d, key_path):
    try:
        for k in key_path.split("."):
            d = d[k]
        return d
    except (KeyError, TypeError):
        return None

def set_nested(d, key_path, value):
    keys = key_path.split(".")
    for k in keys[:-1]:
        d = d[k]
    d[keys[-1]] = value

@mcp.tool()
def get_filled_fields() -> list:
    """Returns a list of all fields that are already filled"""
    filled = []
    for f in required_fields + accommodation_fields:
        try:
            if get_nested(context, f):
                filled.append(f)
        except:
            pass
    return filled

@mcp.tool()
def get_pending_fields() -> list:
    """Returns a list of missing fields, conditionally including accommodation details."""
    pending = []
    accommodation_required = get_nested(context, "travelPlan.companyProvidedAccommodationRequired") == "yes"

    for f in required_fields:
        try:
            if not get_nested(context, f):
                pending.append(f)
        except:
            pending.append(f)

    if accommodation_required:
        for f in accommodation_fields:
            try:
                if not get_nested(context, f):
                    pending.append(f)
            except:
                pending.append(f)

    return pending

VALID_FIELD_OPTIONS = {
    "registererDetails.billableTo": ["client", "company", "internal"],
    "travelPlan.travelType": ["domestic", "international", "local"],
    "travelPlan.travelScope": ["round trip", "multicity", "one way"],
    "travelPlan.travelMode": ["air"],
    "travelPlan.companyProvidedAccommodationRequired": ["yes", "no"]
}

@mcp.tool()
def update_field(field: str, value: str) -> str:
    """Update a field in the context after validating"""

    if field not in required_fields + accommodation_fields:
        raise ValueError(f"Invalid field name: {field}")

    # Predefined option validation
    if field in VALID_FIELD_OPTIONS:
        if value.lower() not in [v.lower() for v in VALID_FIELD_OPTIONS[field]]:
            raise ValueError(
                f"Invalid value '{value}' for field '{field}'. "
                f"Allowed options: {', '.join(VALID_FIELD_OPTIONS[field])}"
            )

    # Example validations
    if "Date" in field:
        try:
            datetime.strptime(value, "%d/%m/%Y")
        except ValueError:
            raise ValueError("Invalid date format, must be dd/mm/yyyy")

    if "additionalDetails" in field and len(value.strip()) < 10:
        raise ValueError("Additional details must be at least 10 characters")

    set_nested(context, field, value)
    return f"{field} updated to '{value}'"

@mcp.tool()
def get_next_question() -> str:
    """Suggest the next question to ask the user"""
    pending = get_pending_fields()
    if not pending:
        return "All fields are complete."

    next_field = pending[0]
    q = next_field.split(".")[-1].replace("Id", "").replace("Or", " or ").replace("And", " and ")
    return f"Can you please provide the {q.replace('_', ' ')}?"

@mcp.tool()
def get_context() -> dict:
    """Returns the full conversation context"""
    return context

@mcp.tool()
def reset_state() -> str:
    """Clears the context for new session"""
    for f in required_fields + accommodation_fields:
        set_nested(context, f, None)
    set_nested(context, "selectedFlight", None)
    return "Context state has been reset."

FLIGHT_OPTIONS = {
    "1": "Air Indigo, 08:00 AM, ₹5500, Economy",
    "2": "Vistara, 11:30 AM, ₹6200, Economy",
    "3": "Air India, 6:45 PM, ₹5900, Premium Economy"
}

@mcp.tool()
def set_selected_flight(option: str) -> str:
    """Set the selected flight option"""
    if option not in FLIGHT_OPTIONS:
        raise ValueError("Invalid flight option. Choose 1, 2, or 3.")
    
    # Parse the flight details into a structured format
    flight_info = FLIGHT_OPTIONS[option].split(", ")
    flight_details = {
        "airline": flight_info[0],
        "departureTime": flight_info[1],
        "price": flight_info[2],
        "class": flight_info[3]
    }
    
    set_nested(context, "selectedFlight", flight_details)
    return f"Flight option {option} selected: {FLIGHT_OPTIONS[option]}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
