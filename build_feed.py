#!/usr/bin/env python3
"""
Mirno — generator feeda (feed.json) iz JAVNIH izvora prijetnji.
Bez AI, bez prijave, bez skrejpovanja platformi. Samo javni feedovi:
  - abuse.ch URLhaus (malver URL-ovi)
  - OpenPhish (aktivni phishing linkovi; community = nekomercijalno!)
  - crt.sh (CT logovi) za crnogorske brend-dvojnike

Pravi kartice po kategoriji (agregat: jedna kartica po sferi + primjer),
sve URL-ove DEFANG-uje (neklikabilno). Izlaz: feed.json u formatu aplikacije.

Pokretanje:  python3 -I build_feed.py
Radi i u GitHub Actions (stdlib only).
"""
import sys, csv, json, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

UA = {"User-Agent": "mirno-feed/0.1 (+https://github.com/Rastovic)"}
URLHAUS = "https://urlhaus.abuse.ch/downloads/csv_recent/"
OPENPHISH = "https://openphish.com/feed.txt"

# Sfera -> ključne riječi u URL-u
THEMES = {
    "djeca": ["roblox", "fortnite", "minecraft", "discord", "tiktok",
              "snapchat", "steam", "epicgames", "xbox", "playstation"],
    "banka": ["bank", "paypal", "visa", "mastercard", "secure", "revolut",
              "wise", "card", "payment"],
    "dostava": ["dhl", "dpd", "fedex", "ups", "posta", "parcel", "customs",
                "carina", "dostava", "delivery", "post-"],
    "kripto": ["crypto", "coin", "binance", "metamask", "wallet", "bitcoin",
               "btc", "ledger", "trust", "eth"],
}
EXE = (".apk", ".exe", ".ps1", ".sh", ".scr", ".bat", ".jar", ".dll")

# Crnogorski brendovi (CT provjera dvojnika)
MNE_BRANDS = {
    "Pošta CG": ["posta", "postacg"], "CKB": ["ckb"], "NLB": ["nlb"],
    "Erste": ["erste"], "Hipotekarna": ["hipotekarna"],
    "Crnogorski Telekom": ["telekom", "mtel"], "gov.me": ["euprava", "gov-me"],
}
MNE_LEGIT = (".posta.co.me", ".ckb.me", ".nlb.me", ".erstebank.me",
             ".hipotekarnabanka.com", ".telekom.me", ".mtel.me", ".gov.me",
             ".euprava.me", ".vercel.app", ".coder.")

# Naslovi/tekst po sferi (ljudski napisano, bez AI)
TITLES = {
    "djeca": ("Lažni linkovi ciljaju gejmere i djecu",
              "Kruže lažni „pokloni/free“ linkovi (Roblox, Discord...) koji kradu nalog. Reci djetetu da ne klikće."),
    "banka": ("Novi phishing za banke i plaćanje",
              "Lažne „login/secure“ stranice kradu podatke kartice i naloga. Ne unosi ništa preko linka iz poruke."),
    "dostava": ("Lažna obavještenja o paketu i carini",
                "Poruke „platite carinu/dostavu“ vode na lažne stranice. Prava pošta ne traži plaćanje preko linka."),
    "kripto": ("Lažni kripto alati i novčanici",
               "Kruže lažni „recovery/wallet“ alati koji kradu novčanik. Nema legalnog alata za „povrat“ kripta."),
}


def get(url, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def defang(u):
    return (u.replace("https://", "hxxps://").replace("http://", "hxxp://")
             .replace("://", "[://]").replace(".", "[.]"))


def theme_of(u):
    u = u.lower()
    for name, kws in THEMES.items():
        if any(k in u for k in kws):
            return name
    return None


def collect_urls():
    """Vrati listu (url, is_exec) iz URLhaus + OpenPhish."""
    out = []
    try:
        for ln in get(URLHAUS).splitlines():
            if ln.startswith("#") or not ln:
                continue
            row = next(csv.reader([ln]), None)
            if row and len(row) > 2:
                out.append(row[2])
    except Exception as e:
        print("URLhaus greška:", e, file=sys.stderr)
    try:
        for ln in get(OPENPHISH).splitlines():
            if ln.strip().startswith("http"):
                out.append(ln.strip())
    except Exception as e:
        print("OpenPhish greška:", e, file=sys.stderr)
    return out


def world_cards(urls):
    """Jedna kartica po sferi (agregat) + broj + jedan primjer."""
    buckets = {k: [] for k in THEMES}
    for u in urls:
        t = theme_of(u)
        if t:
            buckets[t].append(u)
    now = datetime.now(timezone.utc)
    cards = []
    for cat, hits in buckets.items():
        if not hits:
            continue
        exec_hit = next((h for h in hits if h.lower().endswith(EXE)), None)
        example = exec_hit or hits[0]
        sev = "visok" if exec_hit else "srednji"
        title, body = TITLES[cat]
        cards.append({
            "id": f"world-{cat}-{now:%Y%m%d}",
            "title": title,
            "body": body + f" (viđeno danas: {len(hits)})",
            "category": cat,
            "severity": sev,
            "region": "world",
            "time": now.isoformat(),
            "url": defang(example),
        })
    return cards


def mne_cards():
    """CT provjera: novi domeni koji liče na crnogorske brendove."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=2)
    cards, seen = [], set()
    for brand, kws in MNE_BRANDS.items():
        found = None
        for kw in kws:
            try:
                url = "https://crt.sh/?q=" + urllib.parse.quote("%" + kw + "%") + "&output=json"
                rows = json.loads(get(url))
            except Exception:
                continue
            for row in rows:
                nb = row.get("not_before", "")
                try:
                    ts = datetime.fromisoformat(nb).replace(tzinfo=timezone.utc)
                except Exception:
                    continue
                if ts < cutoff:
                    continue
                for dom in set((row.get("name_value") or "").splitlines()):
                    dom = dom.lower().strip().lstrip("*.")
                    if not dom or dom in seen:
                        continue
                    if any(dom.endswith(g) or g in dom for g in MNE_LEGIT):
                        continue
                    seen.add(dom)
                    found = dom
                    break
            if found:
                break
        if found:
            cards.append({
                "id": f"me-{brand.lower().replace(' ', '')}-{now:%Y%m%d}",
                "title": f"Moguć lažni domen: {brand}",
                "body": "Nov domen liči na pravi. Provjeri prije nego uneseš podatke; koristi zvanični sajt/aplikaciju.",
                "category": "banka" if brand not in ("Pošta CG", "gov.me") else "dostava",
                "severity": "srednji",
                "region": "ME",
                "time": now.isoformat(),
                "url": defang(found),
            })
    return cards


def main():
    urls = collect_urls()
    cards = world_cards(urls)
    try:
        cards += mne_cards()
    except Exception as e:
        print("CT greška:", e, file=sys.stderr)
    # sortiraj: visok prvo, pa ME ispred world
    rank = {"visok": 0, "srednji": 1, "nizak": 2}
    cards.sort(key=lambda c: (rank.get(c["severity"], 3), c["region"] != "ME"))
    feed = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": "abuse.ch URLhaus, OpenPhish, crt.sh (javni feedovi)",
        "count": len(cards),
        "cards": cards,
    }
    with open("feed.json", "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=2)
    print(f"feed.json: {len(cards)} kartica")


if __name__ == "__main__":
    main()
