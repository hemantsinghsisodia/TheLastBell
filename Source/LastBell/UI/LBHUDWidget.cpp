#include "UI/LBHUDWidget.h"
#include "Blueprint/WidgetTree.h"
#include "Character/LBCandleComponent.h"
#include "Character/LBCharacter.h"
#include "Character/LBInspectionComponent.h"
#include "Components/Border.h"
#include "Components/BorderSlot.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Image.h"
#include "Components/LBInspectableComponent.h"
#include "Components/LBInteractableComponent.h"
#include "Components/LBInteractorComponent.h"
#include "Components/TextBlock.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Objectives/LBObjectiveSubsystem.h"
#include "Systems/LBUserSettings.h"
#include "UI/LBKeyIconWidget.h"
#include "UI/LBUIBuild.h"
#include "UI/LBUIStyle.h"

namespace
{
	constexpr float CrosshairRestOpacity = 0.35f;
	constexpr float CrosshairFocusOpacity = 0.9f;
	constexpr float CrosshairFocusScale = 1.8f;
	constexpr float CrosshairSpeed = 8.f;
	constexpr float BindRetrySeconds = 0.25f;
	constexpr float VignetteSize = 70.f;
	const FLinearColor VignetteColour(0.f, 0.f, 0.f, 0.35f);
	const FLinearColor InspectInk(0.93f, 0.87f, 0.72f, 1.f);

	UCanvasPanelSlot* Place(UCanvasPanel& Canvas, UWidget* Child, const FAnchors& Anchors, const FMargin& Offsets, const FVector2D& Alignment, bool bAutoSize)
	{
		UCanvasPanelSlot* PanelSlot = Canvas.AddChildToCanvas(Child);
		if (PanelSlot)
		{
			PanelSlot->SetAnchors(Anchors);
			PanelSlot->SetOffsets(Offsets);
			PanelSlot->SetAlignment(Alignment);
			PanelSlot->SetAutoSize(bAutoSize);
		}
		return PanelSlot;
	}

