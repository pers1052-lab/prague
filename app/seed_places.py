"""여행일지 [가족 앨범]의 장소들을 [장소공유] 목록에 등록합니다 (앱 시작 시 1회, 이미 있으면 건너뜀)."""
import secrets

from . import db as dbmod
from .journal_data import DAYS

FAMILY_EMAIL = "family@prague-trip.local"
FAMILY_NICKNAME = "프라하 가족"

# 목록 사진: 여행일지 해당 구간의 대표(landmark) 사진
PHOTO_FROM_SEGMENT = {
    "oldtown_sq": "d1_s2", "republic_sq": "d3_s3", "castle": "d4_s3", "strahov": "d4_s2",
    "charles_bridge": "d3_s2", "riverside": "d5_s2", "mala_strana": "d6_s3", "dresden": "d6_s1",
    "krumlov": "d7_s1", "hluboka": "d8_s2", "vinohrady": "d10_s1", "museum": "d9_s1",
    "riegrovy": "d9_s2", "airport": "d10_s2",
}

# (album key, 이름, 카테고리, 위도, 경도, 설명) — 좌표는 여행일지 지도, 설명은 일지 내용 기준
PLACES = [
    ("oldtown_sq", "구시가지 광장", "관광지", 50.0879, 14.4212,
     "도착 첫날 노을 속에서 처음 산책한 곳. 성 미쿨라셰 성당과 틴 성모 교회, 정각마다 인형극이 열리는 천문시계(Orloj)가 모여 있어요. 관광객이 적은 이른 아침에 가면 천문시계를 여유롭게 볼 수 있습니다. (여행일지 Day 1–2)"),
    ("republic_sq", "공화국 광장", "관광지", 50.0888, 14.4285,
     "트램이 오가는 광장으로, 노을 무렵 노천 테라스에서 한 잔 하며 쉬기 좋았던 곳. 주변 상점가에서 저녁 쇼핑도 했어요. (여행일지 Day 3)"),
    ("castle", "프라하 성", "관광지", 50.0905, 14.3998,
     "성 비투스 대성당의 스테인드글라스, 골든 레인의 작은 집들, 왕실 정원까지 이틀에 걸쳐 둘러봤어요. 성벽에서 보는 노을 전망이 특히 좋습니다. (여행일지 Day 4–5)"),
    ("strahov", "스트라호프 수도원", "관광지", 50.0864, 14.3890,
     "어두운 목조와 금장 장식, 프레스코 천장화가 인상적인 수도원 성당. 프라하 성으로 가는 언덕 위에 있어 함께 묶어 돌기 좋아요. (여행일지 Day 4)"),
    ("charles_bridge", "까를교", "관광지", 50.0862, 14.4140,
     "구시가 다리탑을 지나 건너며 프라하 성을 바라보는 다리. 낮의 풍경도 좋지만, 조명이 켜진 밤 야경과 노을 시간이 특히 아름다워요. (여행일지 Day 3–5)"),
    ("riverside", "블타바 강변", "관광지", 50.0865, 14.4109,
     "까를교 인근 강변 산책로. 뉴트리아와 오리들을 구경할 수 있고, 밤에는 야간 크루즈로 조명 켜진 프라하 성과 까를교를 강 위에서 볼 수 있습니다. (여행일지 Day 3–6)"),
    ("mala_strana", "말라스트라나", "관광지", 50.0877, 14.4050,
     "화려한 금장 내부의 성 미쿨라셰 성당과 존 레논 벽이 있는 동네. 드레스덴에서 돌아온 밤, 샤브샤브로 저녁을 먹고 성당 야경을 봤어요. (여행일지 Day 4, 6)"),
    ("dresden", "드레스덴 (독일)", "관광지", 51.0516, 13.7427,
     "프라하에서 당일치기로 다녀온 독일 도시. 프라우엔 교회, 츠빙거 궁전, 엘베강변 산책까지 하루에 둘러볼 수 있어요. (여행일지 Day 6)"),
    ("krumlov", "체스키 크룸로프", "관광지", 48.8122, 14.3124,
     "굽이치는 블타바 강을 따라 자리한 동화 같은 마을. 성에서 내려다보는 구시가지 전망과 노을 속 저녁 산책이 기억에 남아요. (여행일지 Day 7–8)"),
    ("hluboka", "흘루보카 성", "관광지", 49.0513, 14.4415,
     "하얀 네오고딕 외벽이 아름다운 '백조의 성'. 사냥 트로피 전시실과 스테인드글라스 계단창, 정원이 볼거리예요. 프라하와 체스키 크룸로프 사이 남보헤미아에 있어 오가는 길에 들르기 좋습니다. (여행일지 Day 8)"),
    ("vinohrady", "비노흐라디", "기타", 50.0805, 14.4370,
     "여행 후반에 묵었던 조용한 주거 지역. 나무 그늘이 드리운 거리와 카페, 레스토랑이 많아 여유로운 아침과 식사를 즐기기 좋아요. (여행일지 Day 8–10)"),
    ("museum", "국립 박물관", "관광지", 50.0789, 14.4310,
     "바츨라프 광장 끝에 있는 박물관. 유리돔 아트리움과 아치형 로비, 돔 천장화가 화려해서 건물 자체가 볼거리입니다. (여행일지 Day 9)"),
    ("riegrovy", "리흐로비 공원 (Riegrovy sady)", "관광지", 50.0798, 14.4401,
     "잔디밭에 앉아 프라하 성까지 보이는 노을 파노라마를 감상할 수 있는 공원. 저녁이면 노을을 보러 사람들이 모여들어요. (여행일지 Day 9)"),
    ("airport", "바츨라프 하벨 공항", "기타", 50.1009, 14.2685,
     "프라하 국제공항. 시내까지는 119번 버스 + 지하철 A선 조합이 저렴하고 빠릅니다. (여행일지 Day 10)"),
]


def seed():
    hero = {b["gallery"]: b["hero"] for d in DAYS for b in d["blocks"] if b["type"] == "segment"}

    conn = dbmod.get_conn()
    user = conn.execute("SELECT id FROM users WHERE email=?", (FAMILY_EMAIL,)).fetchone()
    if user:
        uid = user["id"]
    else:
        # Owner account for the seeded places; the random hash means nobody can log in as it.
        uid = conn.execute(
            "INSERT INTO users (email, password_hash, salt, nickname, created_at) VALUES (?, ?, ?, ?, ?)",
            (FAMILY_EMAIL, secrets.token_hex(32), secrets.token_hex(16), FAMILY_NICKNAME, dbmod.now()),
        ).lastrowid

    for key, name, category, lat, lng, desc in PLACES:
        if conn.execute("SELECT 1 FROM places WHERE user_id=? AND name=?", (uid, name)).fetchone():
            continue
        conn.execute(
            """INSERT INTO places (user_id, name, category, lat, lng, description, photo_path, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (uid, name, category, lat, lng, desc, hero[PHOTO_FROM_SEGMENT[key]], dbmod.now()),
        )
    conn.commit()
    conn.close()
