from dotenv import load_dotenv
load_dotenv()
from google import genai

client = genai.Client()
for m in client.models.list():
    actions = getattr(m, "supported_actions", None) or []
    if "embedContent" in actions or "embed" in (m.name or "").lower():
        print(m.name, actions)