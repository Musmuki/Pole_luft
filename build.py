"""Builds site/: one page per city with pollen (DWD) and air quality (UBA), plus an index and sitemap.

Only official public data, no personal data, no tracking, stdlib only.
  python build.py                      -> site/
  SITE_URL=https://example.org python build.py   (absolute URLs in sitemap/canonical)
Inputs: data/cities.json (cities with UBA stations), data/regions.json (city -> DWD part region, optional).
Pollen is shown only for cities whose DWD region is marked sure; nothing is guessed.
"""
import html
import json
import os
import re
import shutil
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Berlin")
UA = {"User-Agent": "pollen-luft-site/0.2"}
ROOT = Path(__file__).parent
OUT = ROOT / "site"
# GitHub Pages passes SITE_URL; Cloudflare Pages provides CF_PAGES_URL at build time.
# Explicit SITE_URL wins when switching to a custom domain.
SITE_URL = (os.environ.get("SITE_URL") or os.environ.get("CF_PAGES_URL") or "").rstrip("/")
SITE_NAME = "Pollen & Luft heute"
BASE = os.environ.get("BASE_PATH", "").rstrip("/")   # e.g. /Pole_luft on GitHub Pages

POLLEN = [("Hasel", "Hasel"), ("Erle", "Erle"), ("Esche", "Esche"), ("Birke", "Birke"),
          ("Graeser", "Gräser"), ("Roggen", "Roggen"), ("Beifuss", "Beifuß"), ("Ambrosia", "Ambrosia")]
POLLEN_LEVELS = {"0": ("keine", 0), "0-1": ("keine bis gering", 1), "1": ("gering", 2), "1-2": ("gering bis mittel", 3),
                 "2": ("mittel", 4), "2-3": ("mittel bis hoch", 5), "3": ("hoch", 6)}
AIR_COMPONENTS = {1: "Feinstaub PM₁₀", 9: "Feinstaub PM₂,₅", 5: "Stickstoffdioxid NO₂", 3: "Ozon O₃"}
AIR_INDEX = ["sehr gut", "gut", "mäßig", "schlecht", "sehr schlecht"]
WD = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def slugify(text):
    t = text.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def load_pollen():
    d = get_json("https://opendata.dwd.de/climate_environment/health/alerts/s31fg.json")
    parts = {}
    for c in d["content"]:
        rows = [(label, [c["Pollen"].get(key, {}).get(day) for day in ("today", "tomorrow", "dayafter_to")])
                for key, label in POLLEN]
        name = c["region_name"] + (f', {c["partregion_name"]}' if c["partregion_name"] else "")
        parts[(c["region_id"], c["partregion_id"])] = {"region": name, "rows": rows}
    return d.get("last_update"), parts


def load_air():
    now = datetime.now(TZ)
    url = ("https://luftdaten.umweltbundesamt.de/api/air-data/v3/airquality/json"
           f"?date_from={(now - timedelta(days=1)).date()}&date_to={now.date()}&time_from=1&time_to=24&lang=de")
    latest = {}
    for sid, hours in get_json(url).get("data", {}).items():
        if not hours:
            continue
        rec = hours[sorted(hours)[-1]]
        end = datetime.fromisoformat(rec[0]).replace(tzinfo=TZ)
        if now - end > timedelta(hours=6):   # stale: do not present as "jetzt"
            continue
        latest[int(sid)] = {"time": rec[0], "index": rec[1], "incomplete": bool(rec[2]),
                            "parts": [(AIR_COMPONENTS[c[0]], c[1], c[2]) for c in rec[3:] if c[0] in AIR_COMPONENTS]}
    return latest


def air_class(i):
    return AIR_INDEX[i] if isinstance(i, int) and 0 <= i < len(AIR_INDEX) else "keine Angabe"


def pollen_cell(value):
    if value not in POLLEN_LEVELS:
        return '<td class="na">keine Angabe</td>'
    text, step = POLLEN_LEVELS[value]
    return f'<td><span class="lvl p{step}">{html.escape(text)}</span></td>'


