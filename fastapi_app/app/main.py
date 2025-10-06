import os, redis, logging, json
from fastapi import FastAPI, status, Request
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from fft import WeeklyFFT, Transcript, extract_latest_transcript, generate_fft
import uuid

app = FastAPI()
IFTTT_SERVICE_KEY = os.getenv("IFTTT_SERVICE_KEY")

# Connect to Redis
r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    force=True
)
logger = logging.getLogger(__name__)

logger.info(f"IFTTT_SERVICE_KEY {IFTTT_SERVICE_KEY}")

# -- Objects --
class Week(BaseModel):
    """ Weekly information about a show transcript."""
    created_at: datetime = Field(
      default_factory=datetime.now(timezone.utc).isoformat(timespec='seconds'), 
      description="Timestamp when the record was created"
    )
    day: int = Field(default=1, description="The day of the week (1-based)")
    transcript: Transcript = Field(..., description="The episode transcript")
    fft: WeeklyFFT = Field(..., description="A weeks worth of Food for Thoughts")

class Day(BaseModel):
    """ Daily food for thought and metadata to be used sent to IFTTT """
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec='seconds'),
        description="Timestamp when the record was created"
    )
    food_for_thought: str = Field(..., description="A small idea from the podcast as wisdom to use for your journal entry.")
    prompt: str = Field(..., description="A journal prompt that uses the food for thought as inspiration.")
    podcast_name: str = Field(..., description="The name of the podcast episode")
    podcast_url: str = Field(..., description="The URL of the podcast transcript")
    meta: dict = Field(
        default_factory=lambda: {
            'id': str(uuid.uuid4()),
            'timestamp': int(datetime.now(timezone.utc).timestamp())
        },
        description="Metadata including a unique id and timestamp"
    )

class User(BaseModel):
    timezone: str

class IftttSource(BaseModel):
    id: str
    url: str

class TriggerPayload(BaseModel):
    """ Required payload for the trigger to run. """
    trigger_identity: str
    triggerFields: Dict[str, Any]
    limit: Optional[int] = 3
    user: User
    ifttt_source: Optional[IftttSource] = None


# -- Middleware --
@app.middleware("http")
async def check_service_key(request: Request, call_next):
    """ Checks if the IFTTT request is authorized (ensures the request holds the right service key). """
    headers = request.headers
    if 'IFTTT-Service-Key' not in headers or headers['IFTTT-Service-Key'] != IFTTT_SERVICE_KEY :
      content = {"errors": [{"message": "Unauthorized"}]}
      return JSONResponse(content = content, status_code = status.HTTP_401_UNAUTHORIZED)
    response = await call_next(request)
    return response


# -- Service health check --
@app.get('/ifttt/v1/status', status_code=status.HTTP_200_OK)
def check():
    return

@app.post('/ifttt/v1/test/setup', status_code=status.HTTP_200_OK)
def test_setup():
    data = {"accessToken": IFTTT_SERVICE_KEY}
    return {'data': data}


# -- Triggers --
@app.post('/ifttt/v1/triggers/new_fft', status_code=status.HTTP_200_OK)
def new_fft(trigger_payload: TriggerPayload):
    """ A trigger that returns the most recent FFT Day """
    data = []
    logger.info(f"trigger_payload: {trigger_payload}")

    days_length = r.llen('days')
    logger.info(f"Length of 'days' in Redis: {days_length}")

    if days_length:
      day_raw = r.lindex("days", -1)
      day = Day.parse_raw(day_raw) if day_raw else None
      day.meta['timestamp'] = int(datetime.now(timezone.utc).timestamp())
      data.append(day.dict())

    logger.info(f"... Data {data}")

    return {'data': data}

# -- Cron endpoints --
@app.post("/create_week", status_code=status.HTTP_200_OK)
def create_week():
    """ Creates the current Week in Redis (stores 7 FFT's) to create days from. 
        Cron will run this weekly. 
    """
    logger.info("Creating week ...")
    logger.info("... Extracting transcript")
    transcript = extract_latest_transcript()
    logger.info(f"... Transcript {transcript}")
    weekly_fft = generate_fft(transcript)
    week = Week(
      created_at=datetime.now(timezone.utc).isoformat(timespec='seconds'),
      transcript=transcript,
      fft=weekly_fft
    )

    logger.info(f"... Week {week}")
    # Append weekly_fft or create an empty Redis List "weeks"
    r.rpush("weeks", week.json())
    
    return {"message": "Weekly FFT generated and stored.", "week": week.model_dump()}


@app.get("/get_weeks", status_code=status.HTTP_200_OK)
def get_weeks(limit: Optional[int] = 10):
    """
    Retrieve the most recent weeks from Redis.
    """
    weeks = []
    weeks_length = r.llen("weeks")
    for i in range(1, min(limit, weeks_length) + 1):
        week_raw = r.lindex("weeks", -i)
        week = Week.parse_raw(week_raw) if week_raw else None
        if week:
            weeks.append(week)
    return {"data": weeks}


@app.post("/create_day", status_code=status.HTTP_200_OK)
def create_day():
    """ Creates the Day FFT in Redis from the current week. Cron runs this daily. """
    logger.info("Creating day ...")
    # Grab the latest week from Redis
    week_raw = r.lindex("weeks", -1)
    week = Week.parse_raw(week_raw) if week_raw else None
    
    if not week:
        return {"error": "No week found. Please generate a week first."}, 400

    # Find the first unused FoodForThought for the day (cap at 7th day)
    used_days = min(week.day, 7)
    fft_attr = f"food_for_thought_{used_days}"
    fft = getattr(week.fft, fft_attr, None)

    if not fft:
        return {"error": "No more days available in the current week. Please generate a new week."}, 400

    day = Day(
      created_at = datetime.now(timezone.utc).isoformat(timespec='seconds'),
      food_for_thought = fft.food_for_thought,
      prompt = fft.journal,
      podcast_name = week.transcript.name,
      podcast_url = week.transcript.url,
      meta = {
          "id": str(uuid.uuid4()),
          "timestamp": int(datetime.now(timezone.utc).timestamp())
      }
    )
    logger.info(f"... Day {day}")

    # Store in redis
    r.rpush("days", day.json())

    # Replace the updated day in Redis
    week.day = min(week.day+1, 7)
    r.lset("weeks", -1, week.json())

    return {"message": "Day created and stored.", "day": day}


@app.get("/get_days", status_code=status.HTTP_200_OK)
def get_days(limit: int = 50):
    """
    Retrieve the most recent days from Redis, up to the specified limit.
    """
    days = []
    days_length = r.llen("days")
    for i in range(1, min(limit, days_length) + 1):
        day_raw = r.lindex("days", -i)
        day = Day.parse_raw(day_raw) if day_raw else None
        if day:
            days.append(day)
    return {"data": days}