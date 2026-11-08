"""P15-4: build the FX master materials, MF_LB_ClothWave and the material instances over MCP (editor open on L_Monastery, no PIE).

    python p15_4_materials.py <step> [step ...]
    steps: rain splash ripple bolt flame dust mist curtain clothfn cloth     (masters, function)
           mis                                                              (all material instances)
           check                                                            (read back MI values)
Each master step deletes the nodes of its asset first (if it exists) and rebuilds it, then recompiles.
Never saves, never calls set_parent. Spec: Docs/plans/P15_PARTICLES.md section 5.
"""
import sys, json
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\fx")
from p15_mat_lib import *

FXM = "/Game/LastBell/Materials/FX"
FXI = "/Game/LastBell/Materials/Instances/FX"
FN = "/Game/LastBell/Materials/Functions"

COL = (0.55, 0.60, 0.70)


def start(name, props_, folder=FXM):
    pkg = folder + "/" + name
    if not ue.call(AST, "exists", {"path": pkg}):
        create_material(folder, name)
    g = Graph(pkg)
    for e in exprs(g.asset):
        ue.call(MAT, "delete_expression", {"material_or_function": ref(g.asset), "expression": ref(e)})
    assert exprs(g.asset) == []
    setp(g.asset, props_)
    return g


def finish(g):
    g.layout()
    r = g.compile()
    print(g.pkg, "compile ->", r, "| nodes:", len(exprs(g.asset)))


def particle_unlit(extra=None):
    d = dict(materialDomain="MD_Surface", blendMode="BLEND_Translucent", shadingModel="MSM_Unlit",
             bUsedWithNiagaraSprites=True, twoSided=False)
    d.update(extra or {})
    return d


def cam_fade(g, pd=None):
    """PixelDepth fade: 0 at CamFadeNearCm, 1 at CamFadeFarCm (params, 40 / 120)."""
    pd = pd or g.node("PixelDepth")
    return g.ramp(pd, g.sp("CamFadeNearCm", 40, "Fade"), g.sp("CamFadeFarCm", 120, "Fade"))


def depth_fade(g, opacity, dist_param, dist_default):
    k = g.node("DepthFade")
    g.link(opacity, k, "Opacity")
    g.link(g.sp(dist_param, dist_default, "Fade"), k, "FadeDistance")
    return k


# ----------------------------------------------------------------------------- masters
def m_rain():
    g = start("M_LB_Rain", particle_unlit(dict(blendMode="BLEND_Additive", bUseTranslucencyVertexFog=True, bEnableResponsiveAA=True)))
    F = g.mpc("LightningFlash")
    inten = g.add(g.sp("RainBase", 0.035, "Storm"), g.mul(g.sp("RainFlash", 1.4, "Storm"), F))
    col = g.vp("RainColor", COL, "Look")
    pc = g.node("ParticleColor")
    streak = g.tex("StreakTex", "T_LB_FX_RainStreak", "SAMPLERTYPE_LinearColor")
    mask = g.mul(g.mul(streak + ":A", pc + ":A"), cam_fade(g))
    mask = depth_fade(g, mask, "DepthFadeCm", 30)
    # Additive: every mask is in the emissive, nothing depends on how Opacity is treated (Opacity pin left unconnected)
    emis = g.mul(g.mul(g.mul(col + ":RGB", inten), pc + ":RGB"), mask)
    g.out("MP_EmissiveColor", emis)
    finish(g)


def m_splash():
    g = start("M_LB_Splash", particle_unlit(dict(blendMode="BLEND_Additive", bUseTranslucencyVertexFog=True)))
    F = g.mpc("LightningFlash")
    inten = g.add(g.sp("SplashBase", 0.08, "Storm"), g.mul(g.sp("SplashFlash", 1.2, "Storm"), F))
    col = g.vp("SplashColor", COL, "Look")
    pc = g.node("ParticleColor")
    sub = g.node("TextureSampleParameterSubUV", parameterName="SplashTex",
                 texture=tex("T_LB_FX_Splash"), samplerType="SAMPLERTYPE_Color", group="Textures")
    emis = g.mul(g.mul(g.mul(col + ":RGB", inten), pc + ":RGB"), g.mul(sub + ":A", pc + ":A"))
    g.out("MP_EmissiveColor", emis)
    finish(g)


