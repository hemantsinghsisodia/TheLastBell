(fn ConstructionScript ()
  ; ===== copy of BP_TagInteractable's construction script =====
  (bind _interactcomp (Variables|Default|GetInteractComp))
  (bind _usestatetag (Variables|Default|GetUseStateTag))
  (bind _mesh (Variables|Default|GetMesh))
  (CallFunction|ApplyInspectSettings)
  (if (GameplayTags|IsGameplayTagValid _usestatetag)
    (Class|LBInteractableComponent|SetGrantedStateTags (GameplayTags|MakeGameplayTagContainerFromTag _usestatetag) _interactcomp)
    (Class|LBInteractableComponent|SetConsumedStateTag _usestatetag _interactcomp)
    (Class|LBInteractableComponent|SetSingleUse true _interactcomp))
  ; ===== great bell art (D1.17 s5): mesh T12 + every slot set explicitly; collision unchanged (1 hull) =====
  ; NOTE: Mesh is the ROOT component of BP_TagInteractable, so the spec's relative location (0,0,94) / scale 0.4 cannot be applied here
  ; (they would be the actor transform). See the P10-6b report.
  (Components|StaticMesh|SetStaticMesh _mesh "/Game/LastBell/Environments/BellTower/Meshes/SM_LB_Prop_GreatBell_A.SM_LB_Prop_GreatBell_A")
  ; slots: 0 MAT_Bronze, 1 MAT_Iron
  (Rendering|Material|SetMaterial _mesh 0 "/Game/LastBell/Environments/BellTower/Materials/MI_LB_BellBronze.MI_LB_BellBronze")
  (Rendering|Material|SetMaterial _mesh 1 "/Game/LastBell/Environments/Crypt/Materials/MI_Crypt_Iron.MI_Crypt_Iron"))
