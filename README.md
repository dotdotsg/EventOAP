# EventOAP

An Even Management System built for users to register in events

## Running the project

1. Create a virtual environment using venv
   `python -m venv .venv`
   Activate the environment
   `.venv\Scripts\activate`

2. Run the backend application:
   Either run it in your local system :
   `uvicorn main:app --rebuild`
   Or build the docker image using the docker-compose :
   `docker compose up --build`
   Application will run on port `8000` by default , the keycloak server will run on port `8080` , postgres on port `5432`
   Frontend application will run on port `3000` when it will be up.

3. Setting up the Keycloak for this project:
   First of all create a New Realm , eg. "EventOAP"
   Inside the realm, create a new client and give the client all the admin roles. make sure to give the client service roles

Important details about the implemented authentication :
Keycloak has been used to provide jwt authentication for the APIs, and implement Email verification or otp verification lateron if required.
