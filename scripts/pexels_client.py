"""
Модуль поиска и генерации визуальных референсов через Pexels API.
Позволяет находить реальные фото высокого качества для интерьеров,
городских локаций, уютных деталей и использовать их описания / композиции
для построения абсолютно не-шаблонных, живых фото-промптов.
"""

import json
import os
import random
import urllib.request
import urllib.parse

def fetch_pexels_idea(query: str, api_key: str = None) -> dict:
    """
    Ищет фото на Pexels по запросу и возвращает описание / тему для идеи визуализации.
    Если API-ключ не задан или запрос завершился ошибкой, возвращает структурированный fallback.
    """
    key = api_key or os.environ.get("PEXELS_API_KEY", "")
    if not key:
        return {}
    
    url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(query)}&per_page=5&orientation=square"
    req = urllib.request.Request(url, headers={"Authorization": key, "User-Agent": "ExcaliburPexelsClient/1.0"})
    
    try:
        with urllib.request.urlopen(req, timeout=7) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            photos = data.get("photos", [])
            if photos:
                chosen = random.choice(photos)
                return {
                    "alt": chosen.get("alt", ""),
                    "url": chosen.get("src", {}).get("large", ""),
                    "photographer": chosen.get("photographer", "")
                }
    except Exception as e:
        print(f"Pexels API note: {e}")
    
    return {}
