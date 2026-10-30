#!/usr/bin/env python3
"""Génère les SVG du profil GitHub (thèmes clair et sombre).

Usage :
    python scripts/generate.py            # bandeau, projets, stack (+ stats si GITHUB_TOKEN)
    GITHUB_TOKEN=xxx python scripts/generate.py

Tout le contenu éditable est dans config.json à la racine du dépôt.
"""
import json
import os
import urllib.request
from datetime import datetime, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))

THEMES = {
    "light": {
        "bg": "#FFFFFF", "surface": "#F7F6F2", "text": "#111111", "muted": "#5F5F5A",
        "border": "#E6E4DD", "accent": "#F59E0B", "accent2": "#EA580C", "dot": "#E6E4DD",
    },
    "dark": {
        "bg": "#0F0F0F", "surface": "#181818", "text": "#F4F3EE", "muted": "#A3A29C",
        "border": "#2B2B2B", "accent": "#FBBF24", "accent2": "#F97316", "dot": "#262626",
    },
}

SANS = "-apple-system, 'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"
MONO = "'JetBrains Mono', 'Fira Code', Consolas, 'DejaVu Sans Mono', monospace"


def text_width(s, size, mono=False):
    """Estimation grossière de la largeur d'un texte (pas de mesure réelle dans un SVG statique)."""
    return len(s) * size * (0.61 if mono else 0.56)


def gradient(t, gid="g"):
    return (f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{t["accent"]}"/><stop offset="1" stop-color="{t["accent2"]}"/>'
            f'</linearGradient>')


