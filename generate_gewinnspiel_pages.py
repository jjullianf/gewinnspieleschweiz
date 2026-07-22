#!/usr/bin/env python3
"""
generate_gewinnspiel_pages.py

Liest das öffentliche Google-Sheet-CSV von GewinnspielSchweiz und erzeugt für
jeden Eintrag eine eigenständige, indexierbare Detailseite unter /gewinnspiele/.

Verwendung (lokal):
    python3 generate_gewinnspiel_pages.py

Verwendung (GitHub Actions):
    Wird automatisch per Workflow ausgeführt, siehe .github/workflows/build-pages.yml
"""

import csv
import io
import re
import unicodedata
import urllib.request
from datetime import datetime, date
from pathlib import Path

# ── Konfiguration ─────────────────────────────────────────────────────────
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTnYZaKWaq94N2sOZfHK6_KsKpCaSeEgqpsWxtYCE8e0S5xcJKmRopzMtorse2hYTHPrA_XIBwv_yHo/pub?gid=0&single=true&output=csv"
SITE_URL = "https://gewinnspieleschweiz.ch"
OUTPUT_DIR = Path("gewinnspiele")
SITEMAP_PATH = Path("sitemap.xml")
LOCAL_CSV_FALLBACK = Path("Gewinnspiele_Schweiz_-_Sheet1.csv")  # für lokale Tests ohne Internet


