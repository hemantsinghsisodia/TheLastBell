import sys
sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\crypt\r1b")
from h import *
spec = {"L_Crypt_Moon_G1":{"bCastVolumetricShadow":False,"volumetricScatteringIntensity":0.5},
        "L_Crypt_Moon_G2":{"bCastVolumetricShadow":False,"volumetricScatteringIntensity":0.5},
        "L_Crypt_Torch_T1":{"volumetricScatteringIntensity":0.5},
        "L_Crypt_Torch_T2":{"volumetricScatteringIntensity":0.5},
        "L_Crypt_Torch_T3":{"volumetricScatteringIntensity":0.5}}
for lbl,v in spec.items():
    a=find_label(lbl,world="editor"); assert len(a)==1
    comp={"refPath":a[0]["refPath"]+".LightComponent0"}
    setp(comp,v)
    print(lbl, props(comp,list(v.keys())))
