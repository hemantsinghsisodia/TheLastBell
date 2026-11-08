"""Save the P15-4 assets one package per call, then check is_dirty. Guards: the map and M_LB_Surface must stay clean."""
import sys, time
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\fx")
from p15_mat_lib import *
MAP = "/Game/LastBell/Maps/L_Monastery"; SURF = "/Game/LastBell/Materials/Master/M_LB_Surface"
FXM = "/Game/LastBell/Materials/FX/"; FXI = "/Game/LastBell/Materials/Instances/FX/"
pk = [FXM + n for n in ["M_LB_Rain", "M_LB_Splash", "M_LB_Ripple", "M_LB_Bolt", "M_LB_Flame", "M_LB_DustMote", "M_LB_Mist", "M_LB_RainCurtain", "M_LB_Cloth"]]
pk += ["/Game/LastBell/Materials/Functions/MF_LB_ClothWave"]
pk += [FXI + n for n in ["MI_LB_Rain", "MI_LB_Splash", "MI_LB_Ripple", "MI_LB_Bolt", "MI_Flame_Candle", "MI_Flame_Torch", "MI_LB_DustMote", "MI_LB_Mist", "MI_LB_WaterMist", "MI_LB_RainCurtain", "MI_Cloth_Linen_Dark", "MI_Cloth_Linen_Dark_Sheet", "MI_Cloth_Linen_Red"]]
pk += ["/Game/LastBell/FX/Meshes/" + n for n in ["SM_LB_Prop_ClothStrip_A", "SM_LB_Prop_ClothStrip_B", "SM_LB_Prop_ClothSheet_A", "SM_LB_Prop_ClothBanner_A", "SM_LB_FX_BoltCard", "SM_LB_FX_CurtainCard"]]
only = sys.argv[1:] 
for p in pk:
    if only and p.rsplit("/", 1)[-1] not in only: continue
    assert not dirty(MAP) and not dirty(SURF), "STOP: map or surface dirty"
    t = time.time()
    r = ue.call(AST, "save_assets", {"asset_paths": [p]})
    d = dirty(p)
    print(p.rsplit("/", 1)[-1], "saved", r, "dirty after:", d, "%.1fs" % (time.time() - t), flush=True)
    assert d is False, p
print("map dirty", dirty(MAP), "surface dirty", dirty(SURF))
