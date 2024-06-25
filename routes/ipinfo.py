from fastapi import FastAPI, HTTPException, Query
from fastapi import APIRouter
import requests
import re
import redis
import socket

router = APIRouter()

# Redis database for customer keys
redis_db_customer_keys = redis.StrictRedis(
    host='localhost',
    port=6379,
    db=1,
    password='eR4fLDYyU2qE',
    decode_responses=True
)

def validate_ipv4(ip):
    ipv4_pattern = re.compile(
        r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')
    return ipv4_pattern.match(ip) is not None

def validate_ipv6(ip):
    ipv6_pattern = re.compile(
        r'^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))$')
    return ipv6_pattern.match(ip) is not None

def validate_ip(ip):
    return validate_ipv4(ip) or validate_ipv6(ip)

def validate_domain(domain):
    # Domain pattern to match XTEXT followed by a dot and then TLDR
    domain_pattern = re.compile(r'^[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+$')
    return domain_pattern.match(domain) is not None


@router.get("/ip_geolocation")
def get_ip_geolocation(ip: str = Query(..., description="IP Address or Domain"),
                       key: str = Query(..., description="Customer API key")):
    # Validate the IP address or domain
    if not validate_ip(ip) and not validate_domain(ip):
        raise HTTPException(status_code=400, detail="Invalid IP address or domain format")

    if key is None:
        raise HTTPException(status_code=403, detail="Invalid customer API key")
    if not redis_db_customer_keys.exists(key):
        raise HTTPException(status_code=403, detail="Invalid customer API key")

    # If it's a domain, resolve it to an IP address
    if validate_domain(ip):
        try:
            ip = socket.gethostbyname(ip)
        except socket.gaierror:
            raise HTTPException(status_code=400, detail="Failed to resolve domain to IP address")

    # Fetch data from the IP geolocation API
    api_url = f"http://ip-api.com/json/{ip}?fields=66318335"
    response = requests.get(api_url)
    
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch data from the IP geolocation API")

    return response.json()