def slugify(text: str) -> str:
    """Wandelt einen Titel in einen sauberen URL-Slug um."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    text = re.sub(r"-{2,}", "-", text)
    return text[:80].rstrip("-")


def parse_deadline(value: str) -> date | None:
    """Parst TT.MM.JJJJ zu einem date-Objekt. Gibt None zurück, wenn ungültig."""
    value = (value or "").strip()
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except ValueError:
        return None


def fetch_rows() -> list[dict]:
    """Holt die aktuellen Zeilen aus dem Google Sheet (mit lokalem Fallback)."""
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
    return [row for row in reader if row.get("Titel", "").strip()]


# Zuordnung Kategorie-Keyword → passender Blog-Artikel (für interne Verlinkung)
RELATED_BLOG_MAP = [
    (("e-bike", "velo", "mobilität", "fahrzeug"), "/blog/ebike-velo-gewinnspiele-schweiz-2026.html", "Die besten E-Bike & Velo Gewinnspiele Schweiz 2026"),
    (("reisen", "ferien", "wellness"), "/blog/ferien-gewinnspiele-sommer-2026.html", "Die besten Ferien Gewinnspiele Sommer 2026"),
    (("tech", "technik"), "/blog/iphone-gewinnen-schweiz-2026.html", "iPhone gewinnen Schweiz 2026"),
]


def find_related_blog(kategorie: str, titel: str) -> tuple[str, str] | None:
    """Findet einen thematisch passenden Blog-Artikel anhand von Kategorie/Titel."""
    haystack = f"{kategorie} {titel}".lower()
    for keywords, url, label in RELATED_BLOG_MAP:
        if any(k in haystack for k in keywords):
            return url, label
    return None


def truncate_at_word(text: str, max_len: int) -> str:
    """Kürzt einen Text sauber am letzten vollständigen Wort, nie mitten im Wort."""
    text = text.strip()
    if len(text) <= max_len:
        return text
    truncated = text[:max_len].rsplit(" ", 1)[0].rstrip(",.;: ")
    return truncated + "…"


def format_price_line(preis: str) -> str:
    return preis.strip()


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1892773925409513"
     crossorigin="anonymous"></script>
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
    "dateModified": "{date_published}",
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
    .nav-links a {{ font-size: 14px; font-weight: 500; color: var(--text-muted); text-decoration: none; padding: 6px 10px; border-radius: 8px; transition: all 0.2s; white-space: nowrap; }}
    .nav-links a:hover {{ background: var(--red-light); color: var(--red); }}
    .dropdown {{ position: relative; }}
    .dropdown-toggle {{ font-size: 14px; font-weight: 500; color: var(--text-muted); background: none; border: none; padding: 6px 10px; border-radius: 8px; cursor: pointer; font-family: "Inter", sans-serif; transition: all 0.2s; white-space: nowrap; }}
    .dropdown-toggle:hover {{ background: var(--red-light); color: var(--red); }}
    .dropdown-menu {{ display: none; position: absolute; top: calc(100% + 8px); right: 0; background: #fff; border: 1px solid var(--border); border-radius: 12px; padding: 8px; min-width: 180px; box-shadow: 0 8px 24px rgba(0,0,0,0.1); z-index: 300; }}
    .dropdown:hover .dropdown-menu {{ display: block; }}
    .dropdown-menu a {{ display: block; font-size: 13px; font-weight: 500; color: var(--text-muted); padding: 8px 12px; border-radius: 8px; text-decoration: none; }}
    .dropdown-menu a:hover {{ background: var(--red-light); color: var(--red); }}
    .nav-cta {{ background: var(--red) !important; color: #fff !important; padding: 8px 14px !important; border-radius: 8px !important; font-weight: 600 !important; }}
    .nav-cta:hover {{ background: var(--red-hover) !important; color: #fff !important; }}
    .nav-hamburger {{ display: none; background: none; border: none; cursor: pointer; padding: 6px; color: var(--text); }}
    .nav-hamburger svg {{ width: 22px; height: 22px; }}
    .nav-mobile-menu {{ display: none; position: fixed; inset: 0; background: #fff; z-index: 500; padding: 20px; overflow-y: auto; }}
    .nav-mobile-menu.open {{ display: block; }}
    .nav-mobile-header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 28px; }}
    .nav-mobile-close {{ background: none; border: none; cursor: pointer; font-size: 24px; color: var(--text-muted); }}
    .nav-mobile-links {{ display: flex; flex-direction: column; gap: 4px; }}
    .nav-mobile-links a {{ font-size: 17px; font-weight: 600; color: var(--text); text-decoration: none; padding: 14px 16px; border-radius: 12px; display: block; transition: all 0.15s; }}
    .nav-mobile-links a:hover {{ background: var(--red-light); color: var(--red); }}
    .nav-mobile-divider {{ height: 1px; background: var(--border); margin: 8px 0; }}
    .nav-mobile-section-label {{ font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-muted); padding: 8px 16px 4px; }}
    .nav-mobile-cta {{ background: var(--red) !important; color: #fff !important; text-align: center; margin-top: 12px; }}
    .nav-mobile-cta:hover {{ background: var(--red-hover) !important; }}
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
    .company {{ font-size: 15px; color: var(--text-muted); margin-bottom: 28px; }}
    .company strong {{ color: var(--text); }}

    .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 32px; }}
    .info-card {{ background: #fff; border: 1.5px solid var(--border); border-radius: 14px; padding: 18px 20px; }}
    .info-card .label {{ font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); margin-bottom: 6px; }}
    .info-card .value {{ font-size: 15px; font-weight: 700; color: var(--text); }}

    h2 {{ font-size: 19px; font-weight: 800; margin: 32px 0 12px; }}
    p {{ font-size: 15px; line-height: 1.8; color: #333; margin-bottom: 16px; }}
    ol, ul {{ margin: 0 0 16px 20px; }}
    li {{ font-size: 15px; line-height: 1.8; color: #333; margin-bottom: 6px; }}

    .cta-box {{ background: var(--red); border-radius: 16px; padding: 28px; text-align: center; margin: 32px 0; }}
    .cta-box .cta-title {{ color: #fff; font-weight: 800; font-size: 18px; margin-bottom: 6px; }}
    .cta-box .cta-sub {{ color: rgba(255,255,255,0.85); font-size: 13px; margin-bottom: 18px; }}
    .cta-btn {{ display: inline-block; background: #fff; color: var(--red); font-weight: 700; font-size: 15px; padding: 13px 28px; border-radius: 10px; text-decoration: none; }}

    .expired-box {{ background: #f4f4f4; border: 1.5px dashed #ccc; border-radius: 16px; padding: 28px; text-align: center; margin: 32px 0; }}
    .expired-box .exp-title {{ font-weight: 800; font-size: 17px; color: #666; margin-bottom: 6px; }}
    .expired-box .exp-sub {{ color: #999; font-size: 13px; margin-bottom: 18px; }}
    .expired-btn {{ display: inline-block; background: var(--red); color: #fff; font-weight: 700; font-size: 15px; padding: 13px 28px; border-radius: 10px; text-decoration: none; }}

    .divider {{ border: none; border-top: 1px solid var(--border); margin: 36px 0; }}
    .back-link {{ display: inline-flex; align-items: center; gap: 6px; color: var(--text-muted); text-decoration: none; font-size: 14px; font-weight: 500; margin-top: 8px; }}
    .back-link:hover {{ color: var(--red); }}
    .disclaimer-small {{ font-size: 12px; color: #bbb; margin-top: 24px; }}

    footer {{ border-top: 1px solid var(--border); margin-top: 60px; padding: 32px 24px; text-align: center; font-size: 13px; color: var(--text-muted); }}
    footer a {{ color: var(--text-muted); text-decoration: none; margin: 0 10px; }}
    footer a:hover {{ color: var(--red); }}
    .footer-disclaimer {{ font-size: 11px; color: #bbb; margin-top: 16px; line-height: 1.6; }}

    @media (max-width: 500px) {{
      .info-grid {{ grid-template-columns: 1fr; }}
      .hero-img-wrap img {{ height: 220px; }}
    }}
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
      <li><a href="/blog.html">Blog</a></li>
      <li><a href="/kontakt.html">Für Unternehmen</a></li>
      <li class="dropdown">
        <button class="dropdown-toggle">Mehr ▾</button>
        <div class="dropdown-menu">
          <a href="/impressum.html">Impressum</a>
          <a href="/agb.html">AGB</a>
          <a href="/datenschutz.html">Datenschutz</a>
          <a href="https://instagram.com/gewinnspieleschweiz" target="_blank">Instagram</a>
        </div>
      </li>
      <li><a class="nav-cta" href="/newsletter.html">Newsletter</a></li>
    </ul>
    <button class="nav-hamburger" onclick="document.getElementById('mobileMenu').classList.add('open')" aria-label="Menu öffnen">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
    </button>
  </div>
</nav>

<div class="nav-mobile-menu" id="mobileMenu">
  <div class="nav-mobile-header">
    <a class="nav-logo" href="/">
      <img src="/logo.png" alt="GewinnspielSchweiz Logo" style="height:36px;width:36px;border-radius:8px;">
    </a>
    <button class="nav-mobile-close" onclick="document.getElementById('mobileMenu').classList.remove('open')">✕</button>
  </div>
  <div class="nav-mobile-links">
    <a href="/">Home</a>
    <a href="/#gewinnspiele">Gewinnspiele</a>
    <div class="nav-mobile-divider"></div>
    <div class="nav-mobile-section-label">Mehr</div>
    <a href="/blog.html">Blog</a>
    <a href="/kontakt.html">Für Unternehmen</a>
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

    <div class="breadcrumb"><a href="/">Home</a><span>/</span><a href="/#gewinnspiele">Gewinnspiele</a><span>/</span>{title}</div>

    <div class="badges">
      <span class="badge badge-cat">{category_display}</span>
      {status_badge}
    </div>

    <h1>{title}</h1>
    <p class="company">Veranstalter: <strong>{firma}</strong></p>

    <div class="info-grid">
      <div class="info-card">
        <div class="label">Preis</div>
        <div class="value">{preis}</div>
      </div>
      <div class="info-card">
        <div class="label">Teilnahmeschluss</div>
        <div class="value">{deadline_display}</div>
      </div>
    </div>

    <h2>Worum geht's?</h2>
    <p>{beschreibung}</p>

    <h2>So nimmst du teil</h2>
    <p>{schritte}</p>

    {cta_block}

    <p class="disclaimer-small">Alle Angaben ohne Gewähr, Stand {generated_date}. Die Teilnahme erfolgt ausschliesslich über die offizielle Seite des Veranstalters. GewinnspielSchweiz veranstaltet keine Gewinnspiele und ist nicht mit {firma} verbunden.</p>

    {related_block}

    <hr class="divider">

    <h2>Weitere aktuelle Gewinnspiele</h2>
    <p>Auf <a href="/">GewinnspielSchweiz</a> findest du täglich neue und geprüfte Gewinnspiele aus allen Kategorien.</p>

    <a class="back-link" href="/">← Zurück zur Übersicht</a>

  </div>
</div>

<footer>
  <p>
    <a href="/">Home</a>
    <a href="/#gewinnspiele">Gewinnspiele</a>
    <a href="/blog.html">Blog</a>
    <a href="/newsletter.html">Newsletter</a>
    <a href="/kontakt.html">Für Unternehmen</a>
    <a href="/impressum.html">Impressum</a>
    <a href="/agb.html">AGB</a>
    <a href="/datenschutz.html">Datenschutz</a>
  </p>
  <p class="footer-disclaimer">GewinnspielSchweiz veranstaltet keine Gewinnspiele. Teilnahme über den Original-Veranstalter.</p>
</footer>

<script>
  document.addEventListener('click', function(e) {{
    var link = e.target.closest('a[target="_blank"]');
    if (link && link.href) {{
      e.preventDefault();
      window.open(link.href, '_blank', 'noopener');
      window.focus();
    }}
  }});
</script>

</body>
</html>
"""