def svg(w, h, body, t, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{escape(title)}"><title>{escape(title)}</title>{body}</svg>\n')


def dots(t, x0, y0, cols, rows, gap=16):
    out = []
    for r in range(rows):
        for c in range(cols):
            out.append(f'<circle cx="{x0 + c * gap}" cy="{y0 + r * gap}" r="1.6" fill="{t["dot"]}"/>')
    return "".join(out)


# ---------------------------------------------------------------- bandeau
def header(t):
    h = CONFIG["header"]
    W, H = 1000, 230
    tagline = h["tagline"]
    tw = text_width(tagline, 15, mono=True)
    body = f"""
<defs>{gradient(t)}</defs>
<style>
  .cursor {{ animation: blink 1.1s steps(1) infinite; }}
  @keyframes blink {{ 50% {{ opacity: 0; }} }}
  @media (prefers-reduced-motion: reduce) {{ .cursor {{ animation: none; }} }}
</style>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="18" fill="{t['bg']}" stroke="{t['border']}"/>
{dots(t, 700, 34, 17, 11)}
<path d="M780 230 L1000 10 L1000 230 Z" fill="url(#g)" opacity="0.10"/>
<path d="M880 230 L1000 110 L1000 230 Z" fill="url(#g)" opacity="0.22"/>
<rect x="48" y="52" width="6" height="104" rx="3" fill="url(#g)"/>
<text x="74" y="68" font-family="{MONO}" font-size="14" fill="{t['muted']}" dominant-baseline="middle">{escape(h['hello'])}</text>
<text x="72" y="112" font-family="{SANS}" font-size="46" font-weight="800" fill="{t['text']}" letter-spacing="-1">{escape(h['name'])}</text>
<text x="74" y="146" font-family="{SANS}" font-size="20" font-weight="600" fill="{t['accent2']}">{escape(h['role'])}</text>
<rect x="48" y="174" width="{tw + 52}" height="32" rx="8" fill="{t['surface']}" stroke="{t['border']}"/>
<text x="62" y="191" font-family="{MONO}" font-size="15" fill="{t['accent']}" dominant-baseline="middle">&gt;</text>
<text x="80" y="191" font-family="{MONO}" font-size="15" fill="{t['text']}" dominant-baseline="middle">{escape(tagline)}</text>
<rect class="cursor" x="{82 + tw}" y="182" width="9" height="18" fill="{t['accent']}"/>
"""
    return svg(W, H, body, t, f"{h['name']}, {h['role']}")


# ---------------------------------------------------------------- cartes projets
def wrap(s, max_chars):
    lines, cur = [], ""
    for word in s.split():
        if len(cur) + len(word) + 1 > max_chars and cur:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    if cur:
        lines.append(cur)
    return lines


def merged_prs(repo, login, token):
    q = 'query($q: String!) { search(query: $q, type: ISSUE, first: 1) { issueCount } }'
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": q, "variables": {"q": f"repo:{repo} author:{login} is:pr is:merged"}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["data"]["search"]["issueCount"]


def project_card(p, t, counter=None):
    W, H = 490, 190
    desc = "".join(
        f'<text x="28" y="{86 + i * 21}" font-family="{SANS}" font-size="14" fill="{t["muted"]}">{escape(l)}</text>'
        for i, l in enumerate(wrap(p["description"], 56)[:3]))
    chips, x = [], 28
    for tag in p["tags"]:
        w = text_width(tag, 12, mono=True) + 18
        chips.append(f'<rect x="{x}" y="148" width="{w}" height="24" rx="12" fill="{t["surface"]}" stroke="{t["border"]}"/>'
                     f'<text x="{x + w / 2}" y="160.5" text-anchor="middle" dominant-baseline="middle" '
                     f'font-family="{MONO}" font-size="12" fill="{t["text"]}">{escape(tag)}</text>')
        x += w + 8
    status = ""
    if p.get("status"):
        sw = text_width(p["status"], 11, mono=True) + 20
        status = (f'<rect x="{W - 24 - sw}" y="24" width="{sw}" height="22" rx="11" fill="url(#g)"/>'
                  f'<text x="{W - 24 - sw / 2}" y="35.5" text-anchor="middle" dominant-baseline="middle" '
                  f'font-family="{MONO}" font-size="11" font-weight="700" fill="#111111">{escape(p["status"])}</text>')
    metric = ""
    if counter is not None:
        metric = (f'<text x="{W - 28}" y="168" text-anchor="end" font-family="{SANS}" font-size="22" font-weight="800" fill="url(#g)">{counter}</text>'
                  f'<text x="{W - 28}" y="142" text-anchor="end" font-family="{MONO}" font-size="11" fill="{t["muted"]}">PR mergées</text>')
    body = f"""
<defs>{gradient(t)}</defs>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" fill="{t['bg']}" stroke="{t['border']}"/>
<rect x="0" y="20" width="4" height="30" rx="2" fill="url(#g)"/>
<text x="28" y="44" font-family="{SANS}" font-size="21" font-weight="700" fill="{t['text']}">{escape(p['name'])}</text>
{status}{desc}{''.join(chips)}{metric}
"""
    return svg(W, H, body, t, f"{p['name']} : {p['description']}")


# ---------------------------------------------------------------- stack
def stack(t):
    W = 1000
    groups = CONFIG["stack"]
    rows, y = [], 34
    for g in groups:
        rows.append(f'<text x="32" y="{y + 16}" font-family="{MONO}" font-size="13" fill="{t["accent2"]}" '
                    f'dominant-baseline="middle">{escape(g["label"])}</text>')
        x = 220
        for item in g["items"]:
            w = text_width(item, 13) + 26
            if x + w > W - 32:
                x, y = 220, y + 40
            rows.append(f'<rect x="{x}" y="{y}" width="{w}" height="30" rx="8" fill="{t["surface"]}" stroke="{t["border"]}"/>'
                        f'<text x="{x + w / 2}" y="{y + 16}" text-anchor="middle" dominant-baseline="middle" '
                        f'font-family="{SANS}" font-size="13" font-weight="500" fill="{t["text"]}">{escape(item)}</text>')
            x += w + 8
        y += 46
    H = y + 18
    body = (f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" fill="{t["bg"]}" stroke="{t["border"]}"/>'
            + "".join(rows))
    alt = ". ".join(f"{g['label']} : {', '.join(g['items'])}" for g in groups)
    return svg(W, H, body, t, alt)


# ---------------------------------------------------------------- stats (GitHub API)
QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes { stargazerCount languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } } }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      contributionCalendar { totalContributions }
    }
  }
}
"""


def fetch_stats(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    if "errors" in data:
        raise RuntimeError(data["errors"])
    u = data["data"]["user"]
    langs = {}
    excluded = set(CONFIG["stats"].get("exclude_languages", []))
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            name = e["node"]["name"]
            if name not in excluded:
                langs[name] = langs.get(name, 0) + e["size"]
    total = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:6]
    cc = u["contributionsCollection"]
    return {
        "counters": [
            (cc["contributionCalendar"]["totalContributions"], "contributions", "sur 12 mois"),
            (cc["totalCommitContributions"], "commits", "sur 12 mois"),
            (cc["totalPullRequestContributions"], "pull requests", "sur 12 mois"),
            (u["repositories"]["totalCount"], "dépôts publics", "au total"),
        ],
        "langs": [(n, s / total) for n, s in top],
    }


def stats(t, data):
    W, H = 1000, 236
    cells, cw = [], (W - 64) / 4
    for i, (value, label, sub) in enumerate(data["counters"]):
        x = 32 + i * cw
        cells.append(f'<rect x="{x + 4}" y="28" width="{cw - 8}" height="104" rx="12" fill="{t["surface"]}" stroke="{t["border"]}"/>'
                     f'<text x="{x + 26}" y="80" font-family="{SANS}" font-size="36" font-weight="800" fill="url(#g)">{value}</text>'
                     f'<text x="{x + 26}" y="104" font-family="{SANS}" font-size="14" font-weight="600" fill="{t["text"]}">{escape(label)}</text>'
                     f'<text x="{x + 26}" y="121" font-family="{MONO}" font-size="11" fill="{t["muted"]}">{escape(sub)}</text>')
    # barre des langages
    shades = [t["accent"], t["accent2"], t["text"], t["muted"], t["border"], t["dot"]]
    bar, legend, x = [], [], 36.0
    bw = W - 72
    for i, (name, share) in enumerate(data["langs"]):
        w = bw * share
        bar.append(f'<rect x="{x:.1f}" y="160" width="{max(w - 2, 1):.1f}" height="10" fill="{shades[i]}"/>')
        x += w
    lx = 36
    for i, (name, share) in enumerate(data["langs"]):
        label = f"{name} {share * 100:.0f}%"
        legend.append(f'<circle cx="{lx + 5}" cy="196" r="5" fill="{shades[i]}" stroke="{t["border"]}"/>'
                      f'<text x="{lx + 16}" y="196" dominant-baseline="middle" font-family="{SANS}" font-size="13" fill="{t["text"]}">{escape(label)}</text>')
        lx += text_width(label, 13) + 40
    updated = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    body = f"""
