"""체코어 정류장 이름을 한글로 옮깁니다 (교통정보 트램 노선의 괄호 속 한글 표기).

1) 잘 알려진 곳은 KNOWN 사전의 이름을 그대로 씁니다 (예: Pražský hrad -> 프라하성).
2) 광장·역 같은 일반 명사는 번역합니다 (예: Náměstí Míru -> 미루 광장).
3) 나머지는 국립국어원 체코어 표기법을 단순화한 발음 규칙으로 옮깁니다.
"""
import re
import unicodedata

KNOWN = {
    "Pražský hrad": "프라하성",
    "Národní divadlo": "국립극장",
    "Národní muzeum": "국립박물관",
    "Muzeum": "국립박물관",
    "Václavské náměstí": "바츨라프 광장",
    "Staroměstská": "구시가지 스타로메스트스카",
    "Malostranská": "말로스트란스카",
    "Malostranské náměstí": "말라스트라나 광장",
    "Hlavní nádraží": "중앙역",
    "Masarykovo nádraží": "마사리크 역",
    "Náměstí Republiky": "공화국 광장",
    "Náměstí Míru": "미루 광장",
    "Karlovo náměstí": "카를로보 광장",
    "Palackého náměstí": "팔라츠키 광장",
    "Jiráskovo náměstí": "이라스크 광장",
    "Národní třída": "나로드니 트르지다",
    "Pražské Jezulátko": "프라하의 아기 예수 성당",
    "Královský letohrádek": "왕실 여름 궁전",
    "Břevnovský klášter": "브르제브노프 수도원",
    "Strahovský klášter": "스트라호프 수도원",
    "Výstaviště": "비스타비슈테 전시장",
    "Pražská tržnice": "프라하 시장",
    "Vyšehrad": "비셰흐라드",
    "Karlovy lázně": "카를로비 라즈녜",
    "Letiště": "공항",
    "Můstek": "무스텍",
    "Hradčanská": "흐라드찬스카",
    "Dejvická": "데이비츠카",
    "Nemocnice Motol": "모톨 병원",
    "Černý Most": "체르니 모스트",
    "Háje": "하예",
    "Letňany": "레트냐니",
    "Zličín": "즐리친",
    "Depo Hostivař": "호스티바르시 차량기지",
    "Anděl": "안델",
    "Újezd": "우예즈드",
    "Florenc": "플로렌츠",
    "I. P. Pavlova": "이페 파블로바",
    "Lazarská": "라자르스카",
    "Vodičkova": "보디치코바",
    "Ústřední dílny DP": "교통공사 중앙 정비창",
    "Smíchovské nádraží": "스미호프 역",
    "Nádraží Holešovice": "홀레쇼비체 역",
    "Nádraží Libeň": "리벤 역",
    "Zoologická zahrada": "프라하 동물원",
    "Botanická zahrada Troja": "트로야 식물원",
    "Divoká Šárka": "디보카 샤르카",
    "Olšanské hřbitovy": "올샨스케 묘지",
    "Vozovna Kobylisy": "코빌리시 차량기지",
    "Vozovna Pankrác": "판크라츠 차량기지",
    "Vozovna Motol": "모톨 차량기지",
    "Vozovna Žižkov": "지슈코프 차량기지",
    "Vozovna Strašnice": "스트라슈니체 차량기지",
}

# Generic words: translated, and moved to the end when they lead the name ("Nádraží X" -> "X 역")
GENERIC = {
    "náměstí": "광장", "nádraží": "역", "sídliště": "단지", "vozovna": "차량기지", "depo": "차량기지",
    "most": "다리", "nábřeží": "강변", "hřbitov": "묘지", "hřbitovy": "묘지", "nemocnice": "병원",
    "poliklinika": "의원", "zahrada": "정원", "park": "공원", "letiště": "공항", "klášter": "수도원",
    "kostel": "성당", "škola": "학교", "sady": "공원", "smyčka": "회차장",
}

