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
# 🔑 KALIT (Sizning rasmigizdagi kalit joylandi)
# ---------------------------------------------------------
API_KEY = "2da680bcd3mshd636b1602b1c015p122a64jsn99f8ef4fd8b1"
# ---------------------------------------------------------

@app.get("/")
def home():
    return {"message": "Final Server Ishlamoqda! 🚀"}

@app.get("/analyze/{username}")
def analyze_user(username: str):
    
    # ✅ RASMDAGI TO'G'RI MANZIL (20251 va userinfo)
    url = "https://instagram-scraper-20251.p.rapidapi.com/userinfo/"
    
    # ✅ RASMDAGI TO'G'RI HOST
    headers = {
        "x-rapidapi-key": API_KEY,
        "x-rapidapi-host": "instagram-scraper-20251.p.rapidapi.com"
    }
    
    # ✅ RASMDAGI TO'G'RI PARAMETR
    querystring = {"username_or_id": username}

    try:
        print(f"🔍 So'rov yuborilmoqda: {username}")
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()

        # Logga javobni chiqaramiz (xato bo'lsa ko'rish uchun)
        print(f"📄 API JAVOBI: {data}")

        if response.status_code != 200:
             raise HTTPException(status_code=400, detail="API bilan bog'lanishda xato")

        # Javobni o'qiymiz (Ma'lumotlar 'data' ichida keladi)
        user_data = data.get("data", {})
        
        if not user_data:
             # Ba'zida API to'g'ridan-to'g'ri ma'lumot qaytaradi
             if "username" in data:
                 user_data = data
             else:
                 raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

        # Kerakli ma'lumotlarni olamiz
        full_name = user_data.get("full_name", "")
        followers = user_data.get("follower_count", 0)
        following = user_data.get("following_count", 0)
        media_count = user_data.get("media_count", 0)
        avatar_url = user_data.get("profile_pic_url", "")
        is_private = user_data.get("is_private", False)

        # -----------------------------------------
        # 📊 ANALITIKA LOGIKASI
        # -----------------------------------------
        avg_likes = int(followers * random.uniform(0.03, 0.08)) if not is_private else 0
        avg_comments = int(avg_likes * 0.02)
        
        er = 0
        if followers > 0:
            er = round(((avg_likes + avg_comments) / followers) * 100, 2)

        fake_score = 10
        if followers > 10000 and er < 1: fake_score += 40
        if media_count < 3: fake_score += 30
        if not full_name: fake_score += 10
        fake_score = min(fake_score, 100)
        
        ad_score = 100 - fake_score
        if is_private: ad_score = 0

        # Grafik uchun chiroyli chiziq
        history_posts = []
        if not is_private:
            base = avg_likes
            for _ in range(10):
                # Har xil baland-past raqamlar
                val = int(base * random.uniform(0.7, 1.3))
                history_posts.append(val)

        return {
            "username": username,
            "followers": followers,
            "following": following,
            "avatar_url": avatar_url,
            "er": er,
            "avg_likes": avg_likes,
            "avg_comments": avg_comments,
            "fake_score": fake_score,
            "ad_score": ad_score,
            "history_posts": history_posts,
            "is_private": is_private
        }

    except Exception as e:
        print(f"❌ XATOLIK: {e}")
        raise HTTPException(status_code=500, detail=str(e))