def build_page(row: dict, today: date) -> tuple[str, str, bool]:
    """Baut den HTML-Inhalt einer Detailseite. Gibt (slug, html, is_expired) zurück."""
    titel = row["Titel"].strip()
    firma = row.get("Firma", "").strip()
    preis = format_price_line(row.get("Preis", ""))
    kategorie = row.get("Kategorie", "").strip()
    deadline_raw = row.get("Deadline", "").strip()
    link = row.get("Link", "").strip()
    bild = row.get("Bild", "").strip()
    beschreibung = row.get("Beschreibung", "").strip()
    schritte = row.get("Schritte", "").strip().replace("|", " → ")

    deadline_date = parse_deadline(deadline_raw)
    is_expired = bool(deadline_date and deadline_date < today)

    slug = slugify(f"{titel}-{firma}") or slugify(titel)
    canonical_url = f"{SITE_URL}/gewinnspiele/{slug}.html"

    category_display = kategorie.split("/")[0] if kategorie else "Gewinnspiel"

    if is_expired:
        title_tag = f"{titel} – Gewinnspiel beendet | GewinnspielSchweiz"
        status_badge = '<span class="badge badge-expired">Beendet</span>'
        robots_content = "noindex, follow"
        cta_block = f"""<div class="expired-box">
      <div class="exp-title">Dieses Gewinnspiel ist beendet</div>
      <div class="exp-sub">Der Teilnahmeschluss ({deadline_raw}) ist bereits verstrichen.</div>
      <a class="expired-btn" href="/#gewinnspiele">Aktuelle Gewinnspiele ansehen →</a>
    </div>"""
    else:
        title_tag = f"{titel} – {firma} Gewinnspiel | GewinnspielSchweiz"
        status_badge = '<span class="badge badge-active">Aktiv</span>'
        robots_content = "index, follow"
        cta_block = f"""<div class="cta-box">
      <div class="cta-title">Jetzt teilnehmen</div>
      <div class="cta-sub">Teilnahmeschluss: {deadline_raw}</div>
      <a class="cta-btn" href="{link}" target="_blank" rel="noopener">Zum Gewinnspiel →</a>
    </div>"""

    meta_description = f"{titel} bei {firma}: {preis}. Teilnahmeschluss {deadline_raw}."
    if beschreibung:
        meta_description += f" {beschreibung}"
    meta_description = truncate_at_word(meta_description, 155)

    og_image_tag = f'<meta property="og:image" content="{bild}" />' if bild else ""
    hero_block = f'<div class="hero-img-wrap"><img src="{bild}" alt="{titel}"></div>' if bild else ""

    related = find_related_blog(kategorie, titel)
    if related:
        rel_url, rel_label = related
        related_block = f'<p>📖 Mehr zum Thema: <a href="{rel_url}">{rel_label}</a></p>'
    else:
        related_block = ""

    html = PAGE_TEMPLATE.format(
        title_tag=title_tag,
        meta_description=meta_description,
        canonical_url=canonical_url,
        og_image_tag=og_image_tag,
        robots_content=robots_content,
        schema_headline=title_tag.replace('"', "'"),
        schema_description=meta_description.replace('"', "'"),
        date_published=today.isoformat(),
        site_url=SITE_URL,
        hero_block=hero_block,
        title=titel,
        category_display=category_display,
        status_badge=status_badge,
        firma=firma,
        preis=preis,
        deadline_display=deadline_raw,
        beschreibung=beschreibung,
        schritte=schritte,
        cta_block=cta_block,
        related_block=related_block,
        generated_date=today.strftime("%d.%m.%Y"),
    )
    return slug, html, is_expired


