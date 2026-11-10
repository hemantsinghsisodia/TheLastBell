# P17-4 `M_LB_PP_MaskView` --check output

Route: one `MaterialExpressionCustom` (HLSL) node, parameters as Scalar/VectorParameter nodes feeding its named inputs. Output of `Tools/cine/p17_4_maskview.py --check` (editor open on L_Monastery, no PIE), before the save. No instruction count is available over MCP. The look is judged by the owner in P17-7.

```
PASS  /Game/LastBell/Materials/PostProcess/M_LB_PP_MaskView exists
PASS  /Game/LastBell/Materials/PostProcess/MI_LB_PP_MaskView exists
PASS  Material Domain = MD_PostProcess (read: MD_PostProcess)
PASS  Blendable Location = BL_SceneColorAfterTonemapping (read: BL_SceneColorAfterTonemapping)
INFO  bIsBlendable = True
INFO  nodes: Custom x1, ScalarParameter x13, SceneTexture x1, ScreenPosition x1, Time x1, VectorParameter x1, ViewSize x1
PASS  expression count 19 == 19
PASS  exactly one Custom (HLSL) node
PASS  no texture sample nodes (SceneTexture only)
PASS  Custom output type = CMOT_Float3
PASS  Custom HLSL code equals the script's formula (1012 chars)
PASS  Custom input names: ['SceneColor', 'ScreenUV', 'ViewSizePx', 'TimeSec', 'CenterLX', 'CenterRX', 'CenterY', 'RadiusX', 'RadiusY', 'Feather', 'NoseMinX', 'NoseMaxX', 'NoseAlpha', 'Darkness', 'EdgeTint', 'Breath', 'BreathHz', 'EdgeTintColor']
PASS  SceneTexture id = PPI_PostProcessInput0 (read: PPI_PostProcessInput0)
LINK  SceneColor     <- SceneTexture_1:Color
LINK  ScreenUV       <- ScreenPosition_1:ViewportUV
LINK  ViewSizePx     <- ViewSize_1
LINK  TimeSec        <- Time_1
LINK  CenterLX       <- ScalarParameter_1
LINK  CenterRX       <- ScalarParameter_2
LINK  CenterY        <- ScalarParameter_3
LINK  RadiusX        <- ScalarParameter_4
LINK  RadiusY        <- ScalarParameter_5
LINK  Feather        <- ScalarParameter_6
LINK  NoseMinX       <- ScalarParameter_7
LINK  NoseMaxX       <- ScalarParameter_8
LINK  NoseAlpha      <- ScalarParameter_9
LINK  Darkness       <- ScalarParameter_10
LINK  EdgeTint       <- ScalarParameter_11
LINK  Breath         <- ScalarParameter_12
LINK  BreathHz       <- ScalarParameter_13
LINK  EdgeTintColor  <- VectorParameter_1:RGBA
PASS  every Custom input is connected (18)
PASS  SceneColor <- SceneTexture:Color
PASS  ScreenUV <- ScreenPosition:ViewportUV
PASS  ViewSizePx <- ViewSize
PASS  TimeSec <- Time
PASS  ScalarParameter CenterLX default 0.4 (read 0.4000000059604645) group=MaskView
PASS  ScalarParameter CenterRX default 0.6 (read 0.6000000238418579) group=MaskView
PASS  ScalarParameter CenterY default 0.5 (read 0.5) group=MaskView
PASS  ScalarParameter RadiusX default 0.17 (read 0.17000000178813934) group=MaskView
PASS  ScalarParameter RadiusY default 0.085 (read 0.08500000089406967) group=MaskView
PASS  ScalarParameter Feather default 0.06 (read 0.05999999865889549) group=MaskView
PASS  ScalarParameter NoseMinX default 0.485 (read 0.48500001430511475) group=MaskView
PASS  ScalarParameter NoseMaxX default 0.515 (read 0.5149999856948853) group=MaskView
PASS  ScalarParameter NoseAlpha default 0.35 (read 0.3499999940395355) group=MaskView
PASS  ScalarParameter Darkness default 0.97 (read 0.9700000286102295) group=MaskView
PASS  ScalarParameter EdgeTint default 0.15 (read 0.15000000596046448) group=MaskView
PASS  ScalarParameter Breath default 0.02 (read 0.019999999552965164) group=MaskView
PASS  ScalarParameter BreathHz default 0.25 (read 0.25) group=MaskView
PASS  VectorParameter EdgeTintColor default (1.0, 0.55, 0.4, 1.0) (read [1, 0.55, 0.4, 1])
PASS  14 unique parameter names (no extras)
INFO  MP_EmissiveColor <- {"output_name": "", "expression": {"refPath": "/Game/LastBell/Materials/PostProcess/M_LB_PP_MaskView.M_LB_PP_MaskView:MaterialExpressionCustom_2"}, "input_name": ""}
PASS  Emissive Color is driven by the Custom node
PASS  MP_BaseColor unconnected (emissive only)
PASS  MP_Opacity unconnected (emissive only)
PASS  MP_OpacityMask unconnected (emissive only)
PASS  recompile clean (returned None)
PASS  MI parent = /Game/LastBell/Materials/PostProcess/M_LB_PP_MaskView.M_LB_PP_MaskView (read: /Game/LastBell/Materials/PostProcess/M_LB_PP_MaskView.M_LB_PP_MaskView)
PASS  MI has no overrides (scalar 0, vector 0, texture 0)
INFO  MI.list_parameters -> [{"type": "Scalar", "name": "CenterLX"}, {"type": "Scalar", "name": "CenterRX"}, {"type": "Scalar", "name": "CenterY"}, {"type": "Scalar", "name": "RadiusX"}, {"type": "Scalar", "name": "RadiusY"}, {"type": "Scalar", "name": "Feather"}, {"type": "Scalar", "name": "NoseMin
PASS  MI effective CenterLX = 0.4000000059604645 (expected 0.4)
PASS  MI effective CenterRX = 0.6000000238418579 (expected 0.6)
PASS  MI effective CenterY = 0.5 (expected 0.5)
PASS  MI effective RadiusX = 0.17000000178813934 (expected 0.17)
PASS  MI effective RadiusY = 0.08500000089406967 (expected 0.085)
PASS  MI effective Feather = 0.05999999865889549 (expected 0.06)
PASS  MI effective NoseMinX = 0.48500001430511475 (expected 0.485)
PASS  MI effective NoseMaxX = 0.5149999856948853 (expected 0.515)
PASS  MI effective NoseAlpha = 0.3499999940395355 (expected 0.35)
PASS  MI effective Darkness = 0.9700000286102295 (expected 0.97)
PASS  MI effective EdgeTint = 0.15000000596046448 (expected 0.15)
PASS  MI effective Breath = 0.019999999552965164 (expected 0.02)
PASS  MI effective BreathHz = 0.25 (expected 0.25)
PASS  L_Monastery is not dirty
PASS  M_LB_Surface is not dirty
PASS  BP_SmallBell is not dirty
PASS  BP_SequencePuzzle is not dirty
PASS  BP_Inscription is not dirty
PASS  BP_RitualMechanism is not dirty
PASS  BP_Door_Base is not dirty
PASS  BP_TagInteractable is not dirty
PASS  BP_TagTrigger is not dirty
PASS  BP_EndingTrigger is not dirty
PASS  BP_Inspectable_Note is not dirty
PASS  BP_Door_Base_Dungeon is not dirty
PASS  BP_RitualMechanism_CryptWinch is not dirty
PASS  BP_WardenApparition is not dirty
PASS  BP_PuzzleCandle is not dirty
INFO  LS_P17_Spike dirty = True (the lead's in-memory edits: expected, left alone)
INFO  M_LB_PP_MaskView dirty = True, MI_LB_PP_MaskView dirty = True

66 PASS, 0 FAIL
```
