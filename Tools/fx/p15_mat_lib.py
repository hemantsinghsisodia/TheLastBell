"""Small material-graph builder over MCP for the P15-4 FX materials (editor open).

    g = Graph("/Game/LastBell/Materials/FX/M_LB_Rain")          # existing empty Material or MaterialFunction
    a = g.sp("RainBase", 0.035, "Look")                          # ScalarParameter -> key
    b = g.op("Multiply", a, 2.0)                                 # numbers become constA/constB
    g.out("MP_EmissiveColor", b)

A "key" is a string "nN" or "nN:Output". Every helper returns a key. Nothing here calls set_parent or saves.
"""
import json, sys
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\lighting")
from p14_lib import ue, ref, OBJ, AST, MAT, MI, setp, props, jl, dirty, exprs, mi_compact, objpath

TWO_PI = 6.283185307179586
MPC = ref("/Game/LastBell/Materials/MPC_LB_Storm.MPC_LB_Storm")
TEX = "/Game/LastBell/FX/Textures/"

# input pin name and "const" property for the binary ops
_BIN = {
    "Multiply": ("A", "B", "constA", "constB"),
    "Add": ("A", "B", "constA", "constB"),
    "Subtract": ("A", "B", "constA", "constB"),
    "Divide": ("A", "B", "constA", "constB"),
    "Fmod": ("A", "B", None, None),
    "DotProduct": ("A", "B", None, None),
    "Distance": ("A", "B", None, None),
    "AppendVector": ("A", "B", None, None),
    "Min": ("A", "B", "constA", "constB"),
    "Max": ("A", "B", "constA", "constB"),
}


class Graph:
    def __init__(self, asset_pkg):
        self.pkg = asset_pkg
        self.asset = asset_pkg + "." + asset_pkg.rsplit("/", 1)[1]
        self.n = {}
        self.i = 0
        self.x = 0
        self.y = 0

    # ---- low level
    def _ref(self, key):
        name, _, out = key.partition(":")
        return self.n[name], out

    def node(self, cls, **p):
        self.i += 1
        name = "n%d" % self.i
        self.x += 200
        if self.x > 3000:
            self.x = 0
            self.y += 220
        e = ue.call(MAT, "add_expression", {"material_or_function": ref(self.asset),
                                            "expression_class": ref("/Script/Engine.MaterialExpression" + cls),
                                            "x": self.x, "y": self.y})["refPath"]
        self.n[name] = e
        if p:
            setp(e, p)
        return name

    def link(self, src, dst, pin=""):
        s, out = self._ref(src)
        d, _ = self._ref(dst)
        ue.call(MAT, "connect_expressions", {"from_expression": ref(s), "from_output_name": out,
                                             "to_expression": ref(d), "to_input_name": pin})

    def out(self, prop, src):
        s, out = self._ref(src)
        ue.call(MAT, "connect_to_output", {"expression": ref(s), "output_name": out, "material_property": prop})

    def set(self, key, **p):
        setp(self.n[key.partition(":")[0]], p)

    def inputs(self, key):
        return ue.call(MAT, "get_expression_input_names", {"expression": ref(self.n[key.partition(":")[0]])})

    def outputs(self, key):
        return ue.call(MAT, "get_expression_output_names", {"expression": ref(self.n[key.partition(":")[0]])})

    # ---- ops
    def op(self, cls, x, y=None, **p):
        """Binary op (numbers become constants) or unary op (y None, pin ''). Returns the key."""
        if cls in _BIN:
            pa, pb, ca, cb = _BIN[cls]
            k = self.node(cls, **p)
            for v, pin, cn in ((x, pa, ca), (y, pb, cb)):
                if isinstance(v, str):
                    self.link(v, k, pin)
                else:
                    if cn is None:
                        raise ValueError("%s needs a node on %s" % (cls, pin))
                    self.set(k, **{cn: float(v)})
            return k
        k = self.node(cls, **p)
        self.link(x, k, "")
        return k

    def mul(self, a, b): return self.op("Multiply", a, b)
    def add(self, a, b): return self.op("Add", a, b)
    def sub(self, a, b): return self.op("Subtract", a, b)
    def div(self, a, b): return self.op("Divide", a, b)
    def sat(self, a): return self.op("Saturate", a)
    def frac(self, a): return self.op("Frac", a)
    def floor(self, a): return self.op("Floor", a)
    def one_minus(self, a): return self.op("OneMinus", a)
    def length(self, a): return self.op("Length", a)
    def sine(self, a): return self.op("Sine", a, period=TWO_PI)

    def lerp(self, a, b, alpha):
        k = self.node("LinearInterpolate")
        for v, pin, cn in ((a, "A", "constA"), (b, "B", "constB"), (alpha, "Alpha", "constAlpha")):
            if isinstance(v, str):
                self.link(v, k, pin)
            else:
                self.set(k, **{cn: float(v)})
        return k

    def power(self, base, exp):
        k = self.node("Power", constExponent=float(exp))
        self.link(base, k, "Base")
        return k

    def mask(self, a, r=False, g=False, b=False, a_=False):
        return self.op("ComponentMask", a, r=r, g=g, b=b, a=a_)

    def rgb(self, a): return self.mask(a, True, True, True)
    def ch(self, a, c):
        return self.mask(a, c == "r", c == "g", c == "b", c == "a")

    def const(self, v): return self.node("Constant", r=float(v))
    def c2(self, x, y): return self.node("Constant2Vector", r=float(x), g=float(y))
    def c3(self, x, y, z): return self.node("Constant3Vector", constant={"r": x, "g": y, "b": z, "a": 1.0})

    # ---- parameters / sources
    def sp(self, name, default, group="Look"):
        return self.node("ScalarParameter", parameterName=name, defaultValue=float(default), group=group)

    def vp(self, name, rgba, group="Look"):
        r, g, b = rgba[:3]
        a = rgba[3] if len(rgba) > 3 else 1.0
        return self.node("VectorParameter", parameterName=name, defaultValue={"r": r, "g": g, "b": b, "a": a}, group=group)

    def mpc(self, name):
        return self.node("CollectionParameter", collection=MPC, parameterName=name)

    def tex(self, name, tex_path, sampler, uvs=None, group="Textures"):
        k = self.node("TextureSampleParameter2D", parameterName=name, texture=ref(TEX + tex_path + "." + tex_path.rsplit("/", 1)[-1]),
                      samplerType=sampler, group=group)
        if uvs:
            self.link(uvs, k, "UVs")
        return k

    def texcoord(self, idx=0):
        return self.node("TextureCoordinate", coordinateIndex=idx)

    def compile(self):
        return ue.call(MAT, "recompile", {"material_or_function": ref(self.asset)})

    def layout(self):
        try:
            ue.call(MAT, "layout_expressions", {"material_or_function": ref(self.asset)})
        except Exception as ex:
            print("layout failed (cosmetic):", str(ex)[:100])

    def ramp(self, x, lo, hi):
        """saturate((x - lo) / (hi - lo)); lo/hi keys or numbers."""
        num = self.sub(x, lo)
        den = self.sub(hi, lo) if (isinstance(hi, str) or isinstance(lo, str)) else self.const(hi - lo)
        return self.sat(self.div(num, den))


def create_material(folder, name):
    return ue.call(MAT, "create_material", {"folder_path": folder, "asset_name": name})


def tex(path_in_textures):
    return ref(TEX + path_in_textures + "." + path_in_textures.rsplit("/", 1)[-1])