CSS = """:root{--bg:#fbfaf7;--fg:#1f2421;--muted:#5d6661;--card:#fff;--line:#e3e0d8;
--p0:#e9efe9;--p1:#dcebd3;--p2:#f3e9b5;--p3:#f6d78f;--p4:#f2b872;--p5:#e8925a;--p6:#d4664a;
--a0:#cde9d6;--a1:#dcebc4;--a2:#f3e3a6;--a3:#f0b483;--a4:#e08a8a}
@media (prefers-color-scheme:dark){:root{--bg:#151816;--fg:#e8ebe7;--muted:#9aa39d;--card:#1d211f;--line:#2e3430;
--p0:#28302a;--p1:#2f4130;--p2:#4d4627;--p3:#5a4a24;--p4:#663f22;--p5:#6e3420;--p6:#7a2b20;
--a0:#244232;--a1:#344428;--a2:#4f4524;--a3:#5d3a22;--a4:#5e2a2a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:760px;margin:0 auto;padding:24px 16px 48px}h1{font-size:1.6rem;margin:0 0 4px}
h2{font-size:1.15rem;margin:0 0 12px}.sub{color:var(--muted);margin:0 0 24px}
section{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:16px}
table{width:100%;border-collapse:collapse}th,td{padding:6px 4px;text-align:left;border-top:1px solid var(--line);vertical-align:middle}
thead th{border-top:0;font-weight:600}small{color:var(--muted);font-weight:400}tbody th{font-weight:500}
.lvl{display:inline-block;padding:2px 8px;border-radius:999px;font-size:.85rem;white-space:nowrap}
.p0{background:var(--p0)}.p1{background:var(--p1)}.p2{background:var(--p2)}.p3{background:var(--p3)}.p4{background:var(--p4)}.p5{background:var(--p5)}.p6{background:var(--p6)}
.a0{background:var(--a0)}.a1{background:var(--a1)}.a2{background:var(--a2)}.a3{background:var(--a3)}.a4{background:var(--a4)}
.na{color:var(--muted);font-size:.85rem}.big .lvl{font-size:1.2rem;padding:4px 14px}.meta{color:var(--muted);font-size:.9rem}
.parts{list-style:none;padding:0;margin:0}.parts li{display:grid;grid-template-columns:1fr auto auto;gap:12px;padding:6px 0;border-top:1px solid var(--line);align-items:center}
.cities{columns:2 180px;padding:0;list-style:none;margin:0}.cities li{padding:2px 0}
footer{color:var(--muted);font-size:.85rem}a{color:inherit}nav{margin-bottom:16px;font-size:.9rem}
@media (max-width:480px){th,td{padding:6px 2px}.lvl{font-size:.75rem;padding:2px 6px;white-space:normal}}"""

FOOTER = """<footer><p>Quellen: <a href="https://opendata.dwd.de/climate_environment/health/alerts/">DWD Pollenflug-Gefahrenindex</a>,
<a href="https://www.umweltbundesamt.de/daten/luft/luftdaten">Umweltbundesamt Luftdaten</a>.
Keine medizinische Beratung. Diese Website verwendet selbst kein Besuchertracking und setzt keine Cookies. Beim Hosting können technisch erforderliche Verbindungsdaten verarbeitet werden.</p></footer>"""


def page(title, description, path, body):
    canonical = f'<link rel="canonical" href="{SITE_URL}{path}">' if SITE_URL else ""
    return (f'<!doctype html><html lang="de"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>'
            f'<meta name="description" content="{html.escape(description)}">{canonical}<style>{CSS}</style></head>'
            f'<body><main>{body}{FOOTER}</main></body></html>')


def city_page(city, pol, pollen_updated, air, now):
    name = city["name"]
    days = [now.date() + timedelta(days=i) for i in range(3)]
    body = [f'<nav><a href="{BASE}/">Alle Städte</a></nav><h1>{"Pollenflug und Luftqualität" if pol else "Luftqualität"} in {html.escape(name)}</h1>',
            f'<p class="sub">Amtliche Daten, automatisch aktualisiert. Stand: {now:%d.%m.%Y, %H:%M} Uhr.</p>']
    if pol:
        head = "".join(f"<th>{['Heute', 'Morgen', 'Übermorgen'][i]}<br><small>{WD[d.weekday()]} {d:%d.%m.}</small></th>"
                       for i, d in enumerate(days))
        rows = "".join(f'<tr><th scope="row">{html.escape(n)}</th>{"".join(pollen_cell(v) for v in vals)}</tr>'
                       for n, vals in pol["rows"])
        body.append(f'<section><h2>Pollenflug-Vorhersage</h2><table><thead><tr><th>Pollen</th>{head}</tr></thead>'
                    f'<tbody>{rows}</tbody></table><p class="meta">Deutscher Wetterdienst, Region {html.escape(pol["region"])}. '
                    f'Vorhersage vom {html.escape(str(pollen_updated))}. Die Stufen beschreiben die Pollenmenge in der Luft, '
                    f'nicht wie stark jemand reagiert.</p></section>')
    if air:
        st, a = air
        parts = "".join(f'<li><span>{html.escape(n)}</span><span>{v} µg/m³</span><span class="lvl a{i}">{air_class(i)}</span></li>'
                        for n, v, i in a["parts"])
        t = a["time"]
        body.append(f'<section><h2>Luftqualität jetzt</h2><p class="big"><span class="lvl a{a["index"]}">{air_class(a["index"])}</span></p>'
                    f'<p class="meta">Messstation {html.escape(st)}, Stunde bis {t[11:16]} Uhr am {t[8:10]}.{t[5:7]}.'
                    f'{" (noch nicht alle Werte gemeldet)" if a["incomplete"] else ""}</p><ul class="parts">{parts}</ul>'
                    f'<p class="meta">Umweltbundesamt, Luftqualitätsindex (fünf Stufen von „sehr gut“ bis „sehr schlecht“). '
                    f'Die Gesamtstufe richtet sich nach dem schlechtesten gemessenen Stoff.</p></section>')
    if pol:
        title = f"Pollenflug und Luftqualität heute in {name}"
        desc = f"Pollenflug-Vorhersage (DWD) und aktuelle Luftqualität (Umweltbundesamt) für {name}, automatisch aktualisiert."
    else:   # do not promise pollen where no region could be assigned
        title = f"Luftqualität heute in {name}"
        desc = f"Aktuelle Luftqualität in {name}: Messwerte des Umweltbundesamts, stündlich aktualisiert."
    return page(title, desc, f"/{city['slug']}/", "".join(body))


