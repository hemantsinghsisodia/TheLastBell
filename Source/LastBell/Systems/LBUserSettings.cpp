#include "Systems/LBUserSettings.h"

void ULBUserSettings::SetMouseSensitivity(float NewValue)
{
	MouseSensitivity = FMath::Clamp(NewValue, MinSensitivity, MaxSensitivity);
	SaveConfig();
}

void ULBUserSettings::SetInvertY(bool bNewValue)
{
	bInvertY = bNewValue;
	SaveConfig();
}

void ULBUserSettings::SetHeadBob(bool bNewValue)
{
	bHeadBob = bNewValue;
	SaveConfig();
}
