from fastapi import FastAPI, HTTPException, Path, Depends
from pydantic import BaseModel, EmailStr, Field
from typing import List, Dict
from datetime import datetime
from uuid import uuid4

app = FastAPI()

events = {}
registrations = {}

class EventCreate(BaseModel):
    name: str
    location: str
    start_time: datetime
    end_time: datetime
    max_capacity: int = Field(gt=0)

class Event(EventCreate):
    id: str

class Attendee(BaseModel):
    name: str
    email: EmailStr

@app.post("/events", response_model=Event)
def create_event(event: EventCreate):
    event_id = str(uuid4())
    new_event = Event(id=event_id, **event.dict())
    events[event_id] = new_event
    registrations[event_id] = []
    return new_event

@app.get("/events", response_model=List[Event])
def list_upcoming_events():
    now = datetime.utcnow()
    return [event for event in events.values() if event.start_time > now]

@app.post("/events/{event_id}/register")
def register_attendee(
    event_id: str = Path(...),
    attendee: Attendee = Depends()
):
    if event_id not in events:
        raise HTTPException(status_code=404, detail="Event not found")

    event = events[event_id]
    attendees = registrations[event_id]

    if any(a.email == attendee.email for a in attendees):
        raise HTTPException(status_code=400, detail="Attendee already registered")

    if len(attendees) >= event.max_capacity:
        raise HTTPException(status_code=400, detail="Event is full")

    registrations[event_id].append(attendee)
    return {"message": "Registration successful"}

@app.get("/events/{event_id}/attendees", response_model=List[Attendee])
def get_attendees(event_id: str = Path(...)):
    if event_id not in events:
        raise HTTPException(status_code=404, detail="Event not found")
    return registrations[event_id]