	void Shadow(UTextBlock& Text, float Alpha)
	{
		Text.SetShadowOffset(FVector2D(1.0, 1.0));
		Text.SetShadowColorAndOpacity(FLinearColor(0.f, 0.f, 0.f, Alpha));
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------------------------------------------------

void ULBHUDWidget::NativeOnInitialized()
{
	Super::NativeOnInitialized();
	BuildTree();
	BindSettings();
	ApplyLook();
	// Bind at once when the pawn and the objectives already exist (headless runs and -nullrhi do not tick widgets); otherwise the pawn-change
	// notification and the tick pick it up.
	BindController();
	TryBind();
}

void ULBHUDWidget::NativeConstruct()
{
	Super::NativeConstruct();
	BindSettings();
	BindController();
}

void ULBHUDWidget::NativeDestruct()
{
	UnbindController();
	UnbindPawn();
	UnbindObjective();
	UnbindSettings();
	Super::NativeDestruct();
}

void ULBHUDWidget::BeginDestroy()
{
	UnbindController();
	UnbindPawn();
	UnbindObjective();
	UnbindSettings();
	Super::BeginDestroy();
}

void ULBHUDWidget::BindController()
{
	APlayerController* PC = GetOwningPlayer();
	if (PC && BoundController.Get() != PC)
	{
		UnbindController();
		BoundController = PC;
		PC->OnPossessedPawnChanged.AddUniqueDynamic(this, &ULBHUDWidget::HandlePossessedPawnChanged);
	}
}

void ULBHUDWidget::UnbindController()
{
	if (APlayerController* PC = BoundController.Get())
	{
		PC->OnPossessedPawnChanged.RemoveDynamic(this, &ULBHUDWidget::HandlePossessedPawnChanged);
	}
	BoundController.Reset();
}

void ULBHUDWidget::HandlePossessedPawnChanged(APawn* OldPawn, APawn* NewPawn)
{
	TryBind();
}

void ULBHUDWidget::BindSettings()
{
	if (!SettingsHandle.IsValid())
	{
		SettingsHandle = ULBUserSettings::OnUserSettingsChanged().AddUObject(this, &ULBHUDWidget::HandleSettingsChanged);
	}
}

void ULBHUDWidget::UnbindSettings()
{
	if (SettingsHandle.IsValid())
	{
		ULBUserSettings::OnUserSettingsChanged().Remove(SettingsHandle);
		SettingsHandle.Reset();
	}
}

void ULBHUDWidget::HandleSettingsChanged()
{
	ApplyLook();
}

void ULBHUDWidget::BuildTree()
{
	if (Root || !WidgetTree)
	{
		return;
	}
	Root = WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(), TEXT("Root"));
	WidgetTree->RootWidget = Root;

	// The crosshair: a 4 px dot at the centre, dim until something can be used.
	Crosshair = WidgetTree->ConstructWidget<UImage>(UImage::StaticClass(), TEXT("Crosshair"));
	Crosshair->SetBrush(LBUIBuild::SolidBrush(FLinearColor::White));
	Crosshair->SetRenderOpacity(CrosshairRestOpacity);
	Crosshair->SetVisibility(ESlateVisibility::HitTestInvisible);
	if (UCanvasPanelSlot* PanelSlot = Place(*Root, Crosshair, FAnchors(0.5f, 0.5f), FMargin(0.f, 0.f, 4.f, 4.f), FVector2D(0.5, 0.5), false))
	{
		PanelSlot->SetZOrder(0);
	}

	// The prompt: [key] text, a little below the crosshair, on a plate that only shows in high-contrast mode.
	PromptPlate = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("PromptPlate"));
	PromptPlate->SetPadding(FMargin(14.f, 6.f));
	PromptPlate->SetVisibility(ESlateVisibility::Collapsed);
	PromptRow = WidgetTree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass(), TEXT("PromptRow"));
	PromptPlate->SetContent(PromptRow);

	PromptKey = WidgetTree->ConstructWidget<ULBKeyIconWidget>(ULBKeyIconWidget::StaticClass(), TEXT("PromptKey"));
	PromptKey->SetPlayerContext(GetPlayerContext());
	PromptKey->SetGlyphHeight(34.f);
	PromptKey->SetBoundAction(ELBBindAction::Interact);
	if (UHorizontalBoxSlot* KeySlot = PromptRow->AddChildToHorizontalBox(PromptKey))
	{
		KeySlot->SetVerticalAlignment(VAlign_Center);
		KeySlot->SetPadding(FMargin(0.f, 0.f, 12.f, 0.f));
	}
	PromptText = LBUIBuild::MakeText(*WidgetTree, FText::GetEmpty(), FSlateFontInfo(), FLinearColor::White, ETextJustify::Center);
	Shadow(*PromptText, 0.7f);
	if (UHorizontalBoxSlot* TextSlot = PromptRow->AddChildToHorizontalBox(PromptText))
	{
		TextSlot->SetVerticalAlignment(VAlign_Center);
	}
	Place(*Root, PromptPlate, FAnchors(0.5f, 0.58f), FMargin(), FVector2D(0.5, 0.0), true);

	// The objective: top left.
	ObjectiveText = LBUIBuild::MakeText(*WidgetTree, FText::GetEmpty(), FSlateFontInfo(), FLinearColor::White, ETextJustify::Left);
	Shadow(*ObjectiveText, 0.7f);
	ObjectiveText->SetVisibility(ESlateVisibility::Collapsed);
	Place(*Root, ObjectiveText, FAnchors(0.f, 0.f), FMargin(40.f, 40.f, 0.f, 0.f), FVector2D(0.0, 0.0), true);

	// "Lighting..." while the candle is relit: bottom centre.
	CandleText = LBUIBuild::MakeText(*WidgetTree, NSLOCTEXT("LastBellUI", "CandleLighting", "Lighting…"), FSlateFontInfo(), FLinearColor::White, ETextJustify::Center);
	Shadow(*CandleText, 0.7f);
	CandleText->SetVisibility(ESlateVisibility::Collapsed);
	Place(*Root, CandleText, FAnchors(0.5f, 1.f), FMargin(0.f, -70.f, 0.f, 0.f), FVector2D(0.5, 1.0), true);

	// The inspection overlay: four vignette bands, the item's name at the top, its text on the right, the hint at the bottom.
	InspectOverlay = WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(), TEXT("InspectOverlay"));
	InspectOverlay->SetVisibility(ESlateVisibility::Collapsed);
	Place(*Root, InspectOverlay, FAnchors(0.f, 0.f, 1.f, 1.f), FMargin(), FVector2D(0.0, 0.0), false);

	auto AddBand = [this](const TCHAR* Name, const FAnchors& Anchors, const FMargin& Offsets)
	{
		UBorder* Band = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), Name);
		Band->SetBrush(LBUIBuild::SolidBrush(VignetteColour));
		Band->SetVisibility(ESlateVisibility::HitTestInvisible);
		Place(*InspectOverlay, Band, Anchors, Offsets, FVector2D(0.0, 0.0), false);
	};
	AddBand(TEXT("VigTop"), FAnchors(0.f, 0.f, 1.f, 0.f), FMargin(0.f, 0.f, 0.f, VignetteSize));
	AddBand(TEXT("VigBottom"), FAnchors(0.f, 1.f, 1.f, 1.f), FMargin(0.f, -VignetteSize, 0.f, VignetteSize));
	AddBand(TEXT("VigLeft"), FAnchors(0.f, 0.f, 0.f, 1.f), FMargin(0.f, 0.f, VignetteSize, 0.f));
	AddBand(TEXT("VigRight"), FAnchors(1.f, 0.f, 1.f, 1.f), FMargin(-VignetteSize, 0.f, VignetteSize, 0.f));

	InspectName = LBUIBuild::MakeText(*WidgetTree, FText::GetEmpty(), FSlateFontInfo(), InspectInk, ETextJustify::Center);
	Shadow(*InspectName, 0.8f);
	InspectName->SetVisibility(ESlateVisibility::HitTestInvisible);
	Place(*InspectOverlay, InspectName, FAnchors(0.5f, 0.f), FMargin(0.f, 60.f, 0.f, 0.f), FVector2D(0.5, 0.0), true);

	InspectBodyPanel = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("BodyPanel"));
	InspectBodyPanel->SetPadding(FMargin(24.f, 20.f));
	InspectBodyPanel->SetVisibility(ESlateVisibility::Collapsed);
	InspectBody = LBUIBuild::MakeText(*WidgetTree, FText::GetEmpty(), FSlateFontInfo(), InspectInk, ETextJustify::Left);
	InspectBody->SetAutoWrapText(true);
	InspectBody->SetWrapTextAt(380.f);
	InspectBodyPanel->SetContent(InspectBody);
	Place(*InspectOverlay, InspectBodyPanel, FAnchors(0.66f, 0.5f, 0.97f, 0.5f), FMargin(), FVector2D(0.0, 0.5), true);

	InspectHint = WidgetTree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass(), TEXT("InspectHint"));
	InspectHint->SetVisibility(ESlateVisibility::HitTestInvisible);
	Place(*InspectOverlay, InspectHint, FAnchors(0.5f, 1.f), FMargin(0.f, -50.f, 0.f, 0.f), FVector2D(0.5, 1.0), true);

	SetVisibility(ESlateVisibility::SelfHitTestInvisible);
}

