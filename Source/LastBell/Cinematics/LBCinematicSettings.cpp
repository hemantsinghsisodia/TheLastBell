#include "Cinematics/LBCinematicSettings.h"

const FLBCinematicDef* ULBCinematicSettings::FindDef(FName Id) const
{
	return Cinematics.FindByPredicate([Id](const FLBCinematicDef& Def) { return Def.Id == Id; });
}

const FLBCineCard* ULBCinematicSettings::FindCard(FName Id) const
{
	return Cards.Find(Id);
}
