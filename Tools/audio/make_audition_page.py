"""P16-A4: build a local HTML listening page (Docs/ArtTest/audio/audition.html) from the two audition markdown tables.

    python -I Tools/audio/make_audition_page.py

Open the page in Chrome or Edge (double-click it in Explorer). Each sound has a player, the "what to listen for" note and a
keep / redo / replace choice with a comment box; "Copy my choices" puts a plain-text summary on the clipboard to paste in chat.
Choices are kept in the browser's localStorage only. Reads only the two markdown files; writes only the HTML page.
"""
import html
import io
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
DOCS = os.path.join(ROOT, "Docs", "ArtTest", "audio")
SOURCES = [("Generated (our scripts)", "audition.md", "What to listen for"),
           ("Recorded (Kenney and Freesound CC0)", "audition_recorded.md", "What to listen for")]
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+\.wav)\)")


def parse(md_name, note_col):
    groups, cur, header = [], None, None
    for line in io.open(os.path.join(DOCS, md_name), encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("## "):
            cur = {"title": line[3:].strip(), "rows": []}
            groups.append(cur)
            header = None
            continue
        if not line.startswith("|") or cur is None:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if set(line.replace("|", "").strip()) <= set("-: "):
            continue
        m = LINK.search(cells[0])
        if not m:
            continue
        rec = dict(zip(header, cells))
        note = rec.get(note_col, "")
        weak = rec.get("Weak / note", "")
        cur["rows"].append({"name": m.group(1), "href": m.group(2), "len": rec.get("Length", rec.get("Len", "")),
                            "note": note, "weak": weak})
    return [g for g in groups if g["rows"]]


def main():
    parts = []
    total = 0
    for title, md, col in SOURCES:
        parts.append("<h2>%s</h2>" % html.escape(title))
        for g in parse(md, col):
            parts.append("<h3>%s</h3>" % html.escape(g["title"]))
            for r in g["rows"]:
                total += 1
                rid = html.escape(r["name"])
                weak = ("<div class='weak'>Note: %s</div>" % html.escape(r["weak"])) if r["weak"] and r["weak"] not in ("-", "") else ""
                parts.append(
                    "<div class='row' data-id='%s'><div class='head'><b>%s</b> <span class='len'>%s</span></div>"
                    "<audio controls preload='none' src='%s'></audio>"
                    "<div class='note'>%s</div>%s"
                    "<div class='choice'>"
                    "<label><input type='radio' name='%s' value='keep'> keep</label>"
                    "<label><input type='radio' name='%s' value='redo'> redo</label>"
                    "<label><input type='radio' name='%s' value='replace'> replace</label>"
                    "<input class='cmt' type='text' placeholder='what to change (optional)'></div></div>"
                    % (rid, rid, html.escape(r["len"]), html.escape(r["href"]), html.escape(r["note"]), weak, rid, rid, rid))
    page = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Phase 16 Audition</title>
<style>
:root { --bg:#14161a; --fg:#e8e6e1; --muted:#9a9890; --card:#1d2026; --line:#2c3038; --accent:#d9a441; --warn:#e07a5f; }
body { background:var(--bg); color:var(--fg); font:15px/1.45 system-ui, sans-serif; margin:0 auto; max-width:980px; padding:16px; }
h1 { font-size:22px; } h2 { margin-top:36px; border-bottom:1px solid var(--line); padding-bottom:6px; } h3 { color:var(--accent); margin-top:24px; }
.row { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:10px 12px; margin:8px 0; }
.head .len { color:var(--muted); font-size:13px; margin-left:6px; }
audio { width:100%%; margin:6px 0; }
.note { color:var(--fg); font-size:14px; } .weak { color:var(--warn); font-size:13px; margin-top:4px; }
.choice { margin-top:6px; display:flex; flex-wrap:wrap; gap:12px; align-items:center; font-size:14px; }
.cmt { flex:1; min-width:200px; background:#111; color:var(--fg); border:1px solid var(--line); border-radius:4px; padding:4px 6px; }
.bar { position:sticky; top:0; background:var(--bg); padding:8px 0; border-bottom:1px solid var(--line); display:flex; gap:12px; align-items:center; z-index:2; }
button { background:var(--accent); color:#111; border:0; border-radius:6px; padding:8px 14px; font-weight:600; cursor:pointer; }
#count { color:var(--muted); }
</style></head><body>
<h1>Phase 16 audition: %(total)d sounds</h1>
<p>Listen on headphones. Turn the volume down before thunder, bell stages 4 and 5, the stings and the Warden roars. For each sound pick
<b>keep</b>, <b>redo</b> (say what to change) or <b>replace</b> (use a different recording). Unmarked sounds count as keep.
When done, press <b>Copy my choices</b> and paste the text into the chat.</p>
<div class="bar"><button id="copy">Copy my choices</button><span id="count"></span></div>
%(body)s
<script>
const KEY = "lb_p16_audition";
let saved = {}; try { saved = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) {}
const rows = [...document.querySelectorAll(".row")];
function save() { try { localStorage.setItem(KEY, JSON.stringify(saved)); } catch (e) {} count(); }
function count() { const n = Object.values(saved).filter(v => v.c && v.c !== "keep").length;
  document.getElementById("count").textContent = Object.keys(saved).length + " marked, " + n + " to redo or replace"; }
rows.forEach(r => { const id = r.dataset.id, s = saved[id] || {};
  r.querySelectorAll("input[type=radio]").forEach(b => { if (b.value === s.c) b.checked = true;
    b.addEventListener("change", () => { saved[id] = Object.assign(saved[id] || {}, { c: b.value }); save(); }); });
  const t = r.querySelector(".cmt"); t.value = s.t || "";
  t.addEventListener("input", () => { saved[id] = Object.assign(saved[id] || {}, { t: t.value }); save(); }); });
document.querySelectorAll("audio").forEach(a => a.addEventListener("play", () =>
  document.querySelectorAll("audio").forEach(o => { if (o !== a) o.pause(); })));
document.getElementById("copy").addEventListener("click", () => {
  const lines = ["Phase 16 audition results:"];
  rows.forEach(r => { const s = saved[r.dataset.id]; if (s && (s.c && s.c !== "keep" || s.t)) lines.push("- " + r.dataset.id + ": " + (s.c || "keep") + (s.t ? " -- " + s.t : "")); });
  if (lines.length === 1) lines.push("- everything keep");
  const text = lines.join("\\n");
  navigator.clipboard.writeText(text).then(() => alert("Copied. Paste it into the chat."), () => prompt("Copy this text:", text)); });
count();
</script></body></html>
""" % {"total": total, "body": "\n".join(parts)}
    out = os.path.join(DOCS, "audition.html")
    io.open(out, "w", encoding="utf-8").write(page)
    print("wrote", os.path.relpath(out, ROOT), total, "sounds")


if __name__ == "__main__":
    main()
