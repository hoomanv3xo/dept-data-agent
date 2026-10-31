import os
from dotenv import load_dotenv
import cohere

load_dotenv()
key = os.getenv("COHERE_API_KEY")
print("Key found:", bool(key), "| starts with:", (key or "")[:4])
co = cohere.ClientV2(api_key=key)
r = co.chat(model=os.getenv("COHERE_MODEL", "command-a-plus-05-2026"),
            messages=[{"role": "user", "content": "Say hello in five words."}])
print("".join(getattr(c, "text", "") or "" for c in r.message.content))