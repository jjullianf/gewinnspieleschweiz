#!/usr/bin/env python3
"""
generate_rabattcode_pages.py

Liest das oeffentliche Google-Sheet-CSV der Rabattcode-Sektion von
GewinnspielSchweiz und erzeugt fuer jede FIRMA eine eigene, indexierbare
Detailseite unter /rabattcode/ - auch wenn eine Firma mehrere Codes/Angebote
im Sheet hat, landen die alle gemeinsam auf einer Seite.

WICHTIG (Tracking-Schutz): Codes werden NIE direkt im HTML als Klartext
ausgegeben. Jeder Code wird erst per JavaScript sichtbar, nachdem die Person
auf "Code anzeigen" geklickt hat - der Klick oeffnet gleichzeitig den
Affiliate-Link in einem neuen Tab. So loest praktisch jede Code-Nutzung auch
den Tracking-Klick aus.

Verwendung (lokal):
    python3 generate_rabattcode_pages.py
"""

import csv
import io
import re
import unicodedata
import urllib.request
from collections import defaultdict
from datetime import datetime, date
from pathlib import Path

# Konfiguration
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6N_-IWV5yI4NoSVvHrKsTPqyr6cJ4nMRQj3d-zwIx2A0mI_EDbRXpHVBHjYDc8_N8n1ljz3Ychmy5/pub?gid=0&single=true&output=csv"
SITE_URL = "https://gewinnspieleschweiz.ch"
OUTPUT_DIR = Path("rabattcode")
SITEMAP_PATH = Path("sitemap.xml")
LOCAL_CSV_FALLBACK = Path("Rabattcodes_-_Sheet1.csv")


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    text = re.sub(r"-{2,}", "-", text)
    return text[:80].rstrip("-")


def parse_date(value: str):
    value = (value or "").strip()
    if not value or value.lower() in ("laufend", "unbegrenzt", "-"):
        return None
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except ValueError:
        return None


