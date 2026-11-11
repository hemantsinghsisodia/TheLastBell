using UnrealBuildTool;

// Editor-only automation tests for the LastBell module (LastBell.* test names). Kept out of the runtime module so UnrealEd
// never leaks into it, and out of every Game/Shipping target (module type Editor, listed in the Editor target only).
public class LastBellTests : ModuleRules
{
	public LastBellTests(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		// The test files keep helpers with the same names (Note, StartSession, HalfHeight...) in anonymous namespaces; a unity chunk that merges two of them
		// fails to compile, and which files share a chunk changes whenever a file is added or edited. Each test file compiles on its own.
		bUseUnity = false;

		PublicIncludePaths.Add(ModuleDirectory);

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput", "GameplayTags", "PhysicsCore", "UMG", "Slate", "SlateCore", "LastBell"
		});

		PrivateDependencyModuleNames.AddRange(new string[]
		{
			"UnrealEd", "ApplicationCore", "AIModule", "NavigationSystem", "Niagara", "LevelSequence", "MovieScene", "MovieSceneTracks"
		});
	}
}
