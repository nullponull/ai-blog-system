"""
翠風リゾート AIコンシェルジュ デモ（匿名化版）
- LLM不使用: キーワードマッチによる定型文応答
- デモ公開用: Basic認証なし
"""

import json
import re
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Ryokan AI Concierge Demo")

# ===== Knowledge Base =====
KNOWLEDGE_PATH = Path(__file__).parent / "knowledge.json"
KNOWLEDGE = {}


@app.on_event("startup")
async def load_knowledge():
    global KNOWLEDGE
    with open(KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
        KNOWLEDGE = json.load(f)
    print(f"Knowledge loaded: {len(KNOWLEDGE.get('facilities', {}))} facilities")


# ===== Keyword-based Response Logic =====

def detect_language(text: str) -> str:
    """簡易言語判定"""
    ascii_ratio = sum(1 for c in text if ord(c) < 128) / max(len(text), 1)
    if ascii_ratio > 0.8:
        return "en"
    # 中国語判定
    if re.search(r'[\u4e00-\u9fff]', text) and not re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):
        return "zh"
    return "ja"


def build_response(message: str, lang: str) -> str:
    """キーワードマッチで定型文を返す"""
    msg = message.lower()
    facilities = KNOWLEDGE.get("facilities", {})

    # --- 多言語対応 ---
    detected = detect_language(message)
    if detected == "zh":
        return ("感谢您的咨询。翠风度假村提供5家温泉旅馆，"
                "均配备私人露天温泉。如需中文服务，请联系前台。\n\n"
                "Thank you for your inquiry. Suifu Resorts offers 5 properties "
                "with private open-air hot spring baths. For Chinese language support, "
                "please contact our front desk.")

    if detected == "en" or lang == "en":
        return _build_response_en(msg, facilities)

    return _build_response_ja(msg, facilities)