def fetch_rows():
    try:
        with urllib.request.urlopen(CSV_URL, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
    except Exception as e:
        if LOCAL_CSV_FALLBACK.exists():
            print(f"[warn] Konnte CSV nicht online laden ({e}), nutze lokale Datei.")
            raw = LOCAL_CSV_FALLBACK.read_text(encoding="utf-8")
        else:
            raise
    reader = csv.DictReader(io.StringIO(raw))
    return [row for row in reader if row.get("Firma", "").strip()]


def group_by_firma(rows):
    groups = defaultdict(list)
    for row in rows:
        firma = row["Firma"].strip()
        groups[firma].append(row)
    return groups


def truncate_at_word(text: str, max_len: int) -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text
    truncated = text[:max_len].rsplit(" ", 1)[0].rstrip(",.;: ")
    return truncated + "..."


def js_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("'", "\\'")


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title_tag}</title>
  <meta name="description" content="{meta_description}" />
  <link rel="canonical" href="{canonical_url}" />
  <meta property="og:title" content="{title_tag}" />
  <meta property="og:description" content="{meta_description}" />
  <meta property="og:url" content="{canonical_url}" />
  <meta property="og:type" content="article" />
  {og_image_tag}
  <meta name="robots" content="{robots_content}" />
  <link rel="icon" href="/favicon.png" type="image/png">

  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "{schema_headline}",
    "description": "{schema_description}",
    "datePublished": "{date_published}",
    "dateModified": "{last_checked_iso}",
    "author": {{ "@type": "Organization", "name": "GewinnspielSchweiz" }},
    "publisher": {{ "@type": "Organization", "name": "GewinnspielSchweiz", "url": "{site_url}" }},
    "url": "{canonical_url}"
  }}
  </script>

  <script async src="https://www.googletagmanager.com/gtag/js?id=G-RWWB1CDLR8"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'G-RWWB1CDLR8');
  </script>

  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">

  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{ --red: #D52B1E; --red-hover: #b82318; --red-light: #fff0ef; --border: #ebebeb; --text: #111; --text-muted: #666; }}
    html {{ scroll-behavior: smooth; }}
    body {{ font-family: 'Inter', sans-serif; background: #f9f9f9; color: var(--text); }}

    nav {{ position: sticky; top: 0; z-index: 200; background: rgba(255,255,255,0.97); border-bottom: 1px solid var(--border); }}
    .nav-inner {{ max-width: 1100px; margin: 0 auto; padding: 0 20px; height: 62px; display: flex; align-items: center; justify-content: space-between; gap: 16px; }}
    .nav-logo {{ display: flex; align-items: center; gap: 10px; text-decoration: none; flex-shrink: 0; }}
    .nav-logo img {{ height: 36px; width: 36px; border-radius: 8px; object-fit: cover; }}
    .nav-logo-text {{ font-size: 15px; font-weight: 800; color: var(--text); }}
    .nav-logo-text span {{ color: var(--red); }}
    .nav-links {{ display: flex; align-items: center; gap: 4px; list-style: none; }}
    .nav-links a {{ font-size: 14px; font-weight: 500; color: var(--text-muted); text-decoration: none; padding: 6px 10px; border-radius: 8px; }}
    .nav-links a:hover {{ background: var(--red-light); color: var(--red); }}
    .dropdown {{ position: relative; }}
    .dropdown-toggle {{ font-size: 14px; font-weight: 500; color: var(--text-muted); background: none; border: none; padding: 6px 10px; border-radius: 8px; cursor: pointer; font-family: "Inter", sans-serif; }}
    .dropdown-toggle:hover {{ background: var(--red-light); color: var(--red); }}
    .dropdown-menu {{ display: none; position: absolute; top: calc(100% + 8px); right: 0; background: #fff; border: 1px solid var(--border); border-radius: 12px; padding: 8px; min-width: 180px; box-shadow: 0 8px 24px rgba(0,0,0,0.1); z-index: 300; }}
    .dropdown:hover .dropdown-menu {{ display: block; }}
    .dropdown-menu a {{ display: block; font-size: 13px; font-weight: 500; color: var(--text-muted); padding: 8px 12px; border-radius: 8px; text-decoration: none; }}
    .dropdown-menu a:hover {{ background: var(--red-light); color: var(--red); }}
    .nav-cta {{ background: var(--red) !important; color: #fff !important; padding: 8px 14px !important; border-radius: 8px !important; font-weight: 600 !important; }}
    .nav-hamburger {{ display: none; background: none; border: none; cursor: pointer; padding: 6px; color: var(--text); }}
    .nav-hamburger svg {{ width: 22px; height: 22px; }}
    .nav-mobile-menu {{ display: none; position: fixed; inset: 0; background: #fff; z-index: 500; padding: 20px; overflow-y: auto; }}
    .nav-mobile-menu.open {{ display: block; }}
    .nav-mobile-header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 28px; }}
    .nav-mobile-close {{ background: none; border: none; cursor: pointer; font-size: 24px; color: var(--text-muted); }}
    .nav-mobile-links {{ display: flex; flex-direction: column; gap: 4px; }}
    .nav-mobile-links a {{ font-size: 17px; font-weight: 600; color: var(--text); text-decoration: none; padding: 14px 16px; border-radius: 12px; display: block; }}
    .nav-mobile-links a:hover {{ background: var(--red-light); color: var(--red); }}
    .nav-mobile-divider {{ height: 1px; background: var(--border); margin: 8px 0; }}
    .nav-mobile-section-label {{ font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-muted); padding: 8px 16px 4px; }}
    .nav-mobile-cta {{ background: var(--red) !important; color: #fff !important; text-align: center; margin-top: 12px; }}
    @media (max-width: 768px) {{
      .nav-links {{ display: none; }}
      .nav-hamburger {{ display: block; }}
      .nav-logo-text {{ display: none; }}
    }}

    .wrap {{ max-width: 720px; margin: 0 auto; padding: 0 24px 80px; }}
    .hero-img-wrap {{ width: 100%; max-height: 380px; overflow: hidden; }}
    .hero-img-wrap img {{ width: 100%; height: 380px; object-fit: cover; display: block; }}
    .inner {{ padding-top: 40px; }}

    .breadcrumb {{ font-size: 13px; color: var(--text-muted); margin-bottom: 24px; }}
    .breadcrumb a {{ color: var(--text-muted); text-decoration: none; }}
    .breadcrumb a:hover {{ color: var(--red); }}
    .breadcrumb span {{ margin: 0 6px; }}

    .badges {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 18px; }}
    .badge {{ font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; padding: 4px 10px; border-radius: 100px; }}
    .badge-cat {{ color: var(--red); background: var(--red-light); }}
    .badge-active {{ color: #086629; background: #efffef; }}
    .badge-expired {{ color: #999; background: #f0f0f0; }}

    h1 {{ font-size: clamp(24px, 4vw, 34px); font-weight: 800; letter-spacing: -0.02em; line-height: 1.2; margin-bottom: 8px; }}
    .company-sub {{ font-size: 15px; color: var(--text-muted); margin-bottom: 32px; }}

    .offer-card {{ background: #fff; border: 1.5px solid var(--border); border-radius: 16px; padding: 24px; margin-bottom: 18px; }}
    .offer-card.is-expired {{ opacity: 0.6; }}
    .offer-title {{ font-size: 18px; font-weight: 800; margin-bottom: 8px; }}
    .offer-desc {{ font-size: 14px; color: #333; line-height: 1.7; margin-bottom: 14px; }}
    .offer-meta {{ font-size: 12px; color: var(--text-muted); margin-bottom: 16px; }}
    .offer-meta strong {{ color: var(--text); }}

    .reveal-btn {{ display: inline-flex; align-items: center; gap: 8px; background: var(--red); color: #fff; border: none; padding: 13px 24px; border-radius: 10px; font-size: 15px; font-weight: 700; cursor: pointer; font-family: 'Inter', sans-serif; width: 100%; justify-content: center; }}
    .reveal-btn:hover {{ background: var(--red-hover); }}
    .revealed-code {{ display: flex; align-items: center; justify-content: space-between; gap: 10px; background: #f4fff6; border: 2px dashed #1a8a3d; border-radius: 10px; padding: 13px 18px; }}
    .revealed-code .code-text {{ font-family: 'Courier New', monospace; font-weight: 800; font-size: 17px; letter-spacing: 0.04em; color: #0a6b28; }}
    .revealed-code .copied-tag {{ font-size: 12px; font-weight: 700; color: #0a6b28; }}
    .expired-note {{ text-align: center; font-size: 13px; color: #999; font-weight: 600; padding: 13px; background: #f4f4f4; border-radius: 10px; }}

    h2 {{ font-size: 19px; font-weight: 800; margin: 36px 0 12px; }}
    p {{ font-size: 15px; line-height: 1.8; color: #333; margin-bottom: 16px; }}

    .divider {{ border: none; border-top: 1px solid var(--border); margin: 36px 0; }}
    .back-link {{ display: inline-flex; align-items: center; gap: 6px; color: var(--text-muted); text-decoration: none; font-size: 14px; font-weight: 500; margin-top: 8px; }}
    .back-link:hover {{ color: var(--red); }}
    .disclaimer-small {{ font-size: 12px; color: #bbb; margin-top: 24px; }}

    footer {{ border-top: 1px solid var(--border); margin-top: 60px; padding: 32px 24px; text-align: center; font-size: 13px; color: var(--text-muted); }}
    footer a {{ color: var(--text-muted); text-decoration: none; margin: 0 10px; }}
    footer a:hover {{ color: var(--red); }}
    .footer-disclaimer {{ font-size: 11px; color: #bbb; margin-top: 16px; line-height: 1.6; }}

    @media (max-width: 500px) {{ .hero-img-wrap img {{ height: 220px; }} }}
  </style>
</head>
<body>

<nav>
  <div class="nav-inner">
    <a class="nav-logo" href="/">
      <img src="/logo.png" alt="GewinnspielSchweiz Logo">
      <span class="nav-logo-text">Gewinnspiele<span>Schweiz</span></span>
    </a>
    <ul class="nav-links">
      <li><a href="/">Home</a></li>
      <li><a href="/#gewinnspiele">Gewinnspiele</a></li>
      <li><a href="/rabattcode.html">Rabattcodes</a></li>
      <li><a href="/blog.html">Blog</a></li>
      <li><a href="/kontakt.html">Fuer Unternehmen</a></li>
      <li class="dropdown">
        <button class="dropdown-toggle">Mehr &#9662;</button>
        <div class="dropdown-menu">
          <a href="/impressum.html">Impressum</a>
          <a href="/agb.html">AGB</a>
          <a href="/datenschutz.html">Datenschutz</a>
          <a href="https://instagram.com/gewinnspieleschweiz" target="_blank">Instagram</a>
        </div>
      </li>
      <li><a class="nav-cta" href="/newsletter.html">Newsletter</a></li>
    </ul>
    <button class="nav-hamburger" onclick="document.getElementById('mobileMenu').classList.add('open')" aria-label="Menu oeffnen">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
    </button>
  </div>
</nav>

<div class="nav-mobile-menu" id="mobileMenu">
  <div class="nav-mobile-header">
    <a class="nav-logo" href="/">
      <img src="/logo.png" alt="GewinnspielSchweiz Logo" style="height:36px;width:36px;border-radius:8px;">
    </a>
    <button class="nav-mobile-close" onclick="document.getElementById('mobileMenu').classList.remove('open')">X</button>
  </div>
  <div class="nav-mobile-links">
    <a href="/">Home</a>
    <a href="/#gewinnspiele">Gewinnspiele</a>
    <a href="/rabattcode.html">Rabattcodes</a>
    <div class="nav-mobile-divider"></div>
    <div class="nav-mobile-section-label">Mehr</div>
    <a href="/blog.html">Blog</a>
    <a href="/kontakt.html">Fuer Unternehmen</a>
    <a href="/impressum.html">Impressum</a>
    <a href="/agb.html">AGB</a>
    <a href="/datenschutz.html">Datenschutz</a>
    <a href="https://instagram.com/gewinnspieleschweiz" target="_blank">Instagram</a>
    <div class="nav-mobile-divider"></div>
    <a class="nav-mobile-cta" href="/newsletter.html">Newsletter</a>
  </div>
</div>

{hero_block}

<div class="wrap">
  <div class="inner">

    <div class="breadcrumb"><a href="/">Home</a><span>/</span><a href="/rabattcode.html">Rabattcodes</a><span>/</span>{firma}</div>

    <div class="badges">
      <span class="badge badge-cat">{category_display}</span>
      {status_badge}
    </div>

    <h1>{title}</h1>
    <p class="company-sub">{offer_count} Angebot{offer_plural} von <strong>{firma}</strong> auf GewinnspielSchweiz</p>

    {offer_cards}

    <p class="disclaimer-small">Alle Angaben ohne Gewaehr, Stand {generated_date}. Codes werden regelmaessig geprueft, eine Garantie koennen wir aber nicht uebernehmen. GewinnspielSchweiz ist nicht mit {firma} verbunden.</p>

    <hr class="divider">
    <h2>Weitere Rabattcodes</h2>
    <p>Auf <a href="/rabattcode.html">GewinnspielSchweiz</a> findest du laufend gepruefte Rabattcodes verschiedener Schweizer Firmen.</p>
    <a class="back-link" href="/rabattcode.html">&larr; Zurueck zur Uebersicht</a>

  </div>
</div>

<footer>
  <p>
    <a href="/">Home</a>
    <a href="/#gewinnspiele">Gewinnspiele</a>
    <a href="/rabattcode.html">Rabattcodes</a>
    <a href="/blog.html">Blog</a>
    <a href="/newsletter.html">Newsletter</a>
    <a href="/kontakt.html">Fuer Unternehmen</a>
    <a href="/impressum.html">Impressum</a>
    <a href="/agb.html">AGB</a>
    <a href="/datenschutz.html">Datenschutz</a>
  </p>
  <p class="footer-disclaimer">GewinnspielSchweiz ist nicht mit den gelisteten Firmen verbunden. Codes ohne Gewaehr.</p>
</footer>

<script>
  function revealCode(btn, code, link) {{
    window.open(link, '_blank', 'noopener');
    if (navigator.clipboard) {{
      navigator.clipboard.writeText(code).catch(function() {{}});
    }}
    var wrap = document.createElement('div');
    wrap.className = 'revealed-code';
    wrap.innerHTML = '<span class="code-text">' + code + '</span><span class="copied-tag">check kopiert</span>';
    btn.replaceWith(wrap);
  }}
</script>

</body>
</html>
"""


def build_company_page(firma, rows, today):
    slug = slugify(f"{firma}-rabattcode")
    canonical_url = f"{SITE_URL}/rabattcode/{slug}.html"

    offer_cards = []
    any_active = False
    best_bild = ""
    best_kategorie = ""
    best_rabatthoehe = rows[0].get("Rabatthoehe", "").strip()

    for row in rows:
        rabattcode = row.get("Rabattcode", "").strip()
        rabatthoehe = row.get("Rabatthoehe", "").strip()
        kategorie = row.get("Kategorie", "").strip()
        gueltig_bis_raw = row.get("Gueltig_bis", "").strip()
        link = row.get("Link", "").strip()
        bild = row.get("Bild", "").strip()
        beschreibung = row.get("Beschreibung", "").strip()
        zuletzt_geprueft_raw = row.get("Zuletzt_geprueft", "").strip()

        if bild and not best_bild:
            best_bild = bild
        if kategorie and not best_kategorie:
            best_kategorie = kategorie

        gueltig_date = parse_date(gueltig_bis_raw)
        offer_expired = bool(gueltig_date and gueltig_date < today)
        gueltig_display = gueltig_bis_raw if gueltig_bis_raw else "Laufend"
        zuletzt_geprueft = zuletzt_geprueft_raw or today.strftime("%d.%m.%Y")

        if not offer_expired:
            any_active = True
            cta = f'<button class="reveal-btn" onclick="revealCode(this, \'{js_escape(rabattcode)}\', \'{js_escape(link)}\')">Code anzeigen &rarr;</button>'
        else:
            cta = '<div class="expired-note">Dieses Angebot ist abgelaufen</div>'

        offer_cards.append(f"""<div class="offer-card{' is-expired' if offer_expired else ''}">
      <div class="offer-title">{rabatthoehe}</div>
      <p class="offer-desc">{beschreibung}</p>
      <p class="offer-meta">Gueltigkeit: <strong>{gueltig_display}</strong> - Zuletzt geprueft: <strong>{zuletzt_geprueft}</strong></p>
      {cta}
    </div>""")

    all_expired = not any_active
    category_display = (best_kategorie.split("/")[0] if best_kategorie else "Shopping")
    offer_count = len(rows)
    offer_plural = "e" if offer_count != 1 else ""

    if all_expired:
        title_tag = f"{firma} Rabattcode - abgelaufen | GewinnspielSchweiz"
        status_badge = '<span class="badge badge-expired">Abgelaufen</span>'
        robots_content = "noindex, follow"
    else:
        title_tag = f"{firma} Rabattcode {today.year}: {best_rabatthoehe} | GewinnspielSchweiz"
        status_badge = '<span class="badge badge-active">Aktiv</span>'
        robots_content = "index, follow"

    titel = f"{firma} Rabattcode: {best_rabatthoehe}" if best_rabatthoehe else f"{firma} Rabattcode"

    meta_description = f"{firma} Rabattcode: {offer_count} aktuelle{'s' if offer_count == 1 else ''} Angebot{offer_plural}. Codes einfach anzeigen und beim Einkauf sparen."
    meta_description = truncate_at_word(meta_description, 155)

    og_image_tag = f'<meta property="og:image" content="{best_bild}" />' if best_bild else ""
    hero_block = f'<div class="hero-img-wrap"><img src="{best_bild}" alt="{firma} Rabattcode"></div>' if best_bild else ""

    checked_dates = [parse_date(r.get("Zuletzt_geprueft", "")) for r in rows]
    checked_dates = [d for d in checked_dates if d]
    last_checked_iso = max(checked_dates).isoformat() if checked_dates else today.isoformat()

    html = PAGE_TEMPLATE.format(
        title_tag=title_tag,
        meta_description=meta_description,
        canonical_url=canonical_url,
        og_image_tag=og_image_tag,
        robots_content=robots_content,
        schema_headline=title_tag.replace('"', "'"),
        schema_description=meta_description.replace('"', "'"),
        date_published=today.isoformat(),
        last_checked_iso=last_checked_iso,
        site_url=SITE_URL,
        hero_block=hero_block,
        title=titel,
        firma=firma,
        category_display=category_display,
        status_badge=status_badge,
        offer_count=offer_count,
        offer_plural=offer_plural,
        offer_cards="\n".join(offer_cards),
        generated_date=today.strftime("%d.%m.%Y"),
    )
    return slug, html, all_expired


def update_sitemap(active_slugs):
    if not SITEMAP_PATH.exists():
        print("[warn] sitemap.xml nicht gefunden, ueberspringe Sitemap-Update.")
        return

    content = SITEMAP_PATH.read_text(encoding="utf-8")
    today_str = date.today().isoformat()
    new_entries = []
    for slug in active_slugs:
        url = f"{SITE_URL}/rabattcode/{slug}.html"
        if url in content:
            continue
        new_entries.append(
            f"  <url>\n"
            f"    <loc>{url}</loc>\n"
            f"    <lastmod>{today_str}</lastmod>\n"
            f"    <changefreq>weekly</changefreq>\n"
            f"    <priority>0.5</priority>\n"
            f"  </url>\n"
        )

    if new_entries:
        content = content.replace("</urlset>", "".join(new_entries) + "</urlset>")
        SITEMAP_PATH.write_text(content, encoding="utf-8")
        print(f"[info] {len(new_entries)} neue Rabattcode-URLs zur Sitemap hinzugefuegt.")
    else:
        print("[info] Keine neuen Sitemap-Eintraege noetig.")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = fetch_rows()
    today = date.today()
    groups = group_by_firma(rows)

    active_slugs = []
    expired_count = 0

    for firma, firma_rows in groups.items():
        slug, html, all_expired = build_company_page(firma, firma_rows, today)
        out_path = OUTPUT_DIR / f"{slug}.html"
        out_path.write_text(html, encoding="utf-8")
        if all_expired:
            expired_count += 1
        else:
            active_slugs.append(slug)

    update_sitemap(active_slugs)

    print(f"[done] {len(groups)} Firmen-Seiten generiert aus {len(rows)} Zeilen ({len(active_slugs)} aktiv, {expired_count} komplett abgelaufen).")


if __name__ == "__main__":
    main()
