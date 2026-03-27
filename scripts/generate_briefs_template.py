#!/usr/bin/env python3
"""
generate_briefs_template.py - 地域特性テンプレートからブリーフを生成

各都道府県の産業特性と、各業界のキーワードを組み合わせて
local_context と challenge_summary を自動生成する。
"""

import json
import yaml
from pathlib import Path

PROJECT_ROOT = Path("/home/sol/ai-blog-system")
DATA_DIR = PROJECT_ROOT / "_data" / "pseo"
BRIEFS_FILE = DATA_DIR / "briefs.json"

# 都道府県の産業特性（Priority 2, 3）
PREF_CONTEXT = {
    # Priority 2
    "miyagi": {"desc": "宮城県は東北最大の経済都市・仙台を擁し、震災復興を経て産業基盤の再構築が進む地域", "feature": "仙台市を中心とした", "strength": "東北の経済・商業の中心地"},
    "hiroshima": {"desc": "広島県はマツダ・造船業を核とする製造業の集積地であり、瀬戸内海に面した物流の要衝", "feature": "自動車・造船を核とした", "strength": "中国地方最大の工業都市"},
    "niigata": {"desc": "新潟県は米どころとして知られ、燕三条の金属加工産業や長岡の工作機械産業も全国有数の規模", "feature": "燕三条の金属加工や農業を基盤とした", "strength": "伝統的なものづくりと農業の両立"},
    "shizuoka": {"desc": "静岡県はヤマハ・スズキなど輸送機器産業と、茶・みかんの農業が共存する産業多角型の県", "feature": "輸送機器と食品加工が共存する", "strength": "浜松・静岡の二大都市圏"},
    "ibaraki": {"desc": "茨城県はつくば研究学園都市を擁する科学技術の拠点であり、農業産出額も全国トップクラス", "feature": "つくば研究都市と農業が共存する", "strength": "科学技術と第一次産業の融合"},
    "nagano": {"desc": "長野県は精密機器産業の「東洋のスイス」として知られ、諏訪地域にセイコーエプソン等が集積", "feature": "精密機器産業と観光業を柱とした", "strength": "諏訪地域の精密機器クラスター"},
    "gifu": {"desc": "岐阜県は関市の刃物産業・美濃焼・各務原の航空機産業など特色ある製造業が点在する地域", "feature": "刃物・陶磁器・航空機など特色ある産業が集まる", "strength": "伝統産業と先端産業の共存"},
    "gunma": {"desc": "群馬県はSUBARU（太田市）を中心に自動車関連産業が集積し、食品加工業も盛んな内陸工業県", "feature": "自動車産業と食品加工を軸とした", "strength": "北関東の製造業拠点"},
    "tochigi": {"desc": "栃木県は宇都宮を中心にホンダ・キヤノン等の工場が立地し、いちご・乳製品の農業も盛んな地域", "feature": "大手メーカー工場と農業が共存する", "strength": "北関東有数の工業集積"},
    "okayama": {"desc": "岡山県は水島コンビナートの石油化学・鉄鋼と、児島のデニム・学生服産業が特徴的な県", "feature": "石油化学コンビナートと繊維産業を持つ", "strength": "水島工業地帯の重化学工業"},
    "mie": {"desc": "三重県は四日市コンビナートの石油化学と、伊勢志摩の観光・真珠養殖業が共存する地域", "feature": "石油化学と観光・水産業が併存する", "strength": "四日市の化学産業クラスター"},
    "kumamoto": {"desc": "熊本県はTSMC進出で半導体産業が急拡大中であり、農業産出額も全国有数の「農業と半導体の県」", "feature": "TSMC進出で半導体産業が急成長する", "strength": "半導体と農業の新しい産業構造"},
    "kagoshima": {"desc": "鹿児島県は畜産・農業を基盤に食品加工業が発達し、桜島を擁する観光県でもある", "feature": "畜産・食品加工と観光業を軸とした", "strength": "九州南端の農畜産業の拠点"},
    "okinawa": {"desc": "沖縄県は観光業が基幹産業であり、IT特区によるコールセンター・ソフトウェア開発の集積も進む", "feature": "観光業とIT特区が経済を牽引する", "strength": "アジアに最も近い日本の玄関口"},
    "nara": {"desc": "奈良県は伝統工芸（奈良筆・墨）と、大阪のベッドタウンとしての住宅産業が混在する地域", "feature": "伝統工芸と住宅産業が混在する", "strength": "歴史文化資産と近畿圏のベッドタウン"},
    # Priority 3
    "iwate": {"desc": "岩手県は広大な面積に農林水産業が分散し、北上市周辺に半導体・自動車部品の工場が集積", "feature": "農林水産業と北上の製造業が共存する", "strength": "北上川流域の工業集積"},
    "akita": {"desc": "秋田県は稲作を中心とした農業県であり、人口減少が全国で最も進む中、産業構造の転換が急務", "feature": "農業を基盤に産業転換を進める", "strength": "洋上風力発電のポテンシャル"},
    "yamagata": {"desc": "山形県はさくらんぼ等の果樹栽培と、米沢の有機EL・山形市の鋳物産業が特徴的な地域", "feature": "果樹農業と先端技術産業が共存する", "strength": "有機ELなど先端材料産業"},
    "fukushima": {"desc": "福島県は震災・原発事故からの復興途上にあり、ロボット・再エネ分野で「福島イノベーション・コースト構想」を推進", "feature": "復興とイノベーション創出を同時に進める", "strength": "ロボット・ドローン実証フィールド"},
    "aomori": {"desc": "青森県はりんご・にんにく等の農業と、八戸の水産加工業が主力の第一次産業中心の県", "feature": "りんご・水産加工を中心とした", "strength": "第一次産業のブランド力"},
    "toyama": {"desc": "富山県は「薬の富山」として医薬品産業が発達し、YKK等のアルミ加工産業も有力な製造業県", "feature": "医薬品とアルミ加工産業が集積する", "strength": "配置薬の伝統から発展した医薬品産業"},
    "ishikawa": {"desc": "石川県は金沢の伝統工芸（九谷焼・加賀友禅）と、コマツの建設機械産業が共存する地域", "feature": "伝統工芸と建設機械産業が共存する", "strength": "金沢の工芸文化と粟津のコマツ"},
    "fukui": {"desc": "福井県は鯖江市の眼鏡フレーム（世界シェア20%）と繊維産業で知られる専門産業の集積地", "feature": "眼鏡・繊維など専門産業が集積する", "strength": "鯖江の眼鏡産業は世界的ブランド"},
    "yamanashi": {"desc": "山梨県はジュエリー（甲府）・ワイン（勝沼）の地場産業と、富士山麓のファナック等ロボット産業が特徴", "feature": "宝飾・ワインとロボット産業が混在する", "strength": "ファナック本社を擁するロボット産業"},
    "shiga": {"desc": "滋賀県は琵琶湖の環境保全と製造業の両立を図る県であり、日本電気硝子等の素材メーカーが立地", "feature": "環境配慮型の製造業が集積する", "strength": "琵琶湖を守りつつ工業県として成長"},
    "wakayama": {"desc": "和歌山県はみかん・梅の農業と、和歌山市の石油化学・鉄鋼が両輪の産業構造", "feature": "農業と重化学工業が両輪の", "strength": "紀北の工業と紀南の農林水産業"},
    "tottori": {"desc": "鳥取県は人口最少県ながら、スイカ・らっきょう等の農業と、境港の水産業が主力産業", "feature": "農業・水産業を基盤とした", "strength": "小規模ながら特色ある一次産業"},
    "shimane": {"desc": "島根県は出雲大社の観光と、安来のたたら製鉄の伝統を受け継ぐ特殊鋼産業が特徴的な地域", "feature": "観光と特殊鋼産業を持つ", "strength": "日立金属安来工場の特殊鋼技術"},
    "yamaguchi": {"desc": "山口県は周南・下関の化学コンビナートと、下関のふぐ加工など水産業が主力の県", "feature": "化学工業と水産加工業を柱とした", "strength": "瀬戸内海側の重化学工業地帯"},
    "tokushima": {"desc": "徳島県は大塚製薬・日亜化学など世界的企業の本社があり、LED・医薬品で存在感を持つ県", "feature": "LED・医薬品の世界的企業を擁する", "strength": "日亜化学のLED・大塚グループの医薬品"},
    "kagawa": {"desc": "香川県はうどん県として知られ、造船・手袋製造など独自の産業と、瀬戸大橋を活かした物流拠点", "feature": "造船・手袋など独自産業と物流拠点を持つ", "strength": "四国の玄関口としての物流機能"},
    "ehime": {"desc": "愛媛県は今治タオル・造船・みかんの三大産業で知られ、四国最大の工業県でもある", "feature": "タオル・造船・柑橘を三本柱とする", "strength": "今治タオルと来島海峡の造船業"},
    "kochi": {"desc": "高知県は園芸農業（ピーマン・なす）と、鰹のたたきに代表される水産業が主力の県", "feature": "園芸農業と水産業を基盤とした", "strength": "施設園芸技術は全国トップクラス"},
    "saga": {"desc": "佐賀県は有田焼の伝統と、鳥栖市の物流拠点化、海苔養殖日本一など多面的な産業を持つ県", "feature": "陶磁器・物流・水産養殖が共存する", "strength": "鳥栖の九州物流クロスポイント"},
    "nagasaki": {"desc": "長崎県は造船・水産加工を基盤に、ハウステンボスなど観光業も重要な産業である県", "feature": "造船・水産加工と観光業を主力とした", "strength": "三菱重工長崎造船所の伝統"},
    "oita": {"desc": "大分県は新日鐵住金大分・昭和電工など素材産業の集積地であり、温泉観光と地熱発電も特徴的", "feature": "素材産業と温泉観光・地熱エネルギーを持つ", "strength": "大分コンビナートの石油化学"},
    "miyazaki": {"desc": "宮崎県は畜産（宮崎牛・地鶏）と農業が主力で、IT企業の誘致にも力を入れている南九州の県", "feature": "畜産・農業を基盤にIT誘致を進める", "strength": "宮崎牛など畜産ブランド力"},
}