def m_ripple():
    g = start("M_LB_Ripple", particle_unlit(dict(blendMode="BLEND_Additive", bUseTranslucencyVertexFog=True)))
    F = g.mpc("LightningFlash")
    inten = g.add(g.sp("RippleBase", 0.05, "Storm"), g.mul(g.sp("RippleFlash", 1.0, "Storm"), F))
    col = g.vp("RippleColor", COL, "Look")
    pc = g.node("ParticleColor")
    ring = g.tex("RippleTex", "T_LB_FX_Ripple", "SAMPLERTYPE_LinearColor")
    mask = depth_fade(g, g.mul(ring + ":A", pc + ":A"), "DepthFadeCm", 4)
    emis = g.mul(g.mul(g.mul(col + ":RGB", inten), pc + ":RGB"), mask)
    g.out("MP_EmissiveColor", emis)
    finish(g)


def m_bolt():
    # additive, fogging off, two-sided; a static mesh card (SM_LB_FX_BoltCard), not a particle: no Niagara usage flag
    g = start("M_LB_Bolt", dict(materialDomain="MD_Surface", blendMode="BLEND_Additive", shadingModel="MSM_Unlit",
                                twoSided=True, bUseTranslucencyVertexFog=False, bDisableDepthTest=False))
    import os
    F = g.const(1.0) if os.environ.get("P15_BOLT_DEBUG_F1") else g.mpc("LightningFlash")  # debug only: F forced to 1 to look at the atlas cell
    tint = g.rgb(g.mpc("FlashTint"))
    idx = g.sp("AtlasIndex", 0, "Atlas")
    row = g.floor(g.div(g.add(idx, 0.25), 4.0))
    colm = g.sub(idx, g.mul(row, 4.0))
    off = g.op("AppendVector", colm, row)
    uv = g.div(g.add(g.texcoord(0), off), g.c2(4, 2))
    bolt = g.tex("BoltTex", "T_LB_FX_Bolts", "SAMPLERTYPE_Color", uvs=uv)
    # premultiplied RGB (sRGB on): use RGB directly, never RGB x A
    emis = g.mul(g.mul(g.mul(bolt + ":RGB", tint), g.sp("BoltGain", 40, "Storm")), F)
    g.out("MP_EmissiveColor", emis)
    finish(g)


def m_dust():
    g = start("M_LB_DustMote", particle_unlit(dict(blendMode="BLEND_Additive")))
    F = g.mpc("LightningFlash")
    pc = g.node("ParticleColor")
    dot = g.tex("DotTex", "T_LB_FX_SoftDot", "SAMPLERTYPE_Alpha")
    col = g.vp("DustColor", (0.55, 0.62, 0.80), "Look")
    flash = g.add(1.0, g.mul(g.sp("DustFlash", 2.0, "Storm"), F))
    e = g.mul(dot + ":R", col + ":RGB")
    e = g.mul(e, g.sp("DustBrightness", 0.6, "Look"))
    e = g.mul(e, flash)
    e = g.mul(e, cam_fade(g))
    e = g.mul(g.mul(e, pc + ":RGB"), pc + ":A")
    g.out("MP_EmissiveColor", e)
    finish(g)