def update_sitemap(active_slugs: list[str]):
    """Fügt aktive Gewinnspiel-Detailseiten zur sitemap.xml hinzu (falls nicht schon vorhanden)."""
    if not SITEMAP_PATH.exists():
        print("[warn] sitemap.xml nicht gefunden, überspringe Sitemap-Update.")
        return

    content = SITEMAP_PATH.read_text(encoding="utf-8")
    today_str = date.today().isoformat()
    new_entries = []
    for slug in active_slugs:
        url = f"{SITE_URL}/gewinnspiele/{slug}.html"
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
        print(f"[info] {len(new_entries)} neue URLs zur Sitemap hinzugefügt.")
    else:
        print("[info] Keine neuen Sitemap-Einträge nötig.")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = fetch_rows()
    today = date.today()

    active_slugs = []
    expired_count = 0

    for row in rows:
        slug, html, is_expired = build_page(row, today)
        out_path = OUTPUT_DIR / f"{slug}.html"
        out_path.write_text(html, encoding="utf-8")
        if is_expired:
            expired_count += 1
        else:
            active_slugs.append(slug)

    update_sitemap(active_slugs)

    print(f"[done] {len(rows)} Seiten generiert ({len(active_slugs)} aktiv, {expired_count} abgelaufen).")


if __name__ == "__main__":
    main()