def main():
    now = datetime.now(TZ)
    cities = json.loads((ROOT / "data" / "cities.json").read_text(encoding="utf-8"))
    regions_file = ROOT / "data" / "regions.json"
    regions = json.loads(regions_file.read_text(encoding="utf-8")) if regions_file.exists() else {}
    pollen_updated, pollen_parts = load_pollen()
    air = load_air()

    names = {}
    for c in cities:
        names.setdefault(c["name"], []).append(c)
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()

    built, used = [], set()
    for c in cities:
        slug = slugify(c["name"] if len(names[c["name"]]) == 1 else f'{c["name"]}-{c["state"]}')
        n = 2
        while slug in used:   # e.g. "Rostock-Warnemünde" and "Rostock Warnemünde"
            slug, n = f"{slug.rsplit('-', 1)[0] if n > 2 else slug}-{n}", n + 1
        used.add(slug)
        c["slug"] = slug
        reg = regions.get(f'{c["state"]}|{c["name"]}')
        pol = pollen_parts.get((reg["region_id"], reg["partregion_id"])) if reg and reg.get("sure") else None
        st_air = next(((s["name"], air[s["id"]]) for s in c["stations"] if s["id"] in air), None)
        if not st_air:
            continue   # pollen alone is the same for a whole region: no near-duplicate pages
        (OUT / c["slug"]).mkdir()
        (OUT / c["slug"] / "index.html").write_text(city_page(c, pol, pollen_updated, st_air, now), encoding="utf-8")
        built.append(c)

    by_state = {}
    for c in built:
        by_state.setdefault(c["state_name"], []).append(c)
    lists = "".join(f'<section><h2>{html.escape(s)}</h2><ul class="cities">'
                    + "".join(f'<li><a href="{BASE}/{c["slug"]}/">{html.escape(c["name"])}</a></li>' for c in sorted(cs, key=lambda c: c["name"]))
                    + "</ul></section>" for s, cs in sorted(by_state.items()))
    index = (f'<h1>Pollenflug und Luftqualität heute</h1><p class="sub">Für {len(built)} Orte in Deutschland, aus den offenen Daten '
             f'des Deutschen Wetterdienstes und des Umweltbundesamts. Stand: {now:%d.%m.%Y, %H:%M} Uhr.</p>{lists}')
    (OUT / "index.html").write_text(page(SITE_NAME, "Pollenflug-Vorhersage und aktuelle Luftqualität für Orte in Deutschland, "
                                         "amtliche Daten, automatisch aktualisiert.", "/", index), encoding="utf-8")
    static = ROOT / "static"   # e.g. the Google Search Console verification file
    if static.exists():
        for f in static.iterdir():
            if f.is_file():
                shutil.copy(f, OUT / f.name)
    if SITE_URL:
        urls = [f"{SITE_URL}/"] + [f"{SITE_URL}/{c['slug']}/" for c in built]
        (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                                         + "".join(f"<url><loc>{u}</loc></url>" for u in urls) + "</urlset>", encoding="utf-8")
        (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8")
    with_pollen = sum(1 for c in built if regions.get(f'{c["state"]}|{c["name"]}', {}).get("sure"))
    print(f"ok: {len(built)} city pages ({with_pollen} with pollen), {len(air)} stations with current air data, pollen {pollen_updated}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