VOWELS = {"a": "ㅏ", "á": "ㅏ", "e": "ㅔ", "é": "ㅔ", "ě": "ㅔ", "i": "ㅣ", "í": "ㅣ", "y": "ㅣ", "ý": "ㅣ",
          "o": "ㅗ", "ó": "ㅗ", "u": "ㅜ", "ú": "ㅜ", "ů": "ㅜ"}
Y_VOWEL = {"ㅏ": "ㅑ", "ㅔ": "ㅖ", "ㅗ": "ㅛ", "ㅜ": "ㅠ", "ㅣ": "ㅣ"}
# consonant -> (initial jamo, standalone syllable when no vowel follows, palatal y-glide)
CONS = {
    "b": ("ㅂ", "브"), "c": ("ㅊ", "츠"), "č": ("ㅊ", "치"), "d": ("ㄷ", "드"), "ď": ("ㄷ", "디"),
    "f": ("ㅍ", "프"), "g": ("ㄱ", "그"), "h": ("ㅎ", "흐"), "ch": ("ㅎ", "흐"), "k": ("ㅋ", "크"),
    "l": ("ㄹ", "르"), "m": ("ㅁ", "므"), "n": ("ㄴ", "느"), "ň": ("ㄴ", "니"), "p": ("ㅍ", "프"),
    "q": ("ㅋ", "크"), "r": ("ㄹ", "르"), "s": ("ㅅ", "스"), "š": ("ㅅ", "슈"), "t": ("ㅌ", "트"),
    "ť": ("ㅌ", "티"), "v": ("ㅂ", "브"), "w": ("ㅂ", "브"), "z": ("ㅈ", "즈"), "ž": ("ㅈ", "주"),
}
PALATAL = {"ď", "ť", "ň", "š"}
FINAL_DEVOICE = {"b": "프", "d": "트", "g": "크", "v": "프", "z": "스", "ž": "시", "h": "흐"}
BATCHIM = {"m": "ㅁ", "n": "ㄴ", "ň": "ㄴ", "l": "ㄹ"}
VOICELESS = {"k", "p", "t", "s", "c", "č", "š", "ch", "f", "h"}

L_INI = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
L_MED = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
L_FIN = ["", "ㄱ", "ㄲ", "ㄳ", "ㄴ", "ㄵ", "ㄶ", "ㄷ", "ㄹ", "ㄺ", "ㄻ", "ㄼ", "ㄽ", "ㄾ", "ㄿ", "ㅀ", "ㅁ",
         "ㅂ", "ㅄ", "ㅅ", "ㅆ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"]


def _syl(ini, med, fin=""):
    return chr(0xAC00 + (L_INI.index(ini) * 21 + L_MED.index(med)) * 28 + L_FIN.index(fin))


def _add_batchim(syl, fin):
    code = ord(syl) - 0xAC00
    if not (0 <= code < 11172) or code % 28:
        return None
    return chr(ord(syl) + L_FIN.index(fin))


def _tokens(word):
    i, out = 0, []
    while i < len(word):
        if word[i:i + 2] == "ch":
            out.append("ch"); i += 2
        elif word[i:i + 2] in ("ou", "au", "eu"):
            out.append(word[i:i + 2]); i += 2
        else:
            out.append(word[i]); i += 1
    return out