def _build_response_ja(msg: str, facilities: dict) -> str:
    """日本語キーワードマッチ"""

    # 空室・予約
    if any(w in msg for w in ["空室", "予約", "泊まり", "泊まれ", "宿泊", "空き"]):
        return ("ご予約のお問い合わせありがとうございます。\n\n"
                "翠風リゾートでは5つの施設をご用意しております。\n"
                "・翠風 渓谷の宿（全21室）¥84,150〜\n"
                "・翠風 高原の宿（全9室・離れ）¥99,000〜\n"
                "・老舗旅館 本店（全21室）¥57,750〜\n"
                "・Hotel モダン翠風（全10室）¥23,100〜\n"
                "・翠風 茶寮（全6室）¥28,050〜\n\n"
                "ご希望の日程・人数をお聞かせいただければ、最適な施設をご案内いたします。\n\n"
                "※デモ版のため、実際の空室検索は行っておりません。")

    # 料金・価格
    if any(w in msg for w in ["料金", "価格", "値段", "いくら", "コスパ", "予算", "安い", "リーズナブル"]):
        return ("各施設の参考料金（1室2名・税込）をご案内いたします。\n\n"
                "・翠風 渓谷の宿: ¥84,150〜（食事付き）\n"
                "・翠風 高原の宿: ¥99,000〜（食事付き・全室離れ）\n"
                "・老舗旅館 本店: ¥57,750〜（オールインクルーシブ）\n"
                "・Hotel モダン翠風: ¥23,100〜（素泊まり）\n"
                "・翠風 茶寮: ¥28,050〜（食事付き）\n\n"
                "ご予算に合わせた施設をご提案いたします。お気軽にお尋ねください。")

    # 食事・料理
    if any(w in msg for w in ["食事", "料理", "メニュー", "懐石", "ディナー", "朝食", "レストラン",
                                "ヴィーガン", "ベジタリアン", "アレルギー", "グルメ"]):
        return ("お料理についてご案内いたします。\n\n"
                "「渓谷の宿」季節の懐石と和牛懐石の2コース。\n"
                "  別注: 鮑¥4,400/伊勢海老¥8,800/和牛フィレ¥13,200\n\n"
                "「高原の宿」本格京懐石を全室部屋食で一品ずつ提供。\n"
                "  土鍋炊きご飯。別注: ¥1,650〜¥10,450\n\n"
                "「老舗旅館 本店」山の幸と海の幸の会席料理。\n\n"
                "ヴィーガン・ベジタリアン・アレルギー対応は3日前までにお申し付けください。")

    # 温泉
    if any(w in msg for w in ["温泉", "露天", "風呂", "泉質", "お湯"]):
        return ("温泉についてご案内いたします。\n\n"
                "「渓谷の宿」自家源泉「黄金の湯」pH9.5。美肌の湯。\n"
                "  全室に源泉掛け流し露天風呂付き。檜・ヒバ・御影石の3種。\n\n"
                "「高原の宿」白濁の源泉掛け流し。酸性硫酸塩泉。\n"
                "  全室離れの露天風呂付きヴィラ。\n\n"
                "「老舗旅館 本店」三大美肌泉質を全て含む奇跡の源泉。\n"
                "  エメラルドグリーンの湯。大浴場あり。\n\n"
                "すべての施設で天然温泉をお楽しみいただけます。")

    # アクセス・送迎
    if any(w in msg for w in ["アクセス", "行き方", "送迎", "駐車", "電車", "バス", "タクシー", "車"]):
        return ("アクセスについてご案内いたします。\n\n"
                "「渓谷の宿」最寄り駅からバス約7分。シャトルバスあり。\n"
                "「高原の宿」最寄り駅からバス約30分。送迎リムジンあり（要予約）。\n"
                "「老舗旅館 本店」最寄り駅からバス約30分。無料送迎あり。\n"
                "「Hotel モダン翠風」最寄り駅から徒歩6分。\n"
                "「翠風 茶寮」最寄り駅からバスまたはタクシー。\n\n"
                "空港からのハイヤー手配も承ります（3日前要予約）。")

    # 子連れ・家族
    if any(w in msg for w in ["子供", "子連れ", "家族", "お子様", "キッズ"]):
        return ("お子様連れのご家族には「老舗旅館 本店」がおすすめです。\n\n"
                "唯一お子様を歓迎している施設で、\n"
                "・小学生: 大人料金の50%\n"
                "・幼児: ¥5,000\n"
                "・乳児: 無料\n"
                "でご宿泊いただけます。\n\n"
                "オールインクルーシブのため追加料金を気にせずお過ごしいただけます。\n"
                "他の施設は12歳以上（モダン翠風は13歳以上）となります。")

    # 記念日・特別
    if any(w in msg for w in ["記念日", "誕生日", "プロポーズ", "結婚", "お祝い", "特別"]):
        return ("特別な日のご旅行でしたら「翠風 高原の宿」がおすすめです。\n\n"
                "全9室が離れのプライベートヴィラで、\n"
                "「帝 MIKADO」（136m2）は伊勢海老付き懐石とアーリーCI14時の特別プラン。\n"
                "「姫 HIME」（131m2）は露天風呂と内風呂の両方を備えた贅沢な空間。\n\n"
                "海外有名旅行誌の「ラグジュアリー旅館」にも選出された施設です。\n"
                "¥99,000〜（1室2名食事付き）")

    # 施設比較
    if any(w in msg for w in ["違い", "比較", "おすすめ", "どっち", "どの", "選"]):
        return ("施設の特徴をご案内いたします。\n\n"
                "「渓谷の宿」渓谷沿い。全21室。多彩な客室タイプ。大人専用。\n"
                "「高原の宿」高原。全9室離れ。究極のプライベート。大人専用。\n"
                "「老舗旅館 本店」創業1662年。奇跡の泉質。お子様歓迎。\n"
                "「Hotel モダン翠風」駅近。CI17時/CO13時。リーズナブル。\n"
                "「翠風 茶寮」日帰りも可。カジュアル。¥28,050〜。\n\n"
                "ご人数・目的・ご予算をお聞かせいただければ、最適な施設をご提案します。")

    # キャンセル
    if any(w in msg for w in ["キャンセル", "取消", "変更"]):
        return ("キャンセルポリシーは以下の通りです。\n\n"
                "・4〜7日前: 宿泊料金の10%\n"
                "・1〜3日前: 宿泊料金の50%\n"
                "・当日: 宿泊料金の100%\n\n"
                "ご予約の変更は施設に直接お電話ください。")

    # Wi-Fi、ペット等FAQ
    if any(w in msg for w in ["wi-fi", "wifi", "ネット"]):
        return "全施設で無料Wi-Fiをご利用いただけます。お部屋でも快適にお使いいただけます。"

    if any(w in msg for w in ["ペット", "犬", "猫"]):
        return "申し訳ございませんが、ペットのご宿泊はお受けしておりません。ご了承ください。"

    if any(w in msg for w in ["チェックイン", "チェックアウト"]):
        return ("各施設のチェックイン・チェックアウト時間です。\n\n"
                "・渓谷の宿: CI 15:00 / CO 11:00\n"
                "・高原の宿: CI 15:00 / CO 11:00\n"
                "・老舗旅館 本店: CI 15:00 / CO 10:00\n"
                "・Hotel モダン翠風: CI 17:00 / CO 13:00\n"
                "・翠風 茶寮: CI 15:00 / CO 11:00")

    # 挨拶
    if any(w in msg for w in ["こんにちは", "こんばんは", "はじめまして", "よろしく", "ありがとう"]):
        return ("いらっしゃいませ。翠風リゾートコンシェルジュでございます。\n\n"
                "ご宿泊のご相談、施設のご案内、お料理・温泉のご質問など、\n"
                "何でもお気軽にお尋ねください。")

    # デフォルト
    return ("翠風リゾートコンシェルジュでございます。\n\n"
            "以下のようなご質問にお答えできます。\n"
            "・空室検索・ご予約について\n"
            "・料金プランについて\n"
            "・お料理・温泉について\n"
            "・アクセス・送迎について\n"
            "・お子様連れのご利用について\n\n"
            "お気軽にお尋ねください。\n\n"
            "※このチャットボットはデモ版です。実際のサービスではAIが施設ナレッジと"
            "空室APIを統合し、よりパーソナライズされた回答を提供します。")


