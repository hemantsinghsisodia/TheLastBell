using UnrealBuildTool;

// Editor-only automation tests for the LastBell module (LastBell.* test names). Kept out of the runtime module so UnrealEd
// never leaks into it, and out of every Game/Shipping target (module type Editor, listed in the Editor target only).
public class LastBellTests : ModuleRules
{
	public LastBellTests(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicIncludePaths.Add(ModuleDirectory);

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput", "GameplayTags", "PhysicsCore", "LastBell"
		});

		PrivateDependencyModuleNames.AddRange(new string[]
		{
			"UnrealEd", "ApplicationCore"
		});
	}
}