void ULBHUDWidget::ApplyLook()
{
	if (!Root)
	{
		return;
	}
	const ULBUIStyle& Style = *ULBUIStyle::Resolve();
	const ULBUserSettings* User = ULBUserSettings::Get();
	bPromptHighContrast = User && User->bHighContrastPrompts;
	const FLBPromptLook Look = Style.GetPromptLook(bPromptHighContrast);

	Crosshair->SetColorAndOpacity(Style.Ink);

	// The prompt.
	FSlateFontInfo PromptFont = Style.MakeFont(ELBFontWeight::SemiBold, Style.BodySize);
	if (bPromptHighContrast)
	{
		PromptFont = LBUIBuild::WithOutline(PromptFont, Look.OutlineSize, Look.Outline);
		PromptPlate->SetBrush(LBUIBuild::RoundedBrush(Look.Plate, 8.f, Look.Text, 2.f));
	}
	else
	{
		PromptPlate->SetBrush(LBUIBuild::SolidBrush(FLinearColor(0.f, 0.f, 0.f, 0.f)));
	}
	PromptText->SetFont(PromptFont);
	PromptText->SetColorAndOpacity(FSlateColor(Look.Text));
	PromptText->SetShadowColorAndOpacity(FLinearColor(0.f, 0.f, 0.f, bPromptHighContrast ? 0.f : 0.7f));

	// The rest.
	ObjectiveText->SetFont(Style.MakeFont(ELBFontWeight::Regular, Style.SmallSize + 4));
	ObjectiveText->SetColorAndOpacity(FSlateColor(FLinearColor(Style.Ink.R * 0.92f, Style.Ink.G * 0.92f, Style.Ink.B * 0.92f, 1.f)));
	CandleText->SetFont(Style.MakeFont(ELBFontWeight::Italic, Style.SmallSize));
	CandleText->SetColorAndOpacity(FSlateColor(FLinearColor(Style.Accent.R, Style.Accent.G, Style.Accent.B, 0.9f)));
	InspectName->SetFont(Style.MakeFont(ELBFontWeight::SemiBold, Style.ItemSize));
	InspectName->SetColorAndOpacity(FSlateColor(InspectInk));
	InspectBody->SetFont(Style.MakeFont(ELBFontWeight::Regular, Style.SmallSize + 2));
	InspectBody->SetColorAndOpacity(FSlateColor(InspectInk));
	InspectBodyPanel->SetBrush(LBUIBuild::SolidBrush(FLinearColor(0.02f, 0.02f, 0.02f, 0.78f)));

	// The inspection hint: "Drag to rotate - [E] / [RMB] to close". Rebuilt here so it follows the style.
	InspectHint->ClearChildren();
	const FSlateFontInfo HintFont = Style.MakeFont(ELBFontWeight::Italic, Style.SmallSize);
	const FLinearColor HintColour(0.75f, 0.75f, 0.75f, 0.8f);
	auto AddHintText = [this, &HintFont, &HintColour](const FText& Text)
	{
		UTextBlock* Block = LBUIBuild::MakeText(*WidgetTree, Text, HintFont, HintColour, ETextJustify::Center);
		Shadow(*Block, 0.8f);
		if (UHorizontalBoxSlot* BoxSlot = InspectHint->AddChildToHorizontalBox(Block))
		{
			BoxSlot->SetVerticalAlignment(VAlign_Center);
			BoxSlot->SetPadding(FMargin(6.f, 0.f));
		}
	};
	auto AddHintKey = [this, &Style](const FKey* Fixed)
	{
		ULBKeyIconWidget* Key = WidgetTree->ConstructWidget<ULBKeyIconWidget>(ULBKeyIconWidget::StaticClass());
		Key->SetPlayerContext(GetPlayerContext());
		Key->SetGlyphHeight(static_cast<float>(Style.SmallSize) * 1.6f);
		if (Fixed)
		{
			Key->SetKey(*Fixed);
		}
		else
		{
			Key->SetBoundAction(ELBBindAction::Interact);
		}
		if (UHorizontalBoxSlot* BoxSlot = InspectHint->AddChildToHorizontalBox(Key))
		{
			BoxSlot->SetVerticalAlignment(VAlign_Center);
		}
	};
	AddHintText(NSLOCTEXT("LastBellUI", "InspectDrag", "Drag to rotate ·"));
	AddHintKey(nullptr);
	AddHintText(NSLOCTEXT("LastBellUI", "InspectOr", "/"));
	const FKey RightMouse = EKeys::RightMouseButton;
	AddHintKey(&RightMouse);
	AddHintText(NSLOCTEXT("LastBellUI", "InspectClose", "to close"));

	RefreshPromptVisibility();
}

