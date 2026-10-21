import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

veo_models = [
    "veo-3.1-fast-generate-preview",
    "veo-3.1-generate-preview",
    "veo-3.1-lite-generate-preview"
]

print("Testing direct Veo 3 call...")
for m in veo_models:
    print(f"\n--- Model: {m} ---")
    try:
        op = client.models.generate_videos(
            model=m,
            prompt="A cute cartoon octopus floating underwater, 3D Pixar animation style, 9:16 vertical ratio",
            config=types.GenerateVideosConfig(
                aspect_ratio="9:16"
            )
        )
        print(f"SUCCESS on {m}!")
        print("Operation name:", op.name)
        print("Operation done:", op.done)
        break
    except Exception as e:
        print(f"Error on {m}: {e}")
