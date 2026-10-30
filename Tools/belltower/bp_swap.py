"""Blueprint-swap dump/diff helper (P10-6b, D1.17 section 0). Unreal MCP; editor open on L_Monastery.

Usage (python Tools/belltower/bp_swap.py ...; use C:/ paths in Git Bash):
    dump <label> <out.json>        # full dump of the placed actor with this exact label: class, label, folder, world transform,
                                   # every actor property, every component (path, class, all properties incl. relative transform,
                                   # mesh, override materials, collision, visibility, InteractComp / InspectableComp / SeqComp values)
    diff <a.json> <b.json>         # normalised diff (internal actor names and the actor GUID are ignored); prints every difference,
                                   # grouped by actor / component; exit code 0 = no differences, 1 = differences
    diff <a.json> <b.json> --json  # same, machine-readable

The module is also a library: dump_actor(ue, label) -> dict, diff_dumps(a, b) -> [(where, prop, a, b)], find_exact(ue, label).
It only reads from the editor; it never edits anything.
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mcp"))
from ue import UE  # noqa: E402

S = "editor_toolset.toolsets.scene.SceneTools"
A = "editor_toolset.toolsets.actor.ActorTools"
O = "editor_toolset.toolsets.object.ObjectTools"

# properties that always differ between two instances and carry no information
IGNORE_ACTOR = {"actorGuid", "actorInstanceGuid"}
IGNORE_ANY = {"componentGuid"}


def call(ue, ts, tool, args=None, tries=3):
    """UE.call with retry on connection resets (returns (ue, result); ue may be a fresh session)."""
    for k in range(tries):
        try:
            return ue, ue.call(ts, tool, args)
        except RuntimeError as e:
            raise RuntimeError("%s.%s: %s" % (ts.split(".")[-1], tool, str(e)[:400]))
        except Exception as e:  # connection reset
            if k == tries - 1:
                raise
            print("  retry %s (%s)" % (tool, str(e)[:100]), flush=True)
            time.sleep(2)
            ue = UE()
    return ue, None


def as_json(v):
    return json.loads(v) if isinstance(v, str) else v


def find_exact(ue, label):
    """The one actor whose label is exactly `label` (find_actors matches substrings)."""
    hits = ue.call(S, "find_actors", {"name": label, "tag": "", "collision_channels": []}) or []
    ex = [a for a in hits if ue.call(A, "get_label", {"actor": a}) == label]
    if len(ex) != 1:
        raise RuntimeError("expected exactly 1 actor labelled %r, found %d" % (label, len(ex)))
    return ex[0]


_folder_cache = {}


def folder_of(ue, label, refresh=False):
    """Outliner folder of the actor (no direct getter: scan the folders, Gameplay* first)."""
    if not refresh and label in _folder_cache:
        return _folder_cache[label]
    folders = ue.call(S, "get_folders", {}) or []
    folders.sort(key=lambda f: (not f.startswith("Gameplay"), f))
    for f in folders:
        try:
            acs = ue.call(S, "get_actors_in_folder", {"folder_path": f, "recursive": False}) or []
        except Exception:
            continue
        for a in acs:
            if ue.call(A, "get_label", {"actor": a}) == label:
                _folder_cache[label] = f
                return f
    return ""


def cls_of(ue, obj):
    c = ue.call(O, "get_class", {"instance": obj})
    return c.get("refPath", c) if isinstance(c, dict) else c


def all_props(ue, obj):
    """{property: value} for every readable property of obj (chunked get_properties, per-name fallback)."""
    lp = ue.call(O, "list_properties", {"instance": obj})
    names = list(as_json(lp).keys())
    out = {}

    def read(chunk):
        try:
            r = as_json(ue.call(O, "get_properties", {"instance": obj, "properties": chunk}))
            out.update(r)
        except Exception:
            if len(chunk) == 1:
                return
            h = len(chunk) // 2
            read(chunk[:h])
            read(chunk[h:])

    for i in range(0, len(names), 60):
        read(names[i:i + 60])
    return out


def dump_actor(ue, label):
    a = find_exact(ue, label)
    path = a["refPath"]
    d = {"actor_path": path, "label": label, "folder": folder_of(ue, label)}
    d["class"] = cls_of(ue, a)
    d["transform"] = ue.call(A, "get_actor_transform", {"actor": a})
    d["actor"] = all_props(ue, a)
    d["tags"] = ue.call(A, "get_tags", {"actor": a})
    comps = {}
    for c in ue.call(A, "get_components", {"actor": a}) or []:
        cp = c["refPath"]
        name = cp.rsplit(".", 1)[-1]
        comps[name] = {"path": cp, "class": cls_of(ue, c), "props": all_props(ue, c)}
    d["components"] = comps
    try:
        d["bounds"] = ue.call(A, "get_actor_bounds", {"actor": a})
    except Exception as e:
        d["bounds"] = str(e)[:200]
    return d


# ---------------------------------------------------------------- diff
def _norm(v, internal):
    """Replace the actor's internal object name inside refPath strings so two different actors compare equal."""
    if isinstance(v, str):
        return v.replace(internal, "<ACTOR>")
    if isinstance(v, list):
        return [_norm(x, internal) for x in v]
    if isinstance(v, dict):
        return {k: _norm(x, internal) for k, x in v.items()}
    return v


