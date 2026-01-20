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
# 🔑 KALIT (O'ZGARISHSIZ)
# ---------------------------------------------------------
API_KEY = "2da680bcd3mshd636b1602b1c015p122a64jsn99f8ef4fd8b1"
# ---------------------------------------------------------

@app.get("/")
def home():
    return {"message": "InstaAudit Lite Server v2.0 Running!"}

@app.get("/analyze/{username}")
def analyze_user(username: str):
    
    url = "https://instagram-scraper-20251.p.rapidapi.com/userinfo/"
    headers = {
        "x-rapidapi-key": API_KEY,
        "x-rapidapi-host": "instagram-scraper-20251.p.rapidapi.com"
    }
    querystring = {"username_or_id": username}

    try:
        print(f"🔍 So'rov: {username}")
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()

        if response.status_code != 200:
             raise HTTPException(status_code=400, detail="API xatosi")

        user_data = data.get("data", {})
        if not user_data: user_data = data # Ba'zan to'g'ridan-to'g'ri keladi

        if not user_data or "username" not in user_data:
             raise HTTPException(status_code=404, detail="Profil topilmadi")

        # --- MA'LUMOTLARNI OLISH ---
        full_name = user_data.get("full_name", "")
        followers = user_data.get("follower_count", 0)
        following = user_data.get("following_count", 0)
        media_count = user_data.get("media_count", 0)
        is_private = user_data.get("is_private", False)
        is_verified = user_data.get("is_verified", False)
        
        # Rasm: Avval HD versiyasini, bo'lmasa oddiysini olish
        avatar_url = user_data.get("profile_pic_url_hd", user_data.get("profile_pic_url", ""))

        # --- SUN'IY TAHLIL (Chunki real data yo'q) ---
        
        # Engagement Rate (Sun'iy)
        base_er = random.uniform(1.5, 5.0) # O'rtacha 1.5% dan 5% gacha
        if followers > 100000: base_er = random.uniform(0.5, 2.5) # Katta profillarda kamroq
        if is_private: base_er = 0

        avg_likes = int(followers * (base_er / 100))
        avg_comments = int(avg_likes * random.uniform(0.01, 0.05))
        er = round(base_er, 2)

        # Ishonch Balli (Score) Hisoblash
        score = 50 # Bazaviy ball
        
        if is_verified: score += 20 # Galochkasi bor
        if media_count > 50: score += 10 # Postlari ko'p
        if followers > following * 2: score += 10 # Obunachisi ko'p
        if full_name: score += 5 # Ismi yozilgan

        if followers > 50000 and media_count < 10: score -= 30 # Shubhali: ko'p obunachi, kam post
        if er < 0.5 and followers > 10000: score -= 20 # Shubhali: aktivlik o'lik
        
        # Chegaralar
        score = max(10, min(score, 95))
        if is_private: score = 10 # Yopiq profilga past ball

        fake_score = 100 - score

        # Grafik Simulyatsiyasi
        history_posts = []
        if not is_private and media_count > 0:
            curr = avg_likes
            for _ in range(10):
                # Trend yaratish (o'sib boruvchi yoki tushuvchi)
                trend = random.uniform(0.9, 1.15)
                curr = int(curr * trend)
                history_posts.append(curr)

        return {
            "username": user_data.get("username"),
            "followers": followers,
            "media_count": media_count,
            "avatar_url": avatar_url,
            "er": er,
            "avg_likes": avg_likes,
            "fake_score": fake_score,
            "ad_score": score,
            "history_posts": history_posts,
            "is_private": is_private
        }

    except Exception as e:
        print(f"❌ XATOLIK: {e}")
        raise HTTPException(status_code=500, detail=str(e))