def m_mist():
    g = start("M_LB_Mist", particle_unlit())
    F = g.mpc("LightningFlash")
    pc = g.node("ParticleColor")
    puff = g.tex("PuffTex", "T_LB_FX_MistPuff", "SAMPLERTYPE_Alpha")
    tint = g.vp("MistTint", (0.5, 0.55, 0.62), "Look")
    inten = g.add(g.sp("MistBase", 0.06, "Storm"), g.mul(g.sp("MistFlash", 0.5, "Storm"), F))
    emis = g.mul(g.mul(tint + ":RGB", inten), pc + ":RGB")
    op = g.mul(g.mul(puff + ":R", g.sp("MistOpacity", 0.08, "Look")), pc + ":A")
    op = depth_fade(g, op, "DepthFadeCm", 60)
    g.out("MP_EmissiveColor", emis)
    g.out("MP_Opacity", op)
    finish(g)


def m_curtain():
    g = start("M_LB_RainCurtain", dict(materialDomain="MD_Surface", blendMode="BLEND_Additive", shadingModel="MSM_Unlit",
                                      twoSided=True))
    F = g.mpc("LightningFlash")
    wind = g.mpc("WindStrength")
    tc = g.texcoord(0)
    tu, tv = g.ch(tc, "r"), g.ch(tc, "g")
    t = g.node("Time")
    skew = g.mul(g.mul(tv, g.sp("WindSkew", 1.0, "Motion")), wind)
    u = g.add(g.mul(tu, g.sp("TilingU", 6, "Motion")), skew)
    v = g.sub(g.mul(tv, g.sp("TilingV", 1, "Motion")), g.mul(t, g.sp("PanSpeed", 1.2, "Motion")))
    streak = g.tex("StreakTex", "T_LB_FX_RainStreak", "SAMPLERTYPE_LinearColor", uvs=g.op("AppendVector", u, v))
    wp = g.node("WorldPosition")
    dist = g.op("Distance", wp + ":XYZ", g.node("CameraPositionWS"))
    fade = g.ramp(dist, g.sp("FadeNearCm", 0, "Fade"), g.sp("FadeFarCm", 3000, "Fade"))
    inten = g.add(g.sp("CurtainBase", 0.02, "Storm"), g.mul(g.sp("CurtainFlash", 1.6, "Storm"), F))
    col = g.vp("CurtainColor", COL, "Look")
    g.out("MP_EmissiveColor", g.mul(g.mul(col + ":RGB", inten), g.mul(streak + ":A", fade)))
    finish(g)


