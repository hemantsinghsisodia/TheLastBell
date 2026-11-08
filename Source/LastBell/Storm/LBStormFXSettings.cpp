#include "Storm/LBStormFXSettings.h"

ULBStormFXSettings::ULBStormFXSettings()
{
	// Plan P15 section 2.2.
	SkyBoltChance.Add(ELBFlashReason::Ambient, 0.6f);
	SkyBoltChance.Add(ELBFlashReason::Scripted, 1.0f);
	SkyBoltChance.Add(ELBFlashReason::WardenReveal, 0.5f);
	SkyBoltChance.Add(ELBFlashReason::Apparition, 0.5f);
	SkyBoltChance.Add(ELBFlashReason::Debug, 1.0f);
}