// ---------------------------------------------------------------------------------------------------------------------
// Binding to the game
// ---------------------------------------------------------------------------------------------------------------------

void ULBHUDWidget::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	Super::NativeTick(MyGeometry, InDeltaTime);

	// The pawn may not exist yet when the controller creates the HUD, and a respawn gives a new one: look again until bound, and when it changes.
	BindRetryClock += InDeltaTime;
	const bool bPawnChanged = Cast<ALBCharacter>(GetOwningPlayerPawn()) != BoundPawn.Get();
	if (bPawnChanged || (!bBound && BindRetryClock >= BindRetrySeconds))
	{
		BindRetryClock = 0.f;
		TryBind();
	}

	// The crosshair eases toward its target.
	if (!FMath::IsNearlyEqual(FocusAlpha, FocusTarget))
	{
		FocusAlpha = FMath::FInterpConstantTo(FocusAlpha, FocusTarget, InDeltaTime, CrosshairSpeed);
		Crosshair->SetRenderOpacity(FMath::Lerp(CrosshairRestOpacity, CrosshairFocusOpacity, FocusAlpha));
		Crosshair->SetRenderScale(FVector2D(FMath::Lerp(1.f, CrosshairFocusScale, FocusAlpha)));
	}
}

void ULBHUDWidget::TryBind()
{
	ALBCharacter* Pawn = Cast<ALBCharacter>(GetOwningPlayerPawn());
	if (Pawn != BoundPawn.Get())
	{
		UnbindPawn();
		if (Pawn)
		{
			BindPawn(Pawn);
		}
	}
	if (!BoundObjectives.IsValid())
	{
		BindObjective();
	}
	bBound = BoundPawn.IsValid() && BoundObjectives.IsValid();
}

