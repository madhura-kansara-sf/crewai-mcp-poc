from pydantic import BaseModel, Field
from typing import Optional, Dict

class TravelBookingContext(BaseModel):
    registererDetails: Dict[str, Optional[str]] = Field(default_factory=lambda: {
        "projectOrOpportunity": None,
        "billableTo": None
    })

    travelPlan: Dict[str, Optional[str]] = Field(default_factory=lambda: {
        "travelType": None,
        "travelScope": None,
        "leavingFrom": None,
        "goingTo": None,
        "departureDate": None,
        "departureTime": None,
        "returnDate": None,
        "returnTime": None,
        "travelMode": None,
        "companyProvidedAccommodationRequired": None,
        "travelPurpose": None,
        "additionalDetails": None,
    })

    companyProvidedAccommodation: Dict[str, Optional[str]] = Field(default_factory=lambda: {
        "accommodationCity": None,
        "checkIn": None,
        "checkOut": None,
        "visitingOfficeOrLocation": None
    })

    passengerDetails: Dict[str, Optional[str]] = Field(default_factory=lambda: {
        "passengerName": None,
        "relation": None
    })

    approver: Dict[str, Optional[str]] = Field(default_factory=lambda: {
        "approverName": None
    })

    approvalMessage: Optional[str] = None

    def is_complete(self):
        if any(v is None for v in self.registererDetails.values()):
            return False
        if any(v is None for v in self.travelPlan.values()):
            return False
        if self.travelPlan["companyProvidedAccommodationRequired"] == "Yes":
            if any(v is None for v in self.companyProvidedAccommodation.values()):
                return False
        if any(v is None for v in self.passengerDetails.values()):
            return False
        if any(v is None for v in self.approver.values()):
            return False
        if self.travelPlan["additionalDetails"] and len(self.travelPlan["additionalDetails"]) < 10:
            return False
        return True

    def get_next_missing_field(self):
        for section in [self.registererDetails, self.travelPlan, self.passengerDetails, self.approver]:
            for k, v in section.items():
                if v is None:
                    return k
        if self.travelPlan["companyProvidedAccommodationRequired"] == "Yes":
            for k, v in self.companyProvidedAccommodation.items():
                if v is None:
                    return k
        return None

    def next_node(self):
        if not self.is_complete():
            return "ask_next_question"
        else:
            return "booking_options"

    def to_json(self):
        return {
            "registererDetails": self.registererDetails,
            "travelPlan": self.travelPlan,
            "companyProvidedAccommodation": self.companyProvidedAccommodation,
            "passengerDetails": self.passengerDetails,
            "approver": self.approver,
            "approvalMessage": f"travel request is sent to {self.passengerDetails['passengerName']} for approval"
        }
