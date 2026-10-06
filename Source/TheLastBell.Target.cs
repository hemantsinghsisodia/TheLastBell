using UnrealBuildTool;
using System.Collections.Generic;

public class TheLastBellTarget : TargetRules
{
	public TheLastBellTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("LastBell");
	}
}
