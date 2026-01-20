from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import instaloader
import statistics

app = FastAPI()

# Frontend brauzerdan ulanishi uchun ruxsatlar (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instagramga ulanish uchun vosita
L = instaloader.Instaloader()

# ---------------- LOGIKA QISMI ----------------

def calculate_ad_score(er, fake_prob, growth_trend):
    """
    Reklama berish bahosini hisoblash formulasi.
    """
    base_score = 50
    
    # ER (Jalb qilish) ta'siri
    if er > 5: base_score += 40
    elif er > 2: base_score += 20
    else: base_score -= 10
    
    # Fake (Soxtalik) ta'siri
    base_score -= (fake_prob / 2)
    
    # Trend ta'siri
    if growth_trend == "up": base_score += 10
    
    return max(0, min(100, int(base_score)))

# ---------------- API ENDPOINTS ----------------

@app.get("/")
def read_root():
    return {"status": "Active", "service": "InstaAudit Real Backend"}

@app.get("/analyze/{username}")
def analyze_profile(username: str):
    """
    Haqiqiy Instagram ma'lumotlarini olib, Frontendga 
    eski dizayn formatida qaytaradi.
    """
    try:
        # 1. Instagramdan profilni yuklash
        profile = instaloader.Profile.from_username(L.context, username)
        
        # 2. Ma'lumotlarni olish
        followers = profile.followers
        
        # Agar profil yopiq bo'lsa
        if profile.is_private:
             raise HTTPException(status_code=400, detail="Profil yopiq (Private)")

        # 3. Postlarni tahlil qilish (Oxirgi 10 ta)
        posts_likes = []
        posts_comments = []
        count = 0
        
        for post in profile.get_posts():
            posts_likes.append(post.likes)
            posts_comments.append(post.comments)
            count += 1
            if count >= 10: break
            
        if not posts_likes:
            raise HTTPException(status_code=400, detail="Postlar yo'q")

        # 4. Hisob-kitoblar
        avg_likes = int(statistics.mean(posts_likes))
        avg_comments = int(statistics.mean(posts_comments))
        
        # ER hisoblash
        er = 0
        if followers > 0:
            er = round(((avg_likes + avg_comments) / followers) * 100, 2)
            
        # Fake (Soxta) ehtimolini hisoblash (Real logika)
        fake_score = 0
        if followers > 10000 and er < 0.5: fake_score = 80 # Obunachi ko'p, aktivlik yo'q
        elif er > 20: fake_score = 60 # Juda shubhali yuqori aktivlik
        
        # Trendni aniqlash
        # Postlar yangidan eskisiga qarab keladi, shuning uchun teskari qaraymiz
        trend = "up" if posts_likes[0] > posts_likes[-1] else "down"
        
        # AdScore hisoblash
        final_score = calculate_ad_score(er, fake_score, trend)

        # 5. Javob qaytarish (Frontend dizayni buzilmasligi uchun eski formatda)
        return {
            "username": username,
            "avatar_url": profile.profile_pic_url,
            "followers": f"{followers:,}".replace(",", " "),
            "avg_likes": f"{avg_likes:,}".replace(",", " "),
            "avg_comments": avg_comments,
            "er": er,
            "fake_score": fake_score,
            "ad_score": final_score,
            "history_posts": posts_likes[::-1] # Grafik uchun to'g'irlash
        }

    except instaloader.exceptions.ProfileNotExistsException:
        raise HTTPException(status_code=404, detail="Bunday user topilmadi")
    except instaloader.exceptions.ConnectionException:
        raise HTTPException(status_code=503, detail="Instagram ulanish xatosi (IP bloklangan)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))