#include "Storm/LBLightningBolt.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

const FName ALBLightningBolt::AtlasParameterName(TEXT("AtlasIndex"));

ALBLightningBolt::ALBLightningBolt()
{
	PrimaryActorTick.bCanEverTick = false;
	SetCanBeDamaged(false);

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("BoltMesh"));
	SetRootComponent(Mesh);
	Mesh->SetMobility(EComponentMobility::Movable);
	Mesh->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
	Mesh->SetGenerateOverlapEvents(false);
	Mesh->SetCanEverAffectNavigation(false);
	Mesh->SetCastShadow(false);
	Mesh->bCastDynamicShadow = false;
	Mesh->bAffectDynamicIndirectLighting = false;
	Mesh->bAffectDistanceFieldLighting = false;
	Mesh->bRenderCustomDepth = false;
	Mesh->bReceivesDecals = false;

	SetActorHiddenInGame(true);
}

void ALBLightningBolt::SetAssets(UStaticMesh* InMesh, UMaterialInterface* InMaterial)
{
	if (InMesh && Mesh->GetStaticMesh() != InMesh)
	{
		Mesh->SetStaticMesh(InMesh);
	}
	if (InMaterial != SourceMaterial)
	{
		SourceMaterial = InMaterial;
		Dynamic = nullptr;
	}
}

void ALBLightningBolt::SetBolt(const FTransform& Transform, int32 AtlasIndex)
{
	SetActorTransform(Transform, false, nullptr, ETeleportType::TeleportPhysics);
	Atlas = AtlasIndex;
	if (!SourceMaterial)
	{
		return;
	}
	if (!Dynamic)
	{
		Dynamic = UMaterialInstanceDynamic::Create(SourceMaterial, this);
		Mesh->SetMaterial(0, Dynamic);
	}
	if (Dynamic)
	{
		Dynamic->SetScalarParameterValue(AtlasParameterName, static_cast<float>(AtlasIndex));
	}
}

void ALBLightningBolt::ShowBolt(double Now)
{
	bShown = true;
	ShownAt = Now;
	SetActorHiddenInGame(false);
}

void ALBLightningBolt::HideBolt()
{
	bShown = false;
	SetActorHiddenInGame(true);
}

FVector ALBLightningBolt::GetBoltBottom() const
{
	return GetActorTransform().TransformPosition(FVector(0.0, 0.0, -100.0));
}