def m_flame():
    # additive; sprite + mesh. bSprite (static) picks UV-based height / mask for particles vs local height for the lathed mesh.
    g = start("M_LB_Flame", particle_unlit(dict(blendMode="BLEND_Additive", maxWorldPositionOffsetDisplacement=5.0)))
    bS = g.node("StaticBoolParameter", parameterName="bSprite", defaultValue=False, group="Mode")
    t = g.node("Time")
    pc = g.node("ParticleColor")
    uv = g.texcoord(0)
    uvx, uvy = g.ch(uv, "r"), g.ch(uv, "g")

    def sw(true_k, false_k):
        k = g.node("StaticSwitch")
        g.link(bS, k, "Value")
        g.link(true_k, k, "True")
        g.link(false_k, k, "False")
        return k

    # height h: 0 at the base, 1 at the tip
    lb = g.node("ObjectLocalBounds")
    lz = g.ch(g.node("LocalPosition"), "b")
    bmin = g.ch(lb + ":Min", "b")
    bext = g.ch(lb + ":Extents", "b")
    h_mesh = g.sat(g.div(g.sub(lz, bmin), g.op("Max", bext, 0.001)))
    h_sprite = g.one_minus(uvy)
    h = sw(h_sprite, h_mesh)

    # per-instance random: ParticleRandom for sprites, a hash of the object position for the placed meshes
    rnd_s = g.node("ParticleRandom")
    objp = g.node("ObjectPositionWS")
    dotp = g.op("DotProduct", objp, g.c3(12.9898, 78.233, 45.164))
    rnd_m = g.frac(g.mul(g.sine(dotp), 43758.5453))
    rnd = sw(rnd_s, rnd_m)

    # noise distortion, panning up at NoiseSpeed
    ntile = g.sp("NoiseTiling", 1.0, "Noise")
    nu = g.add(g.mul(uvx, ntile), rnd)
    nv = g.sub(g.mul(h, ntile), g.mul(t, g.sp("NoiseSpeed", 1.0, "Noise")))
    noise = g.tex("NoiseTex", "T_LB_FX_Noise", "SAMPLERTYPE_Masks", uvs=g.op("AppendVector", nu, nv))
    dist = g.sp("DistortAmount", 0.12, "Noise")
    hd = g.add(h, g.mul(g.sub(noise + ":R", 0.5), dist))
    tt = g.sat(hd)

    # colour ramp over the (distorted) height: core -> mid -> outer
    core = g.vp("ColorCore", (1.0, 0.95, 0.8), "Ramp")
    mid = g.vp("ColorMid", (1.0, 0.55, 0.15), "Ramp")
    outer = g.vp("ColorOuter", (0.6, 0.12, 0.02), "Ramp")
    a = g.lerp(core + ":RGB", mid + ":RGB", g.sat(g.mul(tt, 2.0)))
    ramp = g.lerp(a, outer + ":RGB", g.sat(g.sub(g.mul(tt, 2.0), 1.0)))

    # shape: sprite = teardrop from UV (x distorted by noise G); mesh = geometry, edges softened by Fresnel
    xs = g.add(g.mul(g.sub(uvx, 0.5), 2.0), g.mul(g.sub(noise + ":G", 0.5), g.mul(dist, 2.0)))
    xs = g.mul(xs, g.add(1.0, g.mul(g.sub(hd, 0.38), 1.2)))
    d2 = g.op("AppendVector", g.div(xs, 0.85), g.div(g.sub(hd, 0.45), 0.5))
    sm = g.node("Power")
    g.link(g.sat(g.one_minus(g.length(d2))), sm, "Base")
    g.link(g.sp("ShapePower", 2.0, "Look"), sm, "Exp")
    sprite_mask = sm
    fres = g.node("Fresnel", exponent=2.0)
    mesh_mask = g.one_minus(g.mul(fres, 0.7))
    shape = sw(sprite_mask, mesh_mask)

    # flicker: 0.85 + 0.3 * noise(time * FlickerSpeed + random)
    fx = g.add(g.mul(g.mul(t, g.sp("FlickerSpeed", 8.0, "Flicker")), g.sp("FlickerNoiseScale", 0.05, "Flicker")), rnd)
    fn = g.tex("FlickerTex", "T_LB_FX_Noise", "SAMPLERTYPE_Masks", uvs=g.op("AppendVector", fx, g.add(g.mul(rnd, 0.7), 0.1)))
    flick = g.add(0.85, g.mul(fn + ":R", 0.3))

    e = g.mul(ramp, shape)
    e = g.mul(e, g.sp("EmissiveStrength", 8.0, "Look"))
    e = g.mul(e, flick)
    e = g.mul(g.mul(e, pc + ":RGB"), pc + ":A")
    g.out("MP_EmissiveColor", e)

    # WPO sway (meshes only): world height of the object * SwayAmount * h * sin, two phases (x, y)
    world_h = g.ch(g.node("ObjectBounds"), "b")
    ph = g.add(g.mul(t, g.sp("SwaySpeed", 3.0, "Flicker")), g.mul(rnd, TWO_PI))
    sx = g.sine(ph)
    sy = g.sine(g.add(g.mul(ph, 0.73), 1.7))
    vec = g.op("AppendVector", g.op("AppendVector", sx, sy), g.const(0.0))
    amt = g.mul(g.mul(h_mesh, world_h), g.sp("SwayAmount", 0.15, "Flicker"))
    wpo = g.mul(vec, amt)
    k = g.node("StaticSwitch")
    g.link(bS, k, "Value")
    g.link(g.c3(0, 0, 0), k, "True")
    g.link(wpo, k, "False")
    g.out("MP_WorldPositionOffset", k)
    finish(g)


