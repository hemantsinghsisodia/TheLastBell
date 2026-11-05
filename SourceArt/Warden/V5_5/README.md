# Warden V5.5 posture and face update

Use the V5.5 mesh and its three V5.5 animation clips together. The native assets are under /Game/WardenArtV5_5 and reference the existing V5 skeleton, V5.1 garment materials and physics asset, and V5.4 skin material.

The idle projects the shoulders and head forward and brings the hands inward. The stoop lifts the face within the hood and retains the lowered doorway pose. The walk has a 1.6 cm pelvis lift. The hood opening and the eye slit geometry are smoothed.

## Import settings

Import SK_Warden_LOD0.fbx as a skeletal mesh with Force Front X Axis enabled, scene/unit conversion enabled, scale 1, and the existing V5 skeleton selected. Disable Update Skeleton Reference Pose and Use T0 As Ref Pose. Import normals and tangents. Add the other two mesh FBXs as LODs.

Import the three supplied animation FBXs onto that skeleton with scene/unit conversion enabled, scale 1 and custom sample rate 30. Use exported duration. The animation FBXs include a root orientation correction for the animation-only importer in Unreal 5.8. Use the supplied clips with the supplied mesh import settings. Set any previous actor/component workaround for the 90 degree discrepancy back to the intended character heading.

The animation clips last 4 seconds (idle), 2 seconds (walk), and 3 seconds (stoop). The review previews use the actual native assets in the isolated WardenAssetValidation project.

The deepest stoop measures approximately 219.5 cm on LOD0 and 219.7 cm on LOD2, leaving over 4 cm below the 224 cm doorway. The walk's lowest mesh point is approximately 3 mm above the floor. The hunch brings the idle hood height to approximately 286 cm. The 110 mesh reference-bone transforms match the existing V5 skeleton exactly.

The previews/blender folder contains neutral-lit views for judging the face opening and the pose independently of the darker Unreal presentation.
