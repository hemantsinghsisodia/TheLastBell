"""P10-2 (offline): assemble Docs/ArtTest/belltower/survey_p10.md from survey_template.md + generated fragments.
Usage: python s27_build_md.py <fragment_dir>   (fragments from s26_tables.py; kit tables from s17_kit_table.py)"""
import sys, os, subprocess
frag = sys.argv[1]
root = r"C:\Hemant\Prj\Learning\TheLastBell"
t = open(os.path.join(root, r"Tools\belltower\survey\survey_template.md"), encoding="utf-8").read()
for n in ["cloister", "tower_shell", "passage", "flights", "landings", "rails", "gameplay_actors", "ai", "walkpath_tower"]:
    t = t.replace("{{%s.md}}" % n, open(os.path.join(frag, n + ".md"), encoding="utf-8").read())
kit = subprocess.run([sys.executable, os.path.join(root, r"Tools\belltower\survey\s17_kit_table.py")], capture_output=True, text=True, encoding="utf-8").stdout
kit = "\n".join(l for l in kit.splitlines() if not l.startswith("('"))
t = t.replace("{{kit_tables}}", kit)
open(os.path.join(root, r"Docs\ArtTest\belltower\survey_p10.md"), "w", encoding="utf-8").write(t)
print("written", len(t))