# 業界別のテンプレート文
INDUSTRY_TEMPLATES = {
    "manufacturing": {
        "local": "{pref_desc}です。{pref_feature}製造業は{pref_strength}を活かし、地域の産業基盤を支えています。",
        "challenge": "{pref_name}の製造業では、AI外観検査による品質管理の自動化と、予知保全による設備稼働率の向上が、人手不足への有効な対策となります。"
    },
    "construction": {
        "local": "{pref_desc}です。建設業はインフラ整備・維持管理を中心に、{pref_strength}に関連した建設需要が続いています。",
        "challenge": "{pref_name}の建設業では、AI施工管理による工期短縮と、ドローン×AI測量の導入が、限られた技術者での品質確保を可能にします。"
    },
    "service": {
        "local": "{pref_desc}です。サービス業は{pref_strength}と連動し、地域経済を支える重要な産業セクターです。",
        "challenge": "{pref_name}のサービス業では、AIチャットボットによる顧客対応の効率化と、需要予測に基づくシフト最適化が人手不足対策に即効性があります。"
    },
    "it_software": {
        "local": "{pref_desc}です。IT産業は{pref_feature}地域特性を活かしたソリューション開発や、リモートワーク拠点としての役割を担っています。",
        "challenge": "{pref_name}のIT企業では、AIコーディングアシスタントの導入による開発生産性の向上と、テスト自動化による品質担保が競争力強化の鍵です。"
    },
    "retail": {
        "local": "{pref_desc}です。小売業は{pref_strength}を背景に、地域住民と観光客の双方にサービスを提供しています。",
        "challenge": "{pref_name}の小売業では、AI需要予測による在庫最適化と、顧客データ分析に基づくパーソナライズド販促が売上向上と廃棄削減に有効です。"
    },
    "healthcare": {
        "local": "{pref_desc}です。医療機関は{pref_strength}を背景とした地域医療体制の維持・強化が課題となっています。",
        "challenge": "{pref_name}の医療機関では、AI画像診断支援による読影効率の向上と、電子カルテ自動要約による事務負荷軽減が医師の働き方改革に直結します。"
    },
    "food_restaurant": {
        "local": "{pref_desc}です。食品・飲食業は{pref_strength}を活かした地場食材の加工・提供が盛んです。",
        "challenge": "{pref_name}の食品業では、AI品質検査による食品安全の強化と、需要予測によるフードロス削減が品質向上とコスト削減を同時に実現します。"
    },
    "printing_advertising": {
        "local": "{pref_desc}です。印刷・広告業は{pref_feature}地域企業の販促物制作やブランディング支援を担っています。",
        "challenge": "{pref_name}の印刷・広告業では、画像生成AIによるデザイン効率化と、AIコピーライティングの活用が短納期・低コストへの対応力を高めます。"
    },
    "real_estate": {
        "local": "{pref_desc}です。不動産市場は{pref_strength}を背景とした住宅・産業用地の需給バランスが特徴的です。",
        "challenge": "{pref_name}の不動産業では、AI価格査定による適正価格の算出と、物件レコメンドによる成約率向上が営業効率の改善に直結します。"
    },
    "education": {
        "local": "{pref_desc}です。教育機関は{pref_strength}を背景に、地域人材の育成と教員の働き方改革の両立が求められています。",
        "challenge": "{pref_name}の教育機関では、AIアダプティブラーニングによる個別最適化学習と、採点自動化による教員負荷軽減が教育の質向上に貢献します。"
    },
    "automotive": {
        "local": "{pref_desc}です。自動車関連産業は{pref_feature}サプライチェーンの中で部品供給や整備・販売を担う企業が活動しています。",
        "challenge": "{pref_name}の自動車関連企業では、AIによる品質検査の自動化と、サプライチェーンの需給予測が生産効率と品質の向上に有効です。"
    },
    "logistics": {
        "local": "{pref_desc}です。物流業は{pref_strength}を活かした配送ネットワークの構築と効率化が課題となっています。",
        "challenge": "{pref_name}の物流業では、AIルート最適化によるドライバー不足への対応と、倉庫管理の自動化が配送効率とコスト削減を同時に改善します。"
    },
    "energy": {
        "local": "{pref_desc}です。エネルギー分野は{pref_strength}を背景に、再生可能エネルギーの導入と安定供給の両立が課題です。",
        "challenge": "{pref_name}のエネルギー事業では、AI電力需要予測による効率的な供給計画と、設備の予知保全が安定供給とコスト最適化に貢献します。"
    },
}