def _internal(d):
    return d["actor_path"].rsplit(".", 1)[-1]


def _flat_cmp(where, pa, pb, out, ignore):
    for k in sorted(set(pa) | set(pb)):
        if k in ignore:
            continue
        if k not in pa:
            out.append((where, k, "<absent>", pb[k]))
        elif k not in pb:
            out.append((where, k, pa[k], "<absent>"))
        elif pa[k] != pb[k]:
            out.append((where, k, pa[k], pb[k]))


def diff_dumps(a, b):
    out = []
    ia, ib = _internal(a), _internal(b)
    na, nb = _norm(a, ia), _norm(b, ib)
    for k in ("class", "label", "folder", "transform", "tags"):
        if na.get(k) != nb.get(k):
            out.append(("actor", k, na.get(k), nb.get(k)))
    _flat_cmp("actor.props", na["actor"], nb["actor"], out, IGNORE_ACTOR)
    ca = {re.sub(r"^BillboardComponent_\d+$", "BillboardComponent", k): v for k, v in na["components"].items()}   # editor sprite: auto-numbered
    cb = {re.sub(r"^BillboardComponent_\d+$", "BillboardComponent", k): v for k, v in nb["components"].items()}
    for name in sorted(set(ca) | set(cb)):
        if name not in ca:
            out.append(("component " + name, "<component>", "<absent>", cb[name]["class"]))
        elif name not in cb:
            out.append(("component " + name, "<component>", ca[name]["class"], "<absent>"))
        else:
            if ca[name]["class"] != cb[name]["class"]:
                out.append(("component " + name, "<class>", ca[name]["class"], cb[name]["class"]))
            _flat_cmp("component " + name, ca[name]["props"], cb[name]["props"], out, IGNORE_ANY)
    return out


def _short(v, n=160):
    s = json.dumps(v) if not isinstance(v, str) else v
    return s if len(s) <= n else s[:n] + "..."


def cmd_diff(pa, pb, as_json_out=False):
    a, b = json.load(open(pa)), json.load(open(pb))
    d = diff_dumps(a, b)
    if as_json_out:
        print(json.dumps(d, indent=1))
    else:
        print("%s: %d difference(s) (%s vs %s)" % (a["label"], len(d), os.path.basename(pa), os.path.basename(pb)))
        for where, k, x, y in d:
            print("  [%s] %s: %s  ->  %s" % (where, k, _short(x), _short(y)))
    return 1 if d else 0


def main():
    if len(sys.argv) >= 4 and sys.argv[1] == "dump":
        ue = UE()
        d = dump_actor(ue, sys.argv[2])
        os.makedirs(os.path.dirname(os.path.abspath(sys.argv[3])), exist_ok=True)
        json.dump(d, open(sys.argv[3], "w"), indent=1)
        print("dumped %s (%s, folder %s, %d components) -> %s" % (d["label"], d["class"], d["folder"], len(d["components"]), sys.argv[3]))
        return 0
    if len(sys.argv) >= 4 and sys.argv[1] == "diff":
        return cmd_diff(sys.argv[2], sys.argv[3], "--json" in sys.argv)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
