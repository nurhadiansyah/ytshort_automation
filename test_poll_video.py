import requests

print("Testing Pollinations video endpoint...")
try:
    r = requests.get("https://video.pollinations.ai/prompt/a%20cute%20cat", timeout=10)
    print("Video endpoint status:", r.status_code)
except Exception as e:
    print("Video endpoint error:", e)
