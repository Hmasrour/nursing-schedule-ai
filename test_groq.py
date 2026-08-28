import requests, os
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GROQ_API_KEY")

resp = requests.get(
    "https://api.groq.com/openai/v1/models",
    headers={"Authorization": f"Bearer {api_key}"}
)
if resp.status_code == 200:
    models = [m["id"] for m in resp.json()["data"]]
    print("Valid models:", models)
else:
    print(resp.status_code, resp.text)
