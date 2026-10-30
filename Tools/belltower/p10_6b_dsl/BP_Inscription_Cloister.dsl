(fn ConstructionScript ()
  (bind _plaque (Variables|Default|GetPlaque))
  (bind _engraving (Variables|Default|GetEngraving))
  ; Plaque = M4 inscription tablet (slot 0 MAT_Trim); pivot at its back centre, front faces +x. D1.11 erratum 3: relative X -2
  (Components|StaticMesh|SetStaticMesh _plaque "/Game/LastBell/Environments/Cloister/Meshes/SM_LB_Prop_InscriptionTablet_A.SM_LB_Prop_InscriptionTablet_A")
  (Transformation|SetRelativeLocation _plaque (Math|Vector|MakeVector -2.0 0.0 0.0))
  (Transformation|SetRelativeScale3D _plaque (Math|Vector|MakeVector 1.0 1.0 1.0))
  (Rendering|Material|SetMaterial _plaque 0 "/Game/LastBell/Environments/Kit/Materials/MI_Kit_Trim.MI_Kit_Trim")
  ; Engraving colour (20, 18, 15, 255); relative location is kept from the parent (x 2.2, in front of the tablet face at x +2)
  (Rendering|Components|TextRender|SetTextRenderColor _engraving (Utilities|Struct|MakeColor :R 20 :G 18 :B 15 :A 255))
  ; copy of BP_Inscription's construction script: Engraving text = Text with '|' replaced by a line break
  (Rendering|Components|TextRender|SetText _engraving (Utilities|Text|ToText(String) (Utilities|String|Replace (Variables|Default|GetText) "|" "
"))))