<defs>{gradient(t)}<clipPath id="bar"><rect x="36" y="160" width="{bw}" height="10" rx="5"/></clipPath></defs>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" fill="{t['bg']}" stroke="{t['border']}"/>
{''.join(cells)}
<g clip-path="url(#bar)">{''.join(bar)}</g>
{''.join(legend)}
<text x="{W - 32}" y="222" text-anchor="end" font-family="{MONO}" font-size="10" fill="{t['muted']}">màj auto · {updated}</text>
"""
    return svg(W, H, body, t, "Statistiques GitHub")


# ---------------------------------------------------------------- main
def write(name, fn, *args):
    ASSETS.mkdir(exist_ok=True)
    for mode, t in THEMES.items():
        (ASSETS / f"{name}-{mode}.svg").write_text(fn(t, *args), encoding="utf-8")


def main():
    write("header", header)
    write("stack", stack)
    token = os.environ.get("GITHUB_TOKEN")
    for p in CONFIG["projects"]:
        counter = None
        if p.get("pr_counter") and os.environ.get("STATS_DEMO"):
            counter = 7
        elif p.get("pr_counter") and token:
            try:
                counter = merged_prs(p["pr_counter"], CONFIG["stats"]["login"], token)
            except Exception as e:
                print(f"Compteur PR non mis à jour : {e}")
                continue  # on garde l'ancienne carte
        write(f"project-{p['slug']}", lambda t, p=p, c=counter: project_card(p, t, c))
    if token and not os.environ.get("STATS_DEMO"):
        try:
            write("stats", stats, fetch_stats(CONFIG["stats"]["login"], token))
        except Exception as e:  # on garde les anciennes stats plutôt que de casser le profil
            print(f"Stats non mises à jour : {e}")
    elif os.environ.get("STATS_DEMO"):
        demo = {"counters": [(312, "contributions", "sur 12 mois"), (248, "commits", "sur 12 mois"),
                             (14, "pull requests", "sur 12 mois"), (17, "dépôts publics", "au total")],
                "langs": [("PHP", .38), ("JavaScript", .22), ("Processing", .16), ("Python", .12), ("CSS", .08), ("HTML", .04)]}
        write("stats", stats, demo)
    else:
        print("Pas de GITHUB_TOKEN : stats non régénérées.")


if __name__ == "__main__":
    main()
