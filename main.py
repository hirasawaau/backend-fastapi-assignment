from fastapi import FastAPI, HTTPException, Body, status
from pydantic.datetime_parse import parse_date
from datetime import date, datetime
from pymongo import MongoClient, ReturnDocument
from pydantic import BaseModel, validator
from fastapi.middleware.cors import CORSMiddleware

from typing import List


DATABASE_NAME = "hotel"
COLLECTION_NAME = "reservation"
MONGO_DB_URL = "mongodb://localhost"
MONGO_DB_PORT = 27017


class Reservation(BaseModel):
    name: str
    start_date: date
    end_date: date
    room_id: int


class ReservationDb(Reservation):
    start_date: datetime
    end_date: datetime


class ResponseResults(BaseModel):
    result: List[Reservation]


client = MongoClient(f"{MONGO_DB_URL}:{MONGO_DB_PORT}")

db = client[DATABASE_NAME]

collection = db[COLLECTION_NAME]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def room_avaliable(room_id: int, start_date: str, end_date: str):

    query = {"room_id": room_id,
             "$or":
             [{"$and": [{"start_date": {"$lte": start_date}}, {"end_date": {"$gte": start_date}}]},
              {"$and": [{"start_date": {"$lte": end_date}},
                        {"end_date": {"$gte": end_date}}]},
              {"$and": [{"start_date": {"$gte": start_date}}, {"end_date": {"$lte": end_date}}]}]
             }

    result = collection.find(query, {"_id": 0})
    list_cursor = list(result)

    return not len(list_cursor) > 0


@app.get("/reservation/by-name/{name}", response_model=ResponseResults)
def get_reservation_by_name(name: str):
    docs = collection.find({
        "name": name
    })

    return ResponseResults(result=list(docs))


@app.get("/reservation/by-room/{room_id}", response_model=ResponseResults)
def get_reservation_by_room(room_id: int):
    if room_id < 1 or room_id > 10:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {
            "errors": "Room must more than or equal 1 and less than or equal 10"
        })
    docs = collection.find({
        "room_id": room_id
    })

    return ResponseResults(result=list(docs))


# @app.post("/reservation", response_model=Reservation)
@app.post("/reservation", response_model=Reservation)
def reserve(reservation: Reservation):
    if reservation.room_id < 1 or reservation.room_id > 10:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {
            "errors": "Room must more than or equal 1 and less than or equal 10"
        })
    if reservation.end_date < reservation.start_date:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {
            "errors": "End date must after start date"
        })
    doc = reservation.dict()
    doc['start_date'] = reservation.start_date.isoformat()
    doc['end_date'] = reservation.end_date.isoformat()

    if not room_avaliable(reservation.room_id, doc['start_date'], doc["end_date"]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {
            "error": "Room is not available."
        })
    collection.insert_one(doc)

    return doc


@app.put("/reservation/update", response_model=Reservation)
def update_reservation(reservation: Reservation, new_start_date: date = Body(), new_end_date: date = Body()):
    if new_end_date < new_start_date:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {
            "errors": "End date must after start date"
        })
    doc = reservation.dict()
    doc['start_date'] = reservation.start_date.isoformat()
    doc['end_date'] = reservation.end_date.isoformat()

    if not room_avaliable(reservation.room_id, new_start_date.isoformat(), new_end_date.isoformat()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {
            "error": "Room is not available."
        })
    doc = collection.find_one_and_update(doc, {
        "$set": {
            "start_date": new_start_date.isoformat(),
            "end_date": new_end_date.isoformat()
        }
    }, return_document=ReturnDocument.AFTER)

    return doc


@app.delete("/reservation/delete", response_model=Reservation)
def cancel_reservation(reservation: Reservation):
    doc = reservation.dict()
    doc['start_date'] = reservation.start_date.isoformat()
    doc['end_date'] = reservation.end_date.isoformat()
    doc = collection.find_one_and_delete(doc)
    return doc
