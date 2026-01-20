from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import random

app = FastAPI()

# CORS ruxsatlari (Sayt ulanishi uchun)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Hamma joydan kirishga ruxsat
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------
# 🔑 SIZNING API KALITINGIZ (RAPIDAPI)
# -------------------------------------------
API_KEY = "2da680bcd3mshd636b1602b1c015p122a64jsn99f8ef4fd8b1"  # <--- Kalitni shu yerga qo'ying!
# -------------------------------------------

@app.get("/")
def home():
    return {"message": "InstaAudit API ishlamoqda! (Powered by RocketAPI)"}

@app.get("/analyze/{username}")
def analyze_user(username: str):
    
    # 1. RapidAPI (RocketAPI) ga so'rov yuboramiz
    url = "https://rocketapi-for-instagram.p.rapidapi.com/instagram/user/get_info"
    querystring = {"username": username}
    
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "rocketapi-for-instagram.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()
        
        # Agar foydalanuvchi topilmasa yoki xato bo'lsa
        if response.status_code != 200 or "status" in data and data["status"] == "fail":
             raise HTTPException(status_code=404, detail="Instagram foydalanuvchisi topilmadi yoki yopiq profil")

        # 2. Kerakli ma'lumotlarni ajratib olamiz
        user_info = data.get("response", {}).get("body", {})
        
        # Agar bo'sh kelsa (himoyalangan profil)
        if not user_info:
             raise HTTPException(status_code=404, detail="Ma'lumot olib bo'lmadi")

        full_name = user_info.get("full_name", "")
        followers = user_info.get("edge_followed_by", {}).get("count", 0)
        following = user_info.get("edge_follow", {}).get("count", 0)
        media_count = user_info.get("edge_owner_to_timeline_media", {}).get("count", 0)
        avatar_url = user_info.get("profile_pic_url_hd", "")
        is_private = user_info.get("is_private", False)

        # 3. Analitika hisoblash (Sun'iy logika)
        
        # Engagement Rate (ER) taxminiy hisoblash
        # (API tekin versiyasida har doim ham like sonini bermaydi, shuning uchun o'rtacha hisoblaymiz)
        avg_likes = int(followers * random.uniform(0.03, 0.08)) if not is_private else 0
        avg_comments = int(avg_likes * 0.02)
        
        er = 0
        if followers > 0:
            er = round(((avg_likes + avg_comments) / followers) * 100, 2)

        # Fake Score (Soxtalik darajasi)
        fake_score = 15
        if followers > 10000 and er < 1: fake_score += 40  # Obunachi ko'p, lekin aktivlik yo'q
        if media_count < 5: fake_score += 30                # Postlar juda kam
        if not user_info.get("highlight_reel_count", 0): fake_score += 10 # Istoriya yo'q
        fake_score = min(fake_score, 100)

        # Ad Score (Reklama berishga loyiqlik)
        ad_score = 100 - fake_score
        if is_private: ad_score = 0

        # Postlar tarixi (Grafik uchun)
        # Haqiqiy postlarni olish uchun alohida API so'rov kerak, 
        # limitni tejash uchun bu yerda simulyatsiya qilamiz:
        history_posts = []
        if not is_private:
            base_like = avg_likes
            for _ in range(10):
                history_posts.append(int(base_like * random.uniform(0.8, 1.2)))

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
        print(f"Xatolik: {e}")
        raise HTTPException(status_code=500, detail=f"Server xatosi: {str(e)}")
