import os
from dotenv import load_dotenv

def load_env():
    env = os.getenv("ENVIRONMENT", "development")

    if env == "production":
        load_dotenv(".env.prod")
    else:
        load_dotenv(".env.dev")