# ----------------------------------------------------------------------------- function and cloth
def mf_clothwave():
    pkg = FN + "/MF_LB_ClothWave"
    if not ue.call(AST, "exists", {"path": pkg}):
        ue.call(MAT, "create_function", {"folder_path": FN, "asset_name": "MF_LB_ClothWave"})
    g = Graph(pkg)
    for e in exprs(g.asset):
        ue.call(MAT, "delete_expression", {"material_or_function": ref(g.asset), "expression": ref(e)})
    setp(g.asset, {"bExposeToLibrary": True, "libraryCategoriesText": ["LastBell"],
                   "description": "Cloth sway WPO. Pinned at UV0.y = 0 (pin = v^1.5), a travelling wave down the length, plus a whip along the vertex normal. Driven by MPC_LB_Storm WindStrength, WindPhase, WindDirection. Exactly (0,0,0) at WindStrength 0."})

    def fin(name, default, desc, prio):
        return g.node("FunctionInput", inputName=name, inputType="FunctionInput_Scalar",
                      previewValue={"x": default, "y": 0, "z": 0, "w": 0}, bUsePreviewValueAsDefault=True,
                      sortPriority=prio, desc=desc)

    amp = fin("AmplitudeCm", 35, "Peak sway in cm at WindStrength 1", 0)
    wl = fin("WavelengthCm", 120, "Wavelength of the travelling wave, cm", 1)
    ps = fin("PhaseScale", 2.5, "WindPhase multiplier", 2)
    wh = fin("WhipAmount", 0.25, "Flap along the vertex normal, fraction of the main sway", 3)
    ln = fin("LengthCm", 200, "Cloth length (mesh height) in cm", 4)
    ws, wph, wdir = g.mpc("WindStrength"), g.mpc("WindPhase"), g.mpc("WindDirection")
    v = g.sat(g.ch(g.texcoord(0), "g"))
    pin = g.power(v, 1.5)
    phi = g.sub(g.mul(wph, ps), g.mul(g.div(g.mul(v, ln), wl), TWO_PI))
    main_s = g.add(g.mul(g.sine(phi), 0.4), 0.6)
    wx = g.ch(g.node("WorldPosition") + ":XYZ", "r")
    flap_s = g.sine(g.add(g.mul(phi, 3.0), g.mul(wx, 0.01)))
    # main = dir * WindStrength * (0.6 + 0.4 sin) * pin * Amp
    m = g.mul(g.rgb(wdir), ws)
    m = g.mul(m, main_s)
    m = g.mul(m, pin)
    m = g.mul(m, amp)
    # flap = N * sin(3 phi + x*0.01) * Whip * WindStrength * pin * Amp
    f = g.mul(g.node("VertexNormalWS"), flap_s)
    f = g.mul(f, wh)
    f = g.mul(f, ws)
    f = g.mul(f, pin)
    f = g.mul(f, amp)
    o = g.node("FunctionOutput", outputName="WPO")
    g.link(g.add(m, f), o, "")
    finish(g)


