from fastapi import FastAPI, HTTPException, Path, Depends
from pydantic import BaseModel, EmailStr, Field
from typing import List
from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_
from model.Event import EventDB, AttendeeDB
from db.database import SessionLocal, Base, engine
from fastapi.middleware.cors import CORSMiddleware
from fastapi_keycloak import FastAPIKeycloak, OIDCUser # type: ignore
from fastapi_keycloak.exceptions import KeycloakError # type: ignore


Base.metadata.create_all(bind=engine)

keycloak = FastAPIKeycloak(
server_url="http://localhost:8080/",
    client_id="eventoap-client",                    # the client for your app's user login
    client_secret="Gd2jS7BQPnXM0iwfKjkjdbKsgj2ePexO", # confidential app client secret
    admin_client_id="eventoap-client",
    admin_client_secret="Gd2jS7BQPnXM0iwfKjkjdbKsgj2ePexO",
    realm="EventOAP",
    callback_uri="http://localhost:8000/callback"
)
def create_keycloak_user(username, email, password):
    user = {
        "email": email,
        "username": username,
        "enabled": True,
        "credentials": [{
            "value": password,
            "type": "password",
            "temporary": False
        }]
    }
    return keycloak.create_user(first_name="Sumeet",last_name="Gupta",username=username,email=email,password="defaultPassword123")


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
keycloak.add_swagger_config(app)
# app.include_router(keycloak.get_login_router(), "/auth")

@app.get("/whoami")
async def whoami(user=Depends(keycloak.get_current_user())):
    return user

@app.get("/secure-data", dependencies=[Depends(keycloak.get_current_user)])
def secure_data():
    return {"data": "only accessible with token"}


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

# Create an Event
@app.post("/events", response_model=Event)
def create_event(event: EventCreate, db: Session = Depends(get_db)):
    event_id = str(uuid4())
    db_event = EventDB(id=event_id, **event.dict())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return Event(id=db_event.id, **event.dict())

# Get List of Upcoming events 
@app.get("/events", response_model=List[Event])
def list_upcoming_events(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    db_events = db.query(EventDB).filter(EventDB.start_time > now).all()
    return [Event(id=e.id, name=e.name, location=e.location, start_time=e.start_time, end_time=e.end_time, max_capacity=e.max_capacity) for e in db_events]

# register an attendee in an upcoming event
@app.post("/events/{event_id}/register")
def register_attendee(
    event_id: str,
    attendee: Attendee,
    user: OIDCUser = Depends(keycloak.get_current_user()),
    db: Session = Depends(get_db)
):
    event = db.query(EventDB).filter_by(id=event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.start_time <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="Cannot register for past or ongoing events")

    existing = db.query(AttendeeDB).filter(
        and_(AttendeeDB.email == attendee.email, AttendeeDB.event_id == event_id)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Attendee already registered")

    if len(event.attendees) >= event.max_capacity:
        raise HTTPException(status_code=400, detail="Event is full")

    # response_from_kc = create_keycloak_user(attendee.name, attendee.email, "defaultPassword123")
    # print(response_from_kc)
    
    try:
        response_from_kc = create_keycloak_user(attendee.name, attendee.email, "defaultPassword123")
        print(response_from_kc)
    except KeycloakError as e:
        detail = e.args[0] if isinstance(e.args[0], dict) and 'errorMessage' in e.args[0] else str(e)
        # raise HTTPException(status_code=500, detail=detail)
        #  we will keep pasthrough

    event = db.query(EventDB).filter_by(id=event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    existing = db.query(AttendeeDB).filter(
        and_(AttendeeDB.email == attendee.email, AttendeeDB.event_id == event_id)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Attendee already registered")

    if len(event.attendees) >= event.max_capacity:
        raise HTTPException(status_code=400, detail="Event is full")

    db_attendee = AttendeeDB(id=str(uuid4()), name=attendee.name, email=attendee.email, event_id=event_id)
    db.add(db_attendee)
    db.commit()
    return {"message": "Registration successful"}

# Get List of Attendee in an event
@app.get("/events/{event_id}/attendees", response_model=List[Attendee])
def get_attendees(event_id: str, db: Session = Depends(get_db)):
    event = db.query(EventDB).filter_by(id=event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return [Attendee(name=a.name, email=a.email) for a in event.attendees]