def transliterate_word(word):
    """One Czech word (lowercase-insensitive) -> Hangul."""
    w = unicodedata.normalize("NFC", word.lower())
    w = re.sub(r"([a-zá-ž])\1", r"\1", w)  # Barrandov -> barandov
    toks = [t for t in _tokens(w) if t.isalpha()]
    out = []  # list of syllable strings
    i = 0
    while i < len(toks):
        t = toks[i]
        nxt = toks[i + 1] if i + 1 < len(toks) else None
        if t in VOWELS or t in ("ou", "au", "eu"):
            if t == "ou":
                out += ["오", "우"]
            elif t == "au":
                out += ["아", "우"]
            elif t == "eu":
                out += ["에", "우"]
            else:
                # l between vowels doubles: "Malá" -> 말라 (handled when l is read); here a bare vowel
                out.append(_syl("ㅇ", VOWELS[t]))
            i += 1
            continue
        if t == "j":
            if nxt in VOWELS:
                out.append(_syl("ㅇ", Y_VOWEL[VOWELS[nxt]])); i += 2
            elif nxt in ("ou", "au", "eu"):
                out += [_syl("ㅇ", Y_VOWEL[{"ou": "ㅗ", "au": "ㅏ", "eu": "ㅔ"}[nxt]]), "우"]; i += 2
            else:
                out.append("이"); i += 1
            continue
        if t == "ř":
            out.append("르")
            if nxt in VOWELS:
                out.append(_syl("ㅈ", VOWELS[nxt])); i += 2
            else:
                out.append("시" if nxt is None or nxt in VOICELESS else "주"); i += 1
            continue
        if t == "x":
            out.append("크")
            if nxt in VOWELS:
                out.append(_syl("ㅅ", VOWELS[nxt])); i += 2
            else:
                out.append("스"); i += 1
            continue
        if t not in CONS:
            i += 1
            continue
        ini, alone = CONS[t]
        if nxt in VOWELS:
            med = VOWELS[nxt]
            if t in PALATAL or (nxt == "ě" and t in ("ď", "ť", "ň")):
                med = Y_VOWEL[med] if t != "š" or med != "ㅣ" else med
            if t == "l" and out and out[-1] and _add_batchim(out[-1], "ㄹ"):
                out[-1] = _add_batchim(out[-1], "ㄹ")  # intervocalic l: 말라, 카를로
            out.append(_syl(ini, med))
            i += 2
            continue
        if nxt in ("ou", "au", "eu"):
            if t == "l" and out and _add_batchim(out[-1], "ㄹ"):
                out[-1] = _add_batchim(out[-1], "ㄹ")
            out.append(_syl(ini, {"ou": "ㅗ", "au": "ㅏ", "eu": "ㅔ"}[nxt]))
            out.append("우")
            i += 2
            continue
        # consonant without a following vowel
        if t in BATCHIM and out and _add_batchim(out[-1], BATCHIM[t]) and not (t == "l" and nxt is None and len(out) == 0):
            out[-1] = _add_batchim(out[-1], BATCHIM[t])
        elif t == "ž" and nxt in VOICELESS:
            out.append("슈")  # Žižkov -> 지슈코프
        elif nxt is None and t in FINAL_DEVOICE:
            out.append(FINAL_DEVOICE[t])
        else:
            out.append(alone)
        i += 1
    return "".join(out)


PREPOSITIONS = {"u": "우", "na": "나", "nad": "나드", "pod": "포드", "v": "브", "z": "즈", "k": "크", "ke": "케", "ve": "베"}


def to_korean(name):
    name = unicodedata.normalize("NFC", name.strip())
    if name in KNOWN:
        return KNOWN[name]
    if " - " in name:  # "Slavia - Nádraží Eden" -> each part on its own
        return " - ".join(to_korean(part) for part in name.split(" - "))
    words = re.split(r"\s+", name)
    lead_generic = None
    if len(words) > 1 and words[0].lower() in GENERIC:
        lead_generic = GENERIC[words.pop(0).lower()]
    parts = []
    for w in words:
        core = w.strip(",.()")
        if not core:
            continue
        if core.lower() in GENERIC:
            parts.append(GENERIC[core.lower()])
        elif core.lower() in PREPOSITIONS and len(parts) == 0 and len(words) > 1:
            parts.append(PREPOSITIONS[core.lower()])
        elif (core.isupper() and len(core) > 1) or any(ch.isdigit() for ch in core):
            parts.append(core)  # abbreviations / numbers stay as they are (DP, 1)
        elif "-" in core:
            parts.append("-".join(transliterate_word(p) for p in core.split("-") if p))
        else:
            parts.append(transliterate_word(core))
    if lead_generic:
        parts.append(lead_generic)
    return " ".join(p for p in parts if p)