def m_cloth():
    g = start("M_LB_Cloth", dict(materialDomain="MD_Surface", blendMode="BLEND_Opaque", shadingModel="MSM_DefaultLit",
                                 twoSided=True, maxWorldPositionOffsetDisplacement=60.0))
    wd = g.sp("ClothWidthCm", 35, "Mesh")
    ln = g.sp("ClothLengthCm", 220, "Mesh")
    # texture scale: one tile per TextureTileCm of cloth
    uvs = g.mul(g.texcoord(0), g.div(g.op("AppendVector", wd, ln), g.sp("TextureTileCm", 40, "Fabric")))
    base = g.tex("BaseColorTex", "Cloth/T_LB_Cloth_Hessian_BaseColor", "SAMPLERTYPE_Color", uvs=uvs)
    nrm = g.tex("NormalTex", "Cloth/T_LB_Cloth_Hessian_Normal", "SAMPLERTYPE_Normal", uvs=uvs)
    rgh = g.tex("RoughnessTex", "Cloth/T_LB_Cloth_Hessian_Roughness", "SAMPLERTYPE_Masks", uvs=uvs)
    ao = g.tex("AOTex", "Cloth/T_LB_Cloth_Hessian_AO", "SAMPLERTYPE_Masks", uvs=uvs)
    tint = g.vp("Tint", (1.0, 1.0, 1.0), "Fabric")
    g.out("MP_BaseColor", g.mul(base + ":RGB", tint + ":RGB"))
    g.out("MP_Normal", nrm + ":RGB")
    g.out("MP_Roughness", rgh + ":R")
    g.out("MP_AmbientOcclusion", g.lerp(1.0, ao + ":R", g.sp("AOStrength", 1.0, "Fabric")))
    fc = g.node("MaterialFunctionCall", materialFunction=ref(FN + "/MF_LB_ClothWave.MF_LB_ClothWave"))
    print("MF inputs", g.inputs(fc), "outputs", g.outputs(fc))
    g.link(g.sp("AmplitudeCm", 35, "Wind"), fc, "AmplitudeCm")
    g.link(g.sp("WavelengthCm", 120, "Wind"), fc, "WavelengthCm")
    g.link(g.sp("PhaseScale", 2.5, "Wind"), fc, "PhaseScale")
    g.link(g.sp("WhipAmount", 0.25, "Wind"), fc, "WhipAmount")
    g.link(ln, fc, "LengthCm")
    g.out("MP_WorldPositionOffset", fc + ":WPO")
    finish(g)


STEPS = dict(rain=m_rain, splash=m_splash, ripple=m_ripple, bolt=m_bolt, dust=m_dust, mist=m_mist, curtain=m_curtain,
             flame=m_flame, clothfn=mf_clothwave, cloth=m_cloth)

if __name__ == "__main__":
    for s in [a for a in sys.argv[1:] if a in STEPS]:
        print("=== step", s)
        STEPS[s]()