def main():
    with open(DATA_DIR / "industries.yml", encoding="utf-8") as f:
        industries = yaml.safe_load(f)
    with open(DATA_DIR / "prefectures.yml", encoding="utf-8") as f:
        prefectures = yaml.safe_load(f)

    # Load existing briefs
    with open(BRIEFS_FILE, encoding="utf-8") as f:
        briefs = json.load(f)

    added = 0
    for ind in industries:
        ind_id = ind["id"]
        templates = INDUSTRY_TEMPLATES.get(ind_id, INDUSTRY_TEMPLATES["manufacturing"])

        for pref in prefectures:
            pref_id = pref["id"]
            key = f"{ind_id}/{pref_id}"

            # Skip if already has a brief
            if key in briefs:
                continue

            ctx = PREF_CONTEXT.get(pref_id)
            if not ctx:
                continue

            local_context = templates["local"].format(
                pref_name=pref["name"],
                pref_desc=ctx["desc"],
                pref_feature=ctx["feature"],
                pref_strength=ctx["strength"],
            )
            challenge_summary = templates["challenge"].format(
                pref_name=pref["name"],
            )

            # Trim to limits
            briefs[key] = {
                "local_context": local_context[:200],
                "challenge_summary": challenge_summary[:150],
            }
            added += 1

    with open(BRIEFS_FILE, "w", encoding="utf-8") as f:
        json.dump(briefs, f, ensure_ascii=False, indent=2)

    print(f"追加: {added}件, 合計: {len(briefs)}件")


if __name__ == "__main__":
    main()
