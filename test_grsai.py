import urllib.request
import json

api_key = "sk-83ab92e75ed64ac6825b0f71cede2fbf"
url = "https://grsaiapi.com/v1/images/generations"

prompt = (
    "Square 1:1 format. Modern luxury Scandinavian style apartment living room in Tyumen near lake and park, "
    "view from window on quiet lake, cozy king size bed with hotel crisp white linen, emerald green designer curtains, "
    "coral red accents and tea cup on wooden table, warm golden sunset light. "
    "Clean typography banner with Russian text: 'Выходные в Тюмени'. "
    "Professional commercial interior photography, 4k detail, photorealistic."
)

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

data = {
    "model": "gpt-image-2",
    "prompt": prompt,
    "n": 1,
    "size": "1024x1024"
}

req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)

try:
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print("SUCCESS:", json.dumps(res, ensure_ascii=False, indent=2))
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code, e.read().decode("utf-8"))
except Exception as e:
    print("Error:", e)
