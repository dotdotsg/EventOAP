from fastapi import FastAPI, HTTPException, Path, Depends
from pydantic import BaseModel, EmailStr, Field
from typing import List
from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_
from model.Event import EventDB, AttendeeDB
from db.database import SessionLocal, Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI()

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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/events", response_model=Event)
def create_event(event: EventCreate, db: Session = Depends(get_db)):
    event_id = str(uuid4())
    db_event = EventDB(id=event_id, **event.dict())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return Event(id=db_event.id, **event.dict())

@app.get("/events", response_model=List[Event])
def list_upcoming_events(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    db_events = db.query(EventDB).filter(EventDB.start_time > now).all()
    return [Event(id=e.id, name=e.name, location=e.location, start_time=e.start_time, end_time=e.end_time, max_capacity=e.max_capacity) for e in db_events]

@app.post("/events/{event_id}/register")
def register_attendee(event_id: str, attendee: Attendee, db: Session = Depends(get_db)):
    event = db.query(EventDB).filter_by(id=event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    existing = db.query(AttendeeDB).filter(and_(AttendeeDB.email == attendee.email, AttendeeDB.event_id == event_id)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Attendee already registered")

    if len(event.attendees) >= event.max_capacity:
        raise HTTPException(status_code=400, detail="Event is full")

    db_attendee = AttendeeDB(id=str(uuid4()), name=attendee.name, email=attendee.email, event_id=event_id)
    db.add(db_attendee)
    db.commit()
    return {"message": "Registration successful"}

@app.get("/events/{event_id}/attendees", response_model=List[Attendee])
def get_attendees(event_id: str, db: Session = Depends(get_db)):
    event = db.query(EventDB).filter_by(id=event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return [Attendee(name=a.name, email=a.email) for a in event.attendees]
