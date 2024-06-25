from fastapi import APIRouter, FastAPI, HTTPException, Query
from typing import List
import redis
import string
import random
from datetime import datetime, timedelta
import re
import ast
import json

app = FastAPI()
redis_db = redis.StrictRedis(host='localhost', port=6379, db=0, password='eR4fLDYyU2qEMntwW', decode_responses=True)
redis_db_customer_keys = redis.StrictRedis(host='localhost', port=6379, db=1, password='eR4fLDYyU2qEMntwWK', decode_responses=True)

def generate_random_license_key():
    license_key = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(32))
    return license_key

def validate_hwid(hwid):
    return re.match(r'^S-\d+-\d+(?:-\d+)+$', hwid) is not None

def validate_username(username):
    return re.match(r'^[a-zA-Z0-9]+$', username) is not None

def generate_random_app_name():
    app_name = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
    return app_name

router = APIRouter()

@router.get("/auth/generate_app")
def generate_app(username: str = Query(..., description="Username of the app owner"),
                 customer_api_key: str = Query(..., description="Customer API key")):
    
    if not redis_db_customer_keys.exists(customer_api_key):
        raise HTTPException(status_code=403, detail="Invalid customer API key")

    if not validate_username(username):
        raise HTTPException(status_code=400, detail="Invalid username format")
    
    app_key = f"Pilot{random.choice(string.ascii_uppercase)}{''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(16))}-{username}"
    app_data = {
        "created_by": username,
        "app_key": app_key
    }
    redis_db.hmset(app_key, app_data)
    return app_data

@router.get("/auth/list_apps_for_user")
def list_apps_for_user(username: str = Query(..., description="Username of the user"),
                       customer_api_key: str = Query(..., description="Customer API key")):

    if not redis_db_customer_keys.exists(customer_api_key):
        raise HTTPException(status_code=403, detail="Invalid customer API key")
    apps = []
    for key in redis_db.keys(pattern=f"Pilot[A-Z]*-{username}"):
        app_data = redis_db.hgetall(key)
        app_info = {
            "app_key": key,
        }
        apps.append(app_info)

    return apps


@router.get("/auth/list_keys_for_username")
def list_keys_for_username(username: str = Query(..., description="Username of the user"),
                            customer_api_key: str = Query(..., description="Customer API key"),
                            page: int = Query(1, description="Page number")):
    if not redis_db_customer_keys.exists(customer_api_key):
        raise HTTPException(status_code=403, detail="Invalid customer API key")
    items_per_page = 100
    start_index = (page - 1) * items_per_page
    end_index = page * items_per_page
    keys = []
    for key in redis_db.scan_iter(match=f"*-{username}", count=100):
        cleaned_key = key.strip()
        keys.append(cleaned_key)
    keys_on_page = keys[start_index:end_index]
    keys_text = "<br>".join(keys_on_page)
    
    return keys_text

@router.get("/auth/pause_app_key")
def pause_app_key(application_key: str = Query(..., description="Application key to pause"),
                  customer_api_key: str = Query(..., description="Customer API key")):
    if not redis_db_customer_keys.exists(customer_api_key):
        raise HTTPException(status_code=403, detail="Invalid customer API key")

    if not redis_db.exists(application_key):
        raise HTTPException(status_code=404, detail="Application key not found")
    
    redis_db.hset(application_key, "paused", True)
    return {"detail": "Application key has been paused"}

@router.get("/auth/delete_app_key")
def delete_app_key(application_key: str = Query(..., description="Application key to delete"),
                   customer_api_key: str = Query(..., description="Customer API key")):
    if not redis_db_customer_keys.exists(customer_api_key):
        raise HTTPException(status_code=403, detail="Invalid customer API key")

    if not redis_db.exists(application_key):
        raise HTTPException(status_code=404, detail="Application key not found")

    redis_db.delete(application_key)
    return {"detail": "Application key has been deleted"}

@router.get("/auth/unpause_app_key")
def unpause_app_key(application_key: str = Query(..., description="Application key to unpause"),
                    customer_api_key: str = Query(..., description="Customer API key")):
    if not redis_db_customer_keys.exists(customer_api_key):
        raise HTTPException(status_code=403, detail="Invalid customer API key")
    
    if not redis_db.exists(application_key):
        raise HTTPException(status_code=404, detail="Application key not found")
    
    redis_db.hset(application_key, "paused", False)
    return {"detail": "Application key has been unpaused"}