void ULBHUDWidget::BindPawn(ALBCharacter* Pawn)
{
	BoundPawn = Pawn;
	if (ULBInteractorComponent* Interactor = Pawn->GetInteractor())
	{
		BoundInteractor = Interactor;
		Interactor->OnFocusChanged.AddUniqueDynamic(this, &ULBHUDWidget::HandleFocusChanged);
	}
	if (ULBCandleComponent* Candle = Pawn->GetCandle())
	{
		BoundCandle = Candle;
		Candle->OnCandleStateChanged.AddUniqueDynamic(this, &ULBHUDWidget::HandleCandleStateChanged);
		Candle->OnRelightStarted.AddUniqueDynamic(this, &ULBHUDWidget::HandleRelightStarted);
	}
	if (ULBInspectionComponent* Inspection = Pawn->GetInspection())
	{
		BoundInspection = Inspection;
		Inspection->OnInspectBegin.AddUniqueDynamic(this, &ULBHUDWidget::HandleInspectBegin);
		Inspection->OnInspectEnd.AddUniqueDynamic(this, &ULBHUDWidget::HandleInspectEnd);
	}
}

void ULBHUDWidget::UnbindPawn()
{
	if (ULBInteractorComponent* Interactor = BoundInteractor.Get())
	{
		Interactor->OnFocusChanged.RemoveDynamic(this, &ULBHUDWidget::HandleFocusChanged);
	}
	if (ULBCandleComponent* Candle = BoundCandle.Get())
	{
		Candle->OnCandleStateChanged.RemoveDynamic(this, &ULBHUDWidget::HandleCandleStateChanged);
		Candle->OnRelightStarted.RemoveDynamic(this, &ULBHUDWidget::HandleRelightStarted);
	}
	if (ULBInspectionComponent* Inspection = BoundInspection.Get())
	{
		Inspection->OnInspectBegin.RemoveDynamic(this, &ULBHUDWidget::HandleInspectBegin);
		Inspection->OnInspectEnd.RemoveDynamic(this, &ULBHUDWidget::HandleInspectEnd);
	}
	BoundPawn.Reset();
	BoundInteractor.Reset();
	BoundCandle.Reset();
	BoundInspection.Reset();
	bBound = false;
}

void ULBHUDWidget::BindObjective()
{
	const UWorld* World = GetWorld();
	if (ULBObjectiveSubsystem* Objectives = World ? World->GetSubsystem<ULBObjectiveSubsystem>() : nullptr)
	{
		BoundObjectives = Objectives;
		Objectives->OnObjectiveChanged.AddUniqueDynamic(this, &ULBHUDWidget::HandleObjectiveChanged);
		HandleObjectiveChanged(Objectives->GetActiveIndex(), Objectives->GetActiveObjectiveText());
	}
}

void ULBHUDWidget::UnbindObjective()
{
	if (ULBObjectiveSubsystem* Objectives = BoundObjectives.Get())
	{
		Objectives->OnObjectiveChanged.RemoveDynamic(this, &ULBHUDWidget::HandleObjectiveChanged);
	}
	BoundObjectives.Reset();
}

// ---------------------------------------------------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------------------------------------------------

void ULBHUDWidget::SetFocusTarget(bool bFocused)
{
	FocusTarget = bFocused ? 1.f : 0.f;
}