# ----------------------------------------------------------------------------- material instances
RC = (0.55, 0.60, 0.70, 1.0)
CAM = {"CamFadeNearCm": 40, "CamFadeFarCm": 120}
MIS = {
    "MI_LB_Rain": ("M_LB_Rain", dict(RainBase=0.035, RainFlash=1.4, DepthFadeCm=30, **CAM), dict(RainColor=RC), {}),
    "MI_LB_Splash": ("M_LB_Splash", dict(SplashBase=0.08, SplashFlash=1.2), dict(SplashColor=RC), {}),
    "MI_LB_Ripple": ("M_LB_Ripple", dict(RippleBase=0.05, RippleFlash=1.0, DepthFadeCm=4), dict(RippleColor=RC), {}),
    "MI_LB_Bolt": ("M_LB_Bolt", dict(BoltGain=40, AtlasIndex=0), {}, {}),
    "MI_Flame_Candle": ("M_LB_Flame", dict(NoiseSpeed=0.6, FlickerSpeed=7, EmissiveStrength=8), {}, dict(bSprite=False)),
    "MI_Flame_Torch": ("M_LB_Flame", dict(NoiseSpeed=1.4, FlickerSpeed=11, EmissiveStrength=12), {}, dict(bSprite=True)),
    "MI_LB_DustMote": ("M_LB_DustMote", dict(DustBrightness=0.6, DustFlash=2.0, **CAM), dict(DustColor=(0.55, 0.62, 0.80, 1.0)), {}),
    "MI_LB_Mist": ("M_LB_Mist", dict(MistBase=0.06, MistFlash=0.5, MistOpacity=0.08, DepthFadeCm=60), dict(MistTint=(0.5, 0.55, 0.62, 1.0)), {}),
    "MI_LB_WaterMist": ("M_LB_Mist", dict(MistBase=0.06, MistFlash=0.5, MistOpacity=0.08, DepthFadeCm=60), dict(MistTint=(0.5, 0.55, 0.62, 1.0)), {}),
    "MI_LB_RainCurtain": ("M_LB_RainCurtain", dict(CurtainBase=0.02, CurtainFlash=1.6, TilingU=6, TilingV=1, PanSpeed=1.2, WindSkew=1.0,
                                                  FadeNearCm=0, FadeFarCm=3000), dict(CurtainColor=RC), {}),
    "MI_Cloth_Linen_Dark": ("M_LB_Cloth", dict(AmplitudeCm=30, WavelengthCm=120, PhaseScale=2.5, WhipAmount=0.25, ClothWidthCm=35, ClothLengthCm=220),
                            dict(Tint=(0.20, 0.18, 0.16, 1.0)), {}),
    "MI_Cloth_Linen_Dark_Sheet": ("M_LB_Cloth", dict(AmplitudeCm=20, WavelengthCm=120, PhaseScale=2.5, WhipAmount=0.25, ClothWidthCm=170, ClothLengthCm=140),
                                  dict(Tint=(0.20, 0.18, 0.16, 1.0)), {}),
    "MI_Cloth_Linen_Red": ("M_LB_Cloth", dict(AmplitudeCm=25, WavelengthCm=120, PhaseScale=2.5, WhipAmount=0.25, ClothWidthCm=110, ClothLengthCm=240),
                           dict(Tint=(0.35, 0.08, 0.06, 1.0)), {}),
}


def make_mis(only=None):
    for name, (parent, sc, vc, st) in MIS.items():
        if only and name not in only:
            continue
        pkg = FXI + "/" + name
        o = objpath(pkg)
        if not ue.call(AST, "exists", {"path": pkg}):
            ue.call(MI, "create", {"folder_path": FXI, "asset_name": name, "parent": ref(objpath(FXM + "/" + parent))})
        for k, v in sc.items():
            assert ue.call(MI, "set_scalar_parameter", {"instance": ref(o), "name": k, "value": float(v)}) is not False, (name, k)
        for k, v in vc.items():
            ue.call(MI, "set_vector_parameter", {"instance": ref(o), "name": k, "value": dict(zip("rgba", v))})
        for k, v in st.items():
            ue.call(MI, "set_static_switch_parameter", {"instance": ref(o), "name": k, "value": v})
        print("made", name)


def check_mis(only=None):
    ok = True
    for name, (parent, sc, vc, st) in MIS.items():
        if only and name not in only:
            continue
        pkg = FXI + "/" + name
        c = mi_compact(pkg)
        good = c["parent"] == objpath(FXM + "/" + parent)
        for k, v in sc.items():
            good &= abs(c["scalars"].get(k, 1e9) - v) < 1e-5
        for k, v in vc.items():
            good &= all(abs(a - b) < 1e-5 for a, b in zip(c["vectors"].get(k, [9] * 4), v))
        sts = {}
        for k, v in st.items():
            sts[k] = ue.call(MI, "get_static_switch_parameter", {"instance": ref(objpath(pkg)), "name": k})
            good &= (sts[k] == v) if not isinstance(sts[k], dict) else True
        print("OK " if good else "BAD", name, c["parent"].rsplit(".", 1)[-1], json.dumps(c["scalars"]), json.dumps(c["vectors"]), sts)
        ok &= good
    print("ALL OK" if ok else "SOME BAD")


if __name__ == "__main__" and sys.argv[1:2] == ["mis"]:
    make_mis()
if __name__ == "__main__" and sys.argv[1:2] == ["check"]:
    check_mis()