@router.get("/auth/generate_license_key")
def generate_license_key(customer_api_key: str = Query(..., description="Customer API key"),
                         app_key: str = Query(..., description="App key"),
                         plan: str = Query(..., description="Plan (package) for the app"),
                         expiry_days: int = Query(..., description="Expiry in days"),
                         username: str = Query(..., description="Username of the app owner"),
                         hwid: str = Query("", description="Hardware ID (optional)")):
    if not redis_db_customer_keys.exists(customer_api_key):
        raise HTTPException(status_code=403, detail="Invalid customer API key")
    if not redis_db.exists(app_key):
        raise HTTPException(status_code=404, detail="App not found")
    if not validate_username(username):
        raise HTTPException(status_code=400, detail="Invalid username format")
    if not validate_username(plan):
        raise HTTPException(status_code=400, detail="Invalid plan format")
    if hwid and not validate_hwid(hwid):
        raise HTTPException(status_code=400, detail="Invalid HWID format")
    if redis_db.hget(app_key, "paused") == "True":
        raise HTTPException(status_code=403, detail="Application is paused")
    license_key = generate_random_license_key()
    expiry_date = datetime.now() + timedelta(days=expiry_days)
    license_data = {
        "license_key": license_key,
        "expiry": expiry_date.strftime("%Y-%m-%d"),
        "plan": plan,
        "hwid": hwid,
        "username": username,
        "app": app_key
    }
    redis_db.hset(app_key, license_key, str(license_data))
    return license_data

@router.get("/auth/assign_hwid")
def assign_hwid(app_key: str = Query(..., description="App key"),
                license_key: str = Query(..., description="License key"),
                hwid: str = Query(..., description="Hardware ID")):
    if not redis_db.exists(app_key):
        raise HTTPException(status_code=404, detail="App not found")
    if not validate_username(license_key):
        raise HTTPException(status_code=400, detail="Invalid license key format")
    license_data = redis_db.hget(app_key, license_key)
    if not license_data:
        raise HTTPException(status_code=404, detail="License key not found")
    license_data = json.loads(license_data)
    last_hwid_change = datetime.strptime(license_data.get("last_hwid_change", "2000-01-01"), "%Y-%m-%d")
    current_date = datetime.now()
    thirty_days_ago = current_date - timedelta(days=30)
    if last_hwid_change >= thirty_days_ago:
        raise HTTPException(status_code=403, detail="HWID change is not allowed within 30 days of the last change")
    if not validate_hwid(hwid):
        raise HTTPException(status_code=400, detail="Invalid HWID format")
    license_data["hwid"] = hwid
    license_data["last_hwid_change"] = current_date.strftime("%Y-%m-%d")
    redis_db.hset(app_key, license_key, str(license_data))
    return {"message": "HWID assigned successfully"}

@router.get("/auth/edit_license_key")
def edit_license_key(customer_api_key: str = Query(..., description="Customer API key"),
                     app_key: str = Query(..., description="App key"),
                     license_key: str = Query(..., description="License key to edit"),
                     new_license_key: str = Query(None, description="New license key"),
                     expiry: str = Query(None, description="Expiry date"),
                     plan: str = Query(None, description="Plan (package)"),
                     hwid: str = Query(None, description="Hardware ID")):
    if not redis_db_customer_keys.exists(customer_api_key):
        raise HTTPException(status_code=403, detail="Invalid customer API key")
    if not redis_db.exists(app_key):
        raise HTTPException(status_code=404, detail="App not found")
    license_data = redis_db.hget(app_key, license_key)
    if not license_data:
        raise HTTPException(status_code=404, detail="License key not found")
    license_data = ast.literal_eval(license_data)
    if new_license_key is not None:
        license_data["license_key"] = new_license_key
    if expiry is not None:
        if not re.match(r'^\d{1,16}$', expiry):
            raise HTTPException(status_code=400, detail="Invalid expiry format")
        license_data["expiry"] = expiry
    if plan is not None:
        if not validate_username(plan):
            raise HTTPException(status_code=400, detail="Invalid plan format")
        license_data["plan"] = plan
    if hwid is not None:
        if not validate_hwid(hwid):
            raise HTTPException(status_code=400, detail="Invalid HWID format")
        license_data["hwid"] = hwid
    redis_db.hset(app_key, license_key, str(license_data))
    return {"message": "License key updated successfully"}

@router.get("/auth/signin")
def signin(application_key: str = Query(..., description="Application key"),
           license_key: str = Query(..., description="License key"),
           hwid: str = Query("", description="Hardware ID (optional)")):
    if not validate_username(license_key):
        raise HTTPException(status_code=400, detail="Invalid key format")
    app_key = application_key
    if not redis_db.exists(app_key):
        raise HTTPException(status_code=404, detail="Application key not found")
    license_data = redis_db.hget(app_key, license_key)
    if not license_data:
        raise HTTPException(status_code=404, detail="License key not found")
    license_info = ast.literal_eval(license_data)
    expiry_date = datetime.strptime(license_info.get("expiry", "2000-01-01"), "%Y-%m-%d")
    if expiry_date < datetime.now():
        raise HTTPException(status_code=403, detail="License key has expired")
    if hwid and license_info.get("hwid", "null") != hwid:
        raise HTTPException(status_code=403, detail="HWID mismatch")
    return {
        "license_key": license_key,
        "expiry": license_info.get("expiry", None),
        "plan": license_info.get("plan", None),
        "hwid": license_info.get("hwid", "null"),
    }

# Include the router in the FastAPI app
app.include_router(router)