void ULBHUDWidget::RefreshPromptVisibility()
{
	if (!PromptPlate || !PromptKey)
	{
		return;
	}
	const bool bHasText = !PromptText->GetText().IsEmpty();
	PromptPlate->SetVisibility(bHasText && !bInspecting ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
	// A denied prompt ("Locked") names no key: pressing it does nothing.
	PromptKey->SetVisibility(bPromptUsable ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
	Crosshair->SetVisibility(bInspecting ? ESlateVisibility::Collapsed : ESlateVisibility::HitTestInvisible);
}

void ULBHUDWidget::HandleFocusChanged(ULBInteractableComponent* NewFocus, FText Prompt)
{
	if (!PromptText)
	{
		return;
	}
	// The interactor sends the denied text when the component cannot be used right now; it is the component's own PromptText otherwise.
	bPromptUsable = !(NewFocus && !Prompt.IsEmpty() && !Prompt.EqualTo(NewFocus->PromptText));
	PromptText->SetText(Prompt);
	SetFocusTarget(NewFocus != nullptr && !Prompt.IsEmpty());
	RefreshPromptVisibility();
}

void ULBHUDWidget::HandleObjectiveChanged(int32 Index, FText Text)
{
	if (!ObjectiveText)
	{
		return;
	}
	ObjectiveText->SetText(Text);
	ObjectiveText->SetVisibility(Text.IsEmpty() ? ESlateVisibility::Collapsed : ESlateVisibility::HitTestInvisible);
}

void ULBHUDWidget::HandleCandleStateChanged(bool bLit)
{
	if (CandleText)
	{
		// Lit or snuffed, the relight message is over.
		CandleText->SetVisibility(ESlateVisibility::Collapsed);
	}
}

void ULBHUDWidget::HandleRelightStarted()
{
	if (CandleText)
	{
		CandleText->SetVisibility(ESlateVisibility::HitTestInvisible);
	}
}

void ULBHUDWidget::HandleInspectBegin(ULBInspectableComponent* Inspectable)
{
	if (!InspectOverlay)
	{
		return;
	}
	bInspecting = true;
	const FText Name = Inspectable ? Inspectable->DisplayName : FText::GetEmpty();
	const FText Body = Inspectable ? Inspectable->BodyText : FText::GetEmpty();
	InspectName->SetText(Name);
	InspectName->SetVisibility(Name.IsEmpty() ? ESlateVisibility::Collapsed : ESlateVisibility::HitTestInvisible);
	InspectBody->SetText(Body);
	InspectBodyPanel->SetVisibility(Body.IsEmpty() ? ESlateVisibility::Collapsed : ESlateVisibility::HitTestInvisible);
	InspectOverlay->SetVisibility(ESlateVisibility::HitTestInvisible);
	RefreshPromptVisibility();
}

void ULBHUDWidget::HandleInspectEnd(bool bKept)
{
	if (!InspectOverlay)
	{
		return;
	}
	bInspecting = false;
	InspectOverlay->SetVisibility(ESlateVisibility::Collapsed);
	RefreshPromptVisibility();
}

// ---------------------------------------------------------------------------------------------------------------------
// Test access
// ---------------------------------------------------------------------------------------------------------------------

FText ULBHUDWidget::GetPromptTextForTest() const { return PromptText ? PromptText->GetText() : FText::GetEmpty(); }
bool ULBHUDWidget::IsPromptVisibleForTest() const { return PromptPlate && PromptPlate->GetVisibility() != ESlateVisibility::Collapsed; }
bool ULBHUDWidget::IsPromptKeyVisibleForTest() const { return IsPromptVisibleForTest() && PromptKey && PromptKey->GetVisibility() != ESlateVisibility::Collapsed; }
FText ULBHUDWidget::GetObjectiveTextForTest() const { return ObjectiveText ? ObjectiveText->GetText() : FText::GetEmpty(); }
bool ULBHUDWidget::IsObjectiveVisibleForTest() const { return ObjectiveText && ObjectiveText->GetVisibility() != ESlateVisibility::Collapsed; }
bool ULBHUDWidget::IsCandleTextVisibleForTest() const { return CandleText && CandleText->GetVisibility() != ESlateVisibility::Collapsed; }
bool ULBHUDWidget::IsInspectOverlayVisibleForTest() const { return InspectOverlay && InspectOverlay->GetVisibility() != ESlateVisibility::Collapsed; }
FText ULBHUDWidget::GetInspectNameForTest() const { return InspectName ? InspectName->GetText() : FText::GetEmpty(); }
FText ULBHUDWidget::GetInspectBodyForTest() const { return InspectBody ? InspectBody->GetText() : FText::GetEmpty(); }
bool ULBHUDWidget::IsCrosshairVisibleForTest() const { return Crosshair && Crosshair->GetVisibility() != ESlateVisibility::Collapsed; }
