using UnrealBuildTool;
using System.Collections.Generic;

public class TheLastBellEditorTarget : TargetRules
{
	public TheLastBellEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("LastBell");
	}
}
