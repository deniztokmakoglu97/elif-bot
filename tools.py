from datetime import datetime
import math
import random
import json, inspect

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
    }
]

FUNCTION_MAP = {"get_datetime": get_datetime, "calculate": calculate, "flip_coin": flip_coin}