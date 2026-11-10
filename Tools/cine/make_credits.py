"""P17-2: build the credits roll (plan Docs/plans/P17_CINEMATICS.md, section 6).

Pure Python (no Unreal). Run from anywhere:
    python Tools/cine/make_credits.py

Reads  Docs/ASSET_REGISTRY.md (the "External assets" table only; the Epic template table is not parsed).
Writes Docs/plans/p17_credits.json        list of {"style": "Heading|Name|Small|Gap", "text": "..."}  (read by Tools/cine/p17_assets.py)
       Docs/ArtTest/cine/credits_preview.md  a readable preview for the owner's review (P17-6)

Rules:
  * Author names come ONLY from the registry rows (never typed here), except the owner and the fixed lines the plan names.
  * Provider lines: "Poly Haven: A, B", "ambientCG", "Fab: ...", "BlenderKit: ...", "Kenney", "Freesound: ...". Authors are
    de-duplicated (case-insensitive), sorted (case-insensitive) and comma-joined; a line over MAX_LINE characters wraps at an
    author boundary into several Name lines (a continued line ends with a comma).
  * Excluded rows: any row whose Unreal path column says "not imported" (nothing ships); in-house / generated in-project / the owner's own build / Epic template rows; Mixamo rows (the fixed
    "Animation / Adobe Mixamo" line covers them); the Roboto font row (the Fonts line covers it); rows whose Use says "not used" or
    "reference ... only" (nothing of them ships).
  * Privacy: no e-mail address is ever written (the script asserts it).
"""
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REGISTRY = os.path.join(ROOT, "Docs", "ASSET_REGISTRY.md")
OUT_JSON = os.path.join(ROOT, "Docs", "plans", "p17_credits.json")
OUT_MD = os.path.join(ROOT, "Docs", "ArtTest", "cine", "credits_preview.md")

MAX_LINE = 90

# (provider key used in the registry's Source column, display name, section)
PROVIDERS = [
    ("Poly Haven", "Poly Haven", "Models and textures"),
    ("ambientCG", "ambientCG", "Models and textures"),
    ("Fab", "Fab", "Models and textures"),
    ("BlenderKit", "BlenderKit", "Models and textures"),
    ("Kenney", "Kenney", "Sound"),
    ("Freesound", "Freesound", "Sound"),
]

COL_ASSET, COL_SOURCE, COL_AUTHOR, COL_UNREAL_PATH, COL_USE = 0, 1, 2, 8, 9


def provider_of(source):
    """(provider key, "") for a credited Source cell, or (None, reason) when the row is excluded."""
    s = source.strip()
    low = s.lower()
    if low.startswith("in-house"):
        return None, "in-house"
    if low.startswith("generated in-project"):
        return None, "project-generated"
    if low.startswith("owner's own build"):
        return None, "owner's own build"
    if low.startswith("unreal engine"):
        return None, "engine font (Fonts line)"
    if low.startswith("mixamo"):
        return None, "Mixamo (fixed Animation line)"
    if low.startswith("https://kenney.nl") or low == "kenney":
        return "Kenney", ""
    s = re.sub(r"\s*\(derived\)\s*$", "", s)  # "Poly Haven (derived)"
    for key, _display, _section in PROVIDERS:
        if s == key:
            return key, ""
    raise SystemExit("make_credits: unknown Source %r in the registry; add it to PROVIDERS or the exclusions" % source)


def clean_authors(cell, provider_display):
    """Names of one Author cell: backticks and (parentheticals) removed, split on commas; the provider's own name is dropped."""
    cell = cell.replace("`", "")
    cell = re.sub(r"\([^)]*\)", "", cell)
    out = []
    for n in (x.strip() for x in cell.split(",")):
        if not n or n.lower() == provider_display.lower() or n.lower() in ("n/a", "none"):
            continue
        out.append(n)
    return out


def parse_registry():
    text = open(REGISTRY, encoding="utf-8").read().split("\n")
    start = next(i for i, l in enumerate(text) if l.strip() == "## External assets")
    rows = []
    for l in text[start:]:
        if not l.startswith("|"):
            continue
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        if len(cells) != 13 or cells[0] == "Asset" or set(cells[0]) <= set("-: "):
            continue
        rows.append(cells)
    return rows


def wrap_authors(prefix, names):
    """Lines of at most MAX_LINE characters: the first starts with prefix; a continued line ends with a comma."""
    lines = []
    cur = prefix
    first_on_line = False  # the prefix is already on the first line, so the first name follows a space
    for i, n in enumerate(names):
        last = i == len(names) - 1
        token = n + ("" if last else ",")
        sep = "" if first_on_line else " "
        if len(cur) + len(sep) + len(token) > MAX_LINE:
            lines.append(cur)
            cur = token
        else:
            cur = cur + sep + token
        first_on_line = False
    lines.append(cur)
    return lines


def build():
    rows = parse_registry()
    authors = {key: {} for key, _d, _s in PROVIDERS}  # key -> {lower name: name}
    used_rows = {key: 0 for key, _d, _s in PROVIDERS}
    excluded = []
    display = {key: d for key, d, _s in PROVIDERS}
    for cells in rows:
        asset, source, author, use = cells[COL_ASSET], cells[COL_SOURCE], cells[COL_AUTHOR], cells[COL_USE]
        key, why = provider_of(source)
        if key is None:
            excluded.append((asset, why))
            continue
        use_low = use.lower()
        if "not imported" in cells[COL_UNREAL_PATH].lower():
            excluded.append((asset, "not imported (nothing ships)"))
            continue
        if use_low.startswith("not used"):
            excluded.append((asset, "not used in the game"))
            continue
        if re.search(r"reference for .*only", use_low):
            excluded.append((asset, "reference only, nothing ships"))
            continue
        used_rows[key] += 1
        for n in clean_authors(author, display[key]):
            authors[key].setdefault(n.lower(), n)

    lines = []

    def add(style, text=""):
        lines.append({"style": style, "text": text})

    # Fixed lines (plan section 6)
    add("Heading", "THE LAST BELL")
    add("Gap")
    add("Small", "Created by")
    add("Name", "Hemant Singh Sisodia")
    add("Gap")
    add("Small", "Developed with")
    add("Name", "Claude (Anthropic)")
    add("Gap")
    add("Small", "Made with")
    add("Name", "Unreal Engine 5")
    add("Name", "Blender")
    add("Gap")
    add("Small", "Warden base model")
    add("Name", "Generated with Tencent Hunyuan3D-2 mini, via Modly")
    add("Gap")
    add("Small", "Animation")
    add("Name", "Adobe Mixamo")

    # Generated from the registry
    sections = []
    for _k, _d, sec in PROVIDERS:
        if sec not in sections:
            sections.append(sec)
    for sec in sections:
        add("Gap")
        add("Heading", sec)
        for key, disp, s in PROVIDERS:
            if s != sec or used_rows[key] == 0:
                continue
            names = sorted(authors[key].values(), key=lambda n: (n.lower(), n))
            if not names:
                add("Name", disp)
            else:
                for line in wrap_authors(disp + ":", names):
                    add("Name", line)

    add("Gap")
    add("Small", "Fonts")
    add("Name", "Roboto, Christian Robertson (Apache 2.0)")
    add("Gap")
    add("Name", "Thank you for playing.")
    return lines, authors, used_rows, excluded


def main():
    lines, authors, used_rows, excluded = build()
    blob = json.dumps(lines, ensure_ascii=False)
    if re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", blob):
        raise SystemExit("make_credits: an e-mail address is in the output; refusing to write it")
    too_long = [l["text"] for l in lines if len(l["text"]) > MAX_LINE]
    if too_long:
        raise SystemExit("make_credits: lines over %d characters: %r" % (MAX_LINE, too_long))

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(lines, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    md = ["# Credits preview (P17-2)", "",
          "Generated by `Tools/cine/make_credits.py` from `Docs/ASSET_REGISTRY.md`; do not edit by hand (edit the registry or the script and re-run).",
          "Source of the data asset: `Docs/plans/p17_credits.json`. The owner reviews this file in P17-6.", "",
          "Style key: `#` Heading (large), plain = Name, `(small)` = Small, `~` = Gap (40 px).", "", "```"]
    for l in lines:
        st, tx = l["style"], l["text"]
        if st == "Heading":
            md.append("# " + tx)
        elif st == "Small":
            md.append("(small) " + tx)
        elif st == "Gap":
            md.append("~")
        else:
            md.append(tx)
    md += ["```", "", "## Summary", "",
           "- %d lines: %s" % (len(lines), ", ".join("%d %s" % (sum(1 for l in lines if l["style"] == s), s) for s in ("Heading", "Small", "Name", "Gap"))),
           "- Registry rows credited and distinct authors per provider:"]
    for key, n in used_rows.items():
        md.append("  - %s: %d rows, %d authors" % (key, n, len(authors[key])))
    md += ["- Excluded registry rows (%d):" % len(excluded)]
    reasons = {}
    for asset, why in excluded:
        reasons.setdefault(why, []).append(asset)
    for why, assets in sorted(reasons.items()):
        md.append("  - %s (%d): %s" % (why, len(assets), "; ".join(a[:48] for a in assets[:6]) + (" ..." if len(assets) > 6 else "")))
    with open(OUT_MD, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(md) + "\n")

    print("credits: %d lines -> %s" % (len(lines), os.path.relpath(OUT_JSON, ROOT)))
    for key, n in used_rows.items():
        print("  %-10s %3d rows %3d authors" % (key, n, len(authors[key])))
    print("  excluded rows: %d (%s)" % (len(excluded), ", ".join("%s %d" % (w, len(a)) for w, a in sorted(reasons.items()))))
    print("  preview: %s" % os.path.relpath(OUT_MD, ROOT))


if __name__ == "__main__":
    sys.exit(main())
