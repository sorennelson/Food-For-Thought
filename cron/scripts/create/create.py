import requests, os

FASTAPI_HOST = "fastapi"
FASTAPI_PORT = 8000
IFTTT_SERVICE_KEY = os.getenv("IFTTT_SERVICE_KEY")

def create_request(endpoint: str, post=True, payload=None):
    """ Convenience function to run the given "create" request with the service key.
      Endpoint: One of ["/create_week", "/create_day", "/get_weeks", "/get_days"].
      Post: Whether this is a post or get request. Defaults to True.
      Payload: The payload to pass to the request. Defaults to None.
    """
    
    url = f"http://{FASTAPI_HOST}:{FASTAPI_PORT}{endpoint}"
    
    headers = {
        "Content-Type": "application/json",
        "IFTTT-Service-Key": IFTTT_SERVICE_KEY
    }

    try:
        if post:
          resp = requests.post(url, headers=headers, json=payload)
        else:
          resp = requests.get(url, headers=headers, json=payload)
        print(resp.status_code, resp.json())
    except Exception as e:
        print("Request failed:", e)
