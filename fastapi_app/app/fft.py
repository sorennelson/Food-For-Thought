

from langchain_google_genai import ChatGoogleGenerativeAI
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

INDEX_URL = "https://tim.blog/2018/09/20/all-transcripts-from-the-tim-ferriss-show/"
BASE_URL = "https://tim.blog"


# -- Objects --
class Transcript(BaseModel):
    """ Information about a show transcript. """
    name: str = Field(..., description="The name of the episode")
    url: str = Field(..., description="The URL of the transcript")

class FoodForThought(BaseModel):
    """ A food for thought for the day. """
    food_for_thought: str = Field(..., description="A small idea from the podcast as wisdom to use for your journal entry.")
    journal: str = Field(..., description="A journal prompt that uses the food for thought as inspiration.")

class WeeklyFFT(BaseModel):
    """ A weeks worth of Food for Thoughts. """
    food_for_thought_1: FoodForThought = Field(..., description="The first food for thought for the week.")
    food_for_thought_2: FoodForThought = Field(..., description="The second food for thought for the week.")
    food_for_thought_3: FoodForThought = Field(..., description="The third food for thought for the week.")
    food_for_thought_4: FoodForThought = Field(..., description="The fourth food for thought for the week.")
    food_for_thought_5: FoodForThought = Field(..., description="The fifth food for thought for the week.")
    food_for_thought_6: FoodForThought = Field(..., description="The sixth food for thought for the week.")
    food_for_thought_7: FoodForThought = Field(..., description="The seventh food for thought for the week.")
    

# -- Transcript --
def __list_transcript_links(url: str):
    """ Scrape the Tim Ferriss transcripts index page for transcript URLs and names. """
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    links_and_names = []
    for a in soup.select("a[href]"):
        text = a.get_text(strip=True)
        # Basic cleaning and filtering for transcript links
        if BASE_URL in a["href"]: 
            links_and_names.append((f'{text} - {a["href"]}'))

    return '\n'.join(links_and_names)

def extract_latest_transcript():
    """ Returns a Transcript object with the latest Tim Ferriss Show transcript. """
    all_transcripts = __list_transcript_links(INDEX_URL)
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    structured_llm = llm.with_structured_output(Transcript)
    prompt = f'Extract the latest transcript name and url from the following:\n\n{all_transcripts}'
    # Future random episode prompt
    # prompt = f'The following is a list of podcast episode titles and their transcript url from the podcast, the Tim Ferriss Show. Extract a podcast name and url that are with guest Naval Ravikant from the following list. Ignore any that are PDF links. If the guest is not listed then pick a similar guest:\n\n{all_transcripts}'
    transcript = structured_llm.invoke(("human", prompt))
    return transcript

# -- FFT --
def __fetch_transcript_content(transcript: Transcript):
    """ Fetch page content from a given transcript URL. """
    transcript_content = ""
    try:
        resp = requests.get(transcript.url)
        resp.raise_for_status() 
        soup = BeautifulSoup(resp.text, "html.parser")
        # Extract a newline separated string of all <p>'s on the page
        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")]
        transcript_content = "\n".join(paragraphs)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching transcript content: {e}")
    return transcript_content
    
def generate_fft(transcript: Transcript):
    """ Returns 7 journal prompts (WeeklyFFT) from the given Transcript content. """
    transcript_content = __fetch_transcript_content(transcript)

    prompt = f"""Extract 7 bits of wisdom and journal entries from the following: 

    Example food for thought:
    The assumptions I make shape the boundaries of my life — if one of them is wrong, then so are the limits they create.
    This question helps challenge your mental models and uncover hidden beliefs that may be limiting your potential. It's a powerful tool for breaking free from self-imposed constraints and fostering personal growth.


    Example journal entry:
    “What assumptions am I making that might be wrong?”

    ---

    Content: \n\n{transcript_content}"""

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    structured_week_llm = llm.with_structured_output(WeeklyFFT)
    fft = structured_week_llm.invoke(
        ("human", prompt)
    )
    return fft