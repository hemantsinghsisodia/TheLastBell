"""Build and verify the V11.1 materials, saved assets, clip poses and review map."""
from pathlib import Path
import json, subprocess, sys
assert sys.version_info[:3]==(3,14,9)
R=Path(__file__).resolve().parents[1]
U=R.parent/"unreal_validation"
for script,report,render in [("materials","materials",False),("update_wool","cloth-update",False),
                              ("check","check",False),("verify_saved","saved",True),("render_warden","render",True)]:
    print("Starting",script,flush=True)
    subprocess.run([sys.executable,str(U/"Scripts/run_unreal.py"),f"{script}_v11_1.py",
                   *(["--editor","--render"] if render else [])],check=True)
    result=json.loads((U/f"Reports/{report}-v11_1.json").read_text())
    if not result.get("passed"): raise RuntimeError(result)
    print("Verified",report,flush=True)