def _build_response_en(msg: str, facilities: dict) -> str:
    """英語キーワードマッチ"""

    if any(w in msg for w in ["availab", "book", "stay", "room", "reserv", "vacant"]):
        return ("Thank you for your inquiry about reservations.\n\n"
                "Suifu Resorts offers 5 properties:\n"
                "- Suifu Keikoku (21 rooms) from ¥84,150\n"
                "- Suifu Kogen (9 detached villas) from ¥99,000\n"
                "- Heritage Honten (21 rooms) from ¥57,750\n"
                "- Hotel Modern Suifu (10 rooms) from ¥23,100\n"
                "- Suifu Saryo (6 rooms) from ¥28,050\n\n"
                "Please share your preferred dates and group size for a personalized recommendation.\n\n"
                "* This is a demo. Actual availability search is not available.")

    if any(w in msg for w in ["price", "rate", "cost", "budget", "cheap", "afford"]):
        return ("Room rates (per room, 2 guests, tax included):\n\n"
                "- Suifu Keikoku: from ¥84,150 (with meals)\n"
                "- Suifu Kogen: from ¥99,000 (with meals, detached villas)\n"
                "- Heritage Honten: from ¥57,750 (all-inclusive)\n"
                "- Hotel Modern Suifu: from ¥23,100 (room only)\n"
                "- Suifu Saryo: from ¥28,050 (with meals)")

    if any(w in msg for w in ["food", "meal", "cuisine", "dinner", "breakfast", "menu", "dining",
                                "vegan", "vegetarian", "allergy"]):
        return ("Dining at Suifu Resorts:\n\n"
                "Keikoku: Seasonal kaiseki & wagyu kaiseki.\n"
                "  A la carte: abalone ¥4,400 / Ise lobster ¥8,800 / wagyu fillet ¥13,200\n\n"
                "Kogen: Authentic Kyoto kaiseki, served course by course in your room.\n\n"
                "Heritage Honten: Kaiseki with mountain & sea ingredients.\n\n"
                "Vegan, vegetarian, and allergy accommodations available with 3 days notice.")

    if any(w in msg for w in ["onsen", "bath", "hot spring", "spa"]):
        return ("Hot Springs at Suifu Resorts:\n\n"
                "Keikoku: Private source 'Golden Water' pH 9.5. Hinoki, Hiba & granite baths.\n"
                "Kogen: Milky white acidic spring. All rooms with private open-air bath.\n"
                "Heritage Honten: Miraculous spring with all 3 skin-beautifying minerals.\n\n"
                "Every room features a natural hot spring bath.")

    if any(w in msg for w in ["access", "shuttle", "train", "bus", "taxi", "how to get", "direction", "tokyo"]):
        return ("Access information:\n\n"
                "Keikoku: 7 min by bus from nearest station. Shuttle available.\n"
                "Kogen: 30 min by bus. Limousine service available.\n"
                "Heritage Honten: 30 min by bus. Free shuttle (reservation required).\n"
                "Hotel Modern Suifu: 6 min walk from station.\n"
                "Saryo: Bus or taxi from station.\n\n"
                "Airport hire car service available (book 3 days ahead).")

    if any(w in msg for w in ["child", "kid", "family", "baby"]):
        return ("For families with children, we recommend Heritage Honten.\n\n"
                "It's our only property welcoming children:\n"
                "- Elementary school: 50% of adult rate\n"
                "- Toddler: ¥5,000\n"
                "- Infant: Free\n\n"
                "All-inclusive — no additional charges to worry about.\n"
                "Other properties require guests to be 12+ (Modern Suifu: 13+).")

    if any(w in msg for w in ["annivers", "birthday", "special", "celebrat", "propose"]):
        return ("For a special occasion, we recommend Suifu Kogen.\n\n"
                "All 9 rooms are detached private villas.\n"
                "MIKADO suite (136m2): Ise lobster kaiseki with early check-in at 14:00.\n"
                "HIME suite (131m2): Open-air + indoor bath in a luxurious space.\n\n"
                "Featured in an international luxury travel magazine.\n"
                "From ¥99,000/room with meals.")

    if any(w in msg for w in ["compare", "difference", "recommend", "which", "best"]):
        return ("Property overview:\n\n"
                "Keikoku: Gorge setting. 21 rooms. Adults only.\n"
                "Kogen: Highland. 9 detached villas. Ultimate privacy. Adults only.\n"
                "Heritage Honten: Founded 1662. Miraculous spring. Children welcome.\n"
                "Hotel Modern Suifu: Near station. CI 17:00/CO 13:00. Budget-friendly.\n"
                "Saryo: Day-trip available. Casual. From ¥28,050.\n\n"
                "Tell me your group size, purpose, and budget for a recommendation.")

    if any(w in msg for w in ["hello", "hi ", "hey", "good morning", "good evening"]):
        return ("Welcome to Suifu Resorts. I'm your personal concierge.\n\n"
                "I can help with availability, dining, property comparisons, "
                "hot springs, and more. How may I assist you?")

    return ("Welcome to Suifu Resorts Concierge.\n\n"
            "I can help with:\n"
            "- Availability & reservations\n"
            "- Room rates & pricing\n"
            "- Cuisine & dining\n"
            "- Hot springs & onsen\n"
            "- Access & transportation\n"
            "- Family-friendly options\n\n"
            "How may I assist you?\n\n"
            "* This chatbot is a demo. The production version uses AI integrated with "
            "property knowledge and real-time availability APIs.")


# ===== API Endpoints =====
@app.post("/api/chat")
async def api_chat(request: Request):
    """キーワードマッチによる定型文チャット"""
    body = await request.json()
    message = body.get("message", "")
    lang = body.get("lang", "ja")

    reply = build_response(message, lang)

    return {
        "reply": reply,
        "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        "demo": True,
    }


# ===== Health Check =====
@app.get("/health")
async def health():
    return {"status": "ok", "facilities": len(KNOWLEDGE.get("facilities", {})), "mode": "keyword-match"}


# ===== Static Files =====
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
else:
    @app.get("/")
    async def root():
        return HTMLResponse("<h1>Ryokan AI Concierge Demo</h1><p>Static files not found.</p>")
