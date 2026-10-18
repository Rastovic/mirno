# Mirno feed

Besplatni pipeline koji generiše `feed.json` (kartice upozorenja) iz **javnih**
izvora prijetnji — bez AI, bez prijave, bez skrejpovanja platformi.

## Izvori
- [abuse.ch URLhaus](https://urlhaus.abuse.ch) — malver URL-ovi
- [OpenPhish](https://openphish.com) — aktivni phishing (community feed = **nekomercijalno**; za komercijalnu upotrebu treba licenca ili zamjena)
- [crt.sh](https://crt.sh) — CT logovi (dvojnici crnogorskih brendova)

## Kako radi
GitHub Actions (`.github/workflows/feed.yml`) pokreće `build_feed.py` svakih ~30 min
**u svom sandboxu** (neprijateljski podaci se ne diraju na ličnom računaru) i
commit-uje `feed.json` ako ima promjena.

Aplikacija čita feed sa:
```
https://raw.githubusercontent.com/Rastovic/mirno/main/feed.json
```

## Sigurnost
- Svi URL-ovi su **defang-ovani** (`hxxp[://]`, `[.]`) — neklikabilni.
- Nema kredencijala u repo-u (izvori ne traže ključeve).
- Kartice su agregat po sferi (jedna po kategoriji + primjer), ne sirova lista.

## Ručno
```
python3 -I build_feed.py   # napravi feed.json lokalno
```
