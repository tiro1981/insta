from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# 👇 KALITNI SHU YERGA QO'YING (Tirnoqlar ichiga!)
# ---------------------------------------------------------
API_KEY = "2da680bcd3mshd636b1602b1c015p122a64jsn99f8ef4fd8b1" 
# ---------------------------------------------------------

@app.get("/")
def home():
    return {"message": "Server ishlayapti!"}

@app.get("/analyze/{username}")
def analyze_user(username: str):
    print(f"🔍 TEKSHIRILMOQDA: {username}")
    
    url = "https://rocketapi-for-instagram.p.rapidapi.com/instagram/user/get_info"
    payload = {"username": username}
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "rocketapi-for-instagram.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=payload)
        data = response.json()
        
        # 🛑 DIAGNOSTIKA: Server javobini Logga chiqaramiz
        print(f"📡 API STATUS: {response.status_code}")
        print(f"📄 API JAVOBI: {data}")

        if response.status_code != 200:
            # Agar kalit xato bo'lsa yoki obuna bo'lmasa
            error_msg = data.get("message", "Noma'lum xatolik")
            raise HTTPException(status_code=400, detail=f"API Xatosi: {error_msg}")

        user_info = data.get("response", {}).get("body", {})
        
        if not user_info:
            raise HTTPException(status_code=404, detail="Profil topilmadi (Yoki yopiq)")

        # Ma'lumotlarni yig'ish
        followers = user_info.get("edge_followed_by", {}).get("count", 0)
        # ... (qolgan logika soddalashtirildi test uchun) ...

        return {
            "username": username,
            "followers": followers,
            "full_name": user_info.get("full_name", ""),
            "avatar_url": user_info.get("profile_pic_url_hd", ""),
            "ad_score": 50 # Test uchun
        }

    except Exception as e:
        print(f"❌ KATTA XATOLIK: {e}")
        raise HTTPException(status_code=500, detail=str(e))
