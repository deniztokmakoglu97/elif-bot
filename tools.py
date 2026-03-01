from datetime import datetime
import math
import random
import json, inspect
from config import OPENWEATHER_API_KEY, TAVILY_API_KEY
import requests
from tavily import TavilyClient


#### 1. TOOLS FUNCTIONS ###

def get_datetime() -> str:
    return datetime.now().strftime("%d:%m:%Y %H:%M:%S")

def calculate(expression: str) -> str:
    try:
        result = eval(expression, {"__builtins__": {}}, vars(math))
        return str(result)
    except Exception as e:
        return f"Error: {e}"

def flip_coin() -> str:
    return random.choice(["Heads", "Tails"])

def safe_call(fn, fn_args):
    if fn_args is None:
        fn_args = {}
    if isinstance(fn_args, str):
        fn_args = json.loads(fn_args)

    sig = inspect.signature(fn)
    allowed = set(sig.parameters.keys())
    cleaned = {k: v for k, v in fn_args.items() if k in allowed}

    return fn(**cleaned) if cleaned else fn()

def get_weather(city: str):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
        "lang": "tr"
    }

    response = requests.get(url, params=params)
    data = response.json()

    if response.status_code != 200:
        return f"Error: {data.get('message', 'unknown error')}"
    
    desc = data["weather"][0]["description"]
    temp = data["main"]["temp"]
    feels_like = data["main"]["feels_like"]
    wind_speed = data["wind"]["speed"]

    context = f"{city}: description {desc}, temperature {temp}°C (feels like {feels_like}°C), wind speed {wind_speed} m/s."

    return context

def search_web(query: str) -> str:
    client = TavilyClient(api_key=TAVILY_API_KEY)
    response = client.search(query, max_results=3)

    context = f"""Search results for '{query}':\n
    {"-" + " ".join([f"{i+1}. {r['title']} ({r['content']})" for i, r in enumerate(response["results"])])}
    """

    return context


### Guardrails ###
def safe_call(fn, fn_args):
    if fn_args is None:
        fn_args = {}
    if isinstance(fn_args, str):
        fn_args = json.loads(fn_args)

    sig = inspect.signature(fn)
    allowed = set(sig.parameters.keys())
    cleaned = {k: v for k, v in fn_args.items() if k in allowed}

#### 2. FUNCTION MAP ###
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_datetime",
            "description": "Get the current time in DD:MM:YY format.",
            "parameters": {"type": "object", "properties": {}, "required": [],   "additionalProperties": False}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluates a math expression. Supports sqrt, sin, cos, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Math expression to evaluate"}
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "flip_coin",
            "description": "Flip a random coin and return Heads or Tails.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Returns the weather description of a given city including temperature and wind speed.",
            "parameters": {"type": "object", 
                           "properties": {
                               "city": {"type": "string", "description": "city name to get weather for"}
                           }, 
                           "required": ["city"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Returns the web query results for a given search query.",
            "parameters": {"type": "object", 
                           "properties": {
                               "query": {"type": "string", "description": "web search query"}
                           }, 
                           "required": ["query"]}
        }
    }
]

FUNCTION_MAP = {"get_datetime": get_datetime, "calculate": calculate, "flip_coin": flip_coin, "get_weather": get_weather, "search_web": search_web}