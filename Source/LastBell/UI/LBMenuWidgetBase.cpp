#include "UI/LBMenuWidgetBase.h"
#include "Blueprint/WidgetTree.h"
#include "Brushes/SlateNoResource.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/LocalPlayer.h"
#include "Input/Events.h"
#include "UI/LBKeyIconWidget.h"
#include "UI/LBUIBuild.h"
#include "UI/LBUILogic.h"
#include "UI/LBUISubsystem.h"

namespace
{
	constexpr float ValueColumnWidth = 380.f;
	constexpr float SliderWidth = 300.f;
	constexpr float SliderValueWidth = 90.f;

	FLinearColor Scaled(const FLinearColor& Colour, float Factor)
	{
		return FLinearColor(Colour.R * Factor, Colour.G * Factor, Colour.B * Factor, Colour.A);
	}
}

ULBMenuButton::ULBMenuButton()
{
	InitIsFocusable(false);
}

TSharedRef<SWidget> ULBMenuButton::RebuildWidget()
{
	TSharedRef<SWidget> Result = Super::RebuildWidget();
	if (MyButton.IsValid())
	{
		MyButton->SetOnClicked(FOnClicked::CreateWeakLambda(this, [this]()
		{
			if (OnClickNative)
			{
				OnClickNative();
			}
			return FReply::Handled();
		}));
		MyButton->SetOnHovered(FSimpleDelegate::CreateWeakLambda(this, [this]()
		{
			if (OnHoverNative)
			{
				OnHoverNative();
			}
		}));
	}
	return Result;
}

void ULBSliderProxy::HandleValueChanged(float NewValue)
{
	if (OnValueNative)
	{
		OnValueNative(NewValue);
	}
}

void ULBSliderProxy::HandleCaptureEnd()
{
	if (OnCaptureEndNative)
	{
		OnCaptureEndNative();
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------------------------------------------------

void ULBMenuWidgetBase::NativeOnInitialized()
{
	Super::NativeOnInitialized();
	BuildBase();
}

void ULBMenuWidgetBase::BuildBase()
{
	if (bBuilt || !WidgetTree)
	{
		return;
	}
	bBuilt = true;

	Root = WidgetTree->ConstructWidget<UOverlay>(UOverlay::StaticClass(), TEXT("Root"));
	WidgetTree->RootWidget = Root;

	Backdrop = WidgetTree->ConstructWidget<UImage>(UImage::StaticClass(), TEXT("Backdrop"));
	Backdrop->SetBrush(LBUIBuild::SolidBrush(FLinearColor::White));
	Backdrop->SetColorAndOpacity(FLinearColor(0.f, 0.f, 0.f, 0.f));
	if (UOverlaySlot* BackdropSlot = Root->AddChildToOverlay(Backdrop))
	{
		BackdropSlot->SetHorizontalAlignment(HAlign_Fill);
		BackdropSlot->SetVerticalAlignment(VAlign_Fill);
	}

	BuildScreen(*Root);

	// The screen takes the keys; its rows are non-focusable buttons.
	SetIsFocusable(true);
}

void ULBMenuWidgetBase::NativeConstruct()
{
	Super::NativeConstruct();
	if (SelectedIndex == INDEX_NONE)
	{
		MoveSelection(1);
	}
}

void ULBMenuWidgetBase::NativeDestruct()
{
	Super::NativeDestruct();
}

const ULBUIStyle& ULBMenuWidgetBase::GetStyle() const
{
	return *ULBUIStyle::Resolve();
}

ULBUISubsystem* ULBMenuWidgetBase::GetUI() const
{
	if (const ULocalPlayer* LocalPlayer = GetOwningLocalPlayer())
	{
		return LocalPlayer->GetSubsystem<ULBUISubsystem>();
	}
	return ULBUISubsystem::Get(this);
}

void ULBMenuWidgetBase::PlaySound(ELBUISound Sound) const
{
	if (const ULBUISubsystem* UI = GetUI())
	{
		UI->PlaySound(Sound);
	}
}

bool ULBMenuWidgetBase::HandleBack()
{
	PlaySound(ELBUISound::Back);
	if (ULBUISubsystem* UI = GetUI())
	{
		if (UI->GetTopWidget() == this)
		{
			UI->PopScreen();
			return true;
		}
	}
	RemoveFromParent();
	return true;
}

UTextBlock* ULBMenuWidgetBase::MakeLabel(const FText& Text, ELBFontWeight Weight, int32 Size, const FLinearColor& Colour, ETextJustify::Type Justify)
{
	return LBUIBuild::MakeText(*WidgetTree, Text, GetStyle().MakeFont(Weight, Size), Colour, Justify);
}

// ---------------------------------------------------------------------------------------------------------------------
// Rows
// ---------------------------------------------------------------------------------------------------------------------

FLBMenuItem& ULBMenuWidgetBase::NewRow(UPanelWidget& Parent, ELBMenuItemKind Kind, const FText& Label, UHorizontalBox*& OutRow)
{
	const ULBUIStyle& Style = GetStyle();
	const int32 Size = RowTextSize > 0 ? RowTextSize : Style.ItemSize;
	const int32 Index = Items.AddDefaulted();
	FLBMenuItem& Item = Items[Index];
	Item.Kind = Kind;

	Item.Button = WidgetTree->ConstructWidget<ULBMenuButton>(ULBMenuButton::StaticClass());
	FButtonStyle ButtonStyle;
	ButtonStyle.SetNormal(FSlateNoResource());
	ButtonStyle.SetHovered(FSlateNoResource());
	ButtonStyle.SetPressed(FSlateNoResource());
	ButtonStyle.SetDisabled(FSlateNoResource());
	ButtonStyle.SetNormalPadding(FMargin(0.f));
	ButtonStyle.SetPressedPadding(FMargin(0.f));
	Item.Button->SetStyle(ButtonStyle);
	Item.Button->OnClickNative = [this, Index]() { HandleRowClicked(Index); };
	Item.Button->OnHoverNative = [this, Index]() { HandleRowHovered(Index); };

	OutRow = WidgetTree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
	Item.Button->SetContent(OutRow);

	// The candle marker: a thin amber bar that shows on the selected row.
	Item.Marker = WidgetTree->ConstructWidget<UImage>(UImage::StaticClass());
	Item.Marker->SetBrush(LBUIBuild::SolidBrush(FLinearColor::White));
	Item.Marker->SetDesiredSizeOverride(FVector2D(4.0, static_cast<double>(Size)));
	Item.Marker->SetColorAndOpacity(Style.Accent);
	Item.Marker->SetVisibility(ESlateVisibility::Hidden);
	if (UHorizontalBoxSlot* MarkerSlot = OutRow->AddChildToHorizontalBox(Item.Marker))
	{
		MarkerSlot->SetVerticalAlignment(VAlign_Center);
		MarkerSlot->SetPadding(FMargin(0.f, 0.f, 14.f, 0.f));
	}

	Item.Label = MakeLabel(Label, ELBFontWeight::Regular, Size, Scaled(Style.Ink, 0.85f));
	if (UHorizontalBoxSlot* LabelSlot = OutRow->AddChildToHorizontalBox(Item.Label))
	{
		LabelSlot->SetVerticalAlignment(VAlign_Center);
		LabelSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
	}

	if (UPanelSlot* RowSlot = Parent.AddChild(Item.Button))
	{
		if (UVerticalBoxSlot* BoxSlot = Cast<UVerticalBoxSlot>(RowSlot))
		{
			BoxSlot->SetPadding(FMargin(0.f, 5.f));
		}
	}
	return Item;
}

int32 ULBMenuWidgetBase::AddButtonItem(UPanelWidget& Parent, const FText& Label, TFunction<void()> OnActivate, bool bDanger)
{
	UHorizontalBox* Row = nullptr;
	FLBMenuItem& Item = NewRow(Parent, ELBMenuItemKind::Button, Label, Row);
	Item.bDanger = bDanger;
	Item.OnActivate = MoveTemp(OnActivate);
	const int32 Index = Items.Num() - 1;
	ApplyItemVisuals(Index, 1.f);
	return Index;
}

int32 ULBMenuWidgetBase::AddToggleItem(UPanelWidget& Parent, const FText& Label, bool bInitial, TFunction<void(bool)> OnChanged)
{
	UHorizontalBox* Row = nullptr;
	FLBMenuItem& Item = NewRow(Parent, ELBMenuItemKind::Toggle, Label, Row);
	Item.Options = { NSLOCTEXT("LastBellUI", "Off", "Off"), NSLOCTEXT("LastBellUI", "On", "On") };
	Item.Index = bInitial ? 1 : 0;
	Item.OnChoose = [Callback = MoveTemp(OnChanged)](int32 NewIndex) { if (Callback) { Callback(NewIndex != 0); } };

	const ULBUIStyle& Style = GetStyle();
	const int32 Size = RowTextSize > 0 ? RowTextSize : Style.ItemSize;
	Item.ValueText = MakeLabel(Item.Options[Item.Index], ELBFontWeight::Regular, Size, Style.Dim, ETextJustify::Right);
	USizeBox* Box = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
	Box->SetWidthOverride(ValueColumnWidth);
	Box->AddChild(Item.ValueText);
	if (UHorizontalBoxSlot* ValueSlot = Row->AddChildToHorizontalBox(Box))
	{
		ValueSlot->SetVerticalAlignment(VAlign_Center);
		ValueSlot->SetHorizontalAlignment(HAlign_Right);
	}
	const int32 Index = Items.Num() - 1;
	ApplyItemVisuals(Index, 1.f);
	return Index;
}

int32 ULBMenuWidgetBase::AddChoiceItem(UPanelWidget& Parent, const FText& Label, const TArray<FText>& Options, int32 Initial, TFunction<void(int32)> OnChanged, int32 SelectableCount)
{
	UHorizontalBox* Row = nullptr;
	FLBMenuItem& Item = NewRow(Parent, ELBMenuItemKind::Choice, Label, Row);
	Item.Options = Options;
	Item.Index = Options.IsEmpty() ? 0 : FMath::Clamp(Initial, 0, Options.Num() - 1);
	Item.OnChoose = MoveTemp(OnChanged);
	Item.SelectableCount = SelectableCount;

	const ULBUIStyle& Style = GetStyle();
	const int32 Size = RowTextSize > 0 ? RowTextSize : Style.ItemSize;
	Item.ValueText = MakeLabel(FText::GetEmpty(), ELBFontWeight::Regular, Size, Style.Dim, ETextJustify::Right);
	USizeBox* Box = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
	Box->SetWidthOverride(ValueColumnWidth);
	Box->AddChild(Item.ValueText);
	if (UHorizontalBoxSlot* ValueSlot = Row->AddChildToHorizontalBox(Box))
	{
		ValueSlot->SetVerticalAlignment(VAlign_Center);
		ValueSlot->SetHorizontalAlignment(HAlign_Right);
	}
	const int32 Index = Items.Num() - 1;
	UpdateValueText(Index);
	ApplyItemVisuals(Index, 1.f);
	return Index;
}

int32 ULBMenuWidgetBase::AddSliderItem(UPanelWidget& Parent, const FText& Label, float Min, float Max, float Step, float Initial, TFunction<FText(float)> Format, TFunction<void(float, bool)> OnSlide)
{
	UHorizontalBox* Row = nullptr;
	FLBMenuItem& Item = NewRow(Parent, ELBMenuItemKind::Slider, Label, Row);
	Item.Min = Min;
	Item.Max = FMath::Max(Max, Min + KINDA_SMALL_NUMBER);
	Item.Step = FMath::Max(Step, KINDA_SMALL_NUMBER);
	Item.Value = FMath::Clamp(Initial, Item.Min, Item.Max);
	Item.FinalValue = Item.Value;
	Item.FormatValue = MoveTemp(Format);
	Item.OnSlide = MoveTemp(OnSlide);
	const int32 Index = Items.Num() - 1;

	const ULBUIStyle& Style = GetStyle();
	const int32 Size = RowTextSize > 0 ? RowTextSize : Style.ItemSize;

	Item.Slider = WidgetTree->ConstructWidget<USlider>(USlider::StaticClass());
	Item.Slider->SetMinValue(Item.Min);
	Item.Slider->SetMaxValue(Item.Max);
	Item.Slider->SetStepSize(Item.Step / (Item.Max - Item.Min));
	Item.Slider->SetValue(Item.Value);
	Item.Slider->SetSliderBarColor(Style.Dim);
	Item.Slider->SetSliderHandleColor(Style.Accent);
	Item.SliderProxy = NewObject<ULBSliderProxy>(this);
	Item.SliderProxy->OnValueNative = [this, Index](float NewValue) { HandleSliderMoved(Index, NewValue); };
	Item.SliderProxy->OnCaptureEndNative = [this, Index]() { HandleSliderReleased(Index); };
	Item.Slider->OnValueChanged.AddDynamic(Item.SliderProxy, &ULBSliderProxy::HandleValueChanged);
	Item.Slider->OnMouseCaptureEnd.AddDynamic(Item.SliderProxy, &ULBSliderProxy::HandleCaptureEnd);

	USizeBox* SliderBox = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
	SliderBox->SetWidthOverride(SliderWidth);
	SliderBox->AddChild(Item.Slider);
	if (UHorizontalBoxSlot* SliderSlot = Row->AddChildToHorizontalBox(SliderBox))
	{
		SliderSlot->SetVerticalAlignment(VAlign_Center);
	}

	Item.ValueText = MakeLabel(FText::GetEmpty(), ELBFontWeight::Regular, Size, Style.Dim, ETextJustify::Right);
	USizeBox* ValueBox = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
	ValueBox->SetWidthOverride(SliderValueWidth);
	ValueBox->AddChild(Item.ValueText);
	if (UHorizontalBoxSlot* ValueSlot = Row->AddChildToHorizontalBox(ValueBox))
	{
		ValueSlot->SetVerticalAlignment(VAlign_Center);
		ValueSlot->SetHorizontalAlignment(HAlign_Right);
		ValueSlot->SetPadding(FMargin(14.f, 0.f, 0.f, 0.f));
	}
	UpdateValueText(Index);
	ApplyItemVisuals(Index, 1.f);
	return Index;
}

int32 ULBMenuWidgetBase::AddKeyItem(UPanelWidget& Parent, const FText& Label, ELBBindAction Action)
{
	UHorizontalBox* Row = nullptr;
	FLBMenuItem& Item = NewRow(Parent, ELBMenuItemKind::KeyBinding, Label, Row);
	Item.BindAction = Action;
	const int32 Index = Items.Num() - 1;

	const ULBUIStyle& Style = GetStyle();
	const int32 Size = RowTextSize > 0 ? RowTextSize : Style.ItemSize;

	// The prompt shown while waiting for a key (hidden otherwise).
	Item.ValueText = MakeLabel(NSLOCTEXT("LastBellUI", "PressAKey", "Press a key..."), ELBFontWeight::Italic, Size, Style.Accent, ETextJustify::Right);
	Item.ValueText->SetVisibility(ESlateVisibility::Collapsed);
	if (UHorizontalBoxSlot* PromptSlot = Row->AddChildToHorizontalBox(Item.ValueText))
	{
		PromptSlot->SetVerticalAlignment(VAlign_Center);
		PromptSlot->SetHorizontalAlignment(HAlign_Right);
	}

	Item.KeyIcon = WidgetTree->ConstructWidget<ULBKeyIconWidget>(ULBKeyIconWidget::StaticClass());
	Item.KeyIcon->SetPlayerContext(GetPlayerContext());
	Item.KeyIcon->SetGlyphHeight(static_cast<float>(Size) * 1.2f);
	Item.KeyIcon->SetBoundAction(Action);
	if (UHorizontalBoxSlot* IconSlot = Row->AddChildToHorizontalBox(Item.KeyIcon))
	{
		IconSlot->SetVerticalAlignment(VAlign_Center);
		IconSlot->SetHorizontalAlignment(HAlign_Right);
		IconSlot->SetPadding(FMargin(0.f, 0.f, 8.f, 0.f));
	}
	ApplyItemVisuals(Index, 1.f);
	return Index;
}

void ULBMenuWidgetBase::ClearItems()
{
	Items.Reset();
	SelectedIndex = INDEX_NONE;
	CaptureItem = INDEX_NONE;
}

// ---------------------------------------------------------------------------------------------------------------------
// State of rows
// ---------------------------------------------------------------------------------------------------------------------

void ULBMenuWidgetBase::UpdateValueText(int32 Index)
{
	if (!Items.IsValidIndex(Index) || !Items[Index].ValueText)
	{
		return;
	}
	FLBMenuItem& Item = Items[Index];
	switch (Item.Kind)
	{
	case ELBMenuItemKind::Slider:
		Item.ValueText->SetText(Item.FormatValue ? Item.FormatValue(Item.Value) : FText::AsNumber(FMath::RoundToInt(Item.Value)));
		break;
	case ELBMenuItemKind::Choice:
		Item.ValueText->SetText(Item.Options.IsValidIndex(Item.Index)
			? FText::Format(NSLOCTEXT("LastBellUI", "ChoiceFormat", "<  {0}  >"), Item.Options[Item.Index]) : FText::GetEmpty());
		break;
	case ELBMenuItemKind::Toggle:
		Item.ValueText->SetText(Item.Options.IsValidIndex(Item.Index) ? Item.Options[Item.Index] : FText::GetEmpty());
		break;
	default:
		break;
	}
}

void ULBMenuWidgetBase::ApplyItemVisuals(int32 Index, float Flicker)
{
	if (!Items.IsValidIndex(Index))
	{
		return;
	}
	const ULBUIStyle& Style = GetStyle();
	FLBMenuItem& Item = Items[Index];
	const bool bSelected = Index == SelectedIndex;
	const FLinearColor Highlight = Item.bDanger ? Style.Danger : Style.Accent;

	FLinearColor LabelColour = Scaled(Style.Ink, 0.85f);
	FLinearColor ValueColour = Style.Dim;
	if (!Item.bEnabled)
	{
		LabelColour = Scaled(Style.Dim, 0.6f);
		ValueColour = Scaled(Style.Dim, 0.6f);
	}
	else if (bSelected)
	{
		LabelColour = Scaled(Highlight, Flicker);
		ValueColour = Scaled(Highlight, Flicker);
	}
	else if (Item.bDanger)
	{
		LabelColour = Scaled(Style.Danger, 0.85f);
	}
	if (Item.Label)
	{
		Item.Label->SetColorAndOpacity(FSlateColor(LabelColour));
	}
	if (Item.ValueText && Item.Kind != ELBMenuItemKind::KeyBinding)
	{
		Item.ValueText->SetColorAndOpacity(FSlateColor(ValueColour));
	}
	if (Item.Marker)
	{
		Item.Marker->SetVisibility(bSelected && Item.bEnabled ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Hidden);
		Item.Marker->SetColorAndOpacity(FLinearColor(Highlight.R, Highlight.G, Highlight.B, Flicker));
	}
}

void ULBMenuWidgetBase::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	Super::NativeTick(MyGeometry, InDeltaTime);
	if (!Items.IsValidIndex(SelectedIndex))
	{
		return;
	}
	// Real time (Slate's), so the flame keeps flickering while the game is paused.
	FlickerClock += InDeltaTime;
	const ULBUIStyle& Style = GetStyle();
	ApplyItemVisuals(SelectedIndex, LBUILogic::CandleFlicker(FlickerClock, Style.FlickerSpeed, Style.FlickerAmplitude));
}

FText ULBMenuWidgetBase::GetItemLabel(int32 Index) const
{
	return (Items.IsValidIndex(Index) && Items[Index].Label) ? Items[Index].Label->GetText() : FText::GetEmpty();
}

int32 ULBMenuWidgetBase::FindItemByLabel(const FText& Label) const
{
	for (int32 Index = 0; Index < Items.Num(); ++Index)
	{
		if (Items[Index].Label && Items[Index].Label->GetText().EqualTo(Label))
		{
			return Index;
		}
	}
	return INDEX_NONE;
}

void ULBMenuWidgetBase::SelectItem(int32 Index, bool bPlaySound)
{
	if (!Items.IsValidIndex(Index) || !Items[Index].bEnabled || Index == SelectedIndex)
	{
		return;
	}
	const int32 Previous = SelectedIndex;
	SelectedIndex = Index;
	ApplyItemVisuals(Previous, 1.f);
	ApplyItemVisuals(SelectedIndex, 1.f);
	if (bPlaySound)
	{
		PlaySound(ELBUISound::Hover);
	}
}

void ULBMenuWidgetBase::MoveSelection(int32 Direction)
{
	const int32 Count = Items.Num();
	if (Count == 0 || Direction == 0)
	{
		return;
	}
	const int32 Step = Direction > 0 ? 1 : -1;
	int32 Candidate = SelectedIndex == INDEX_NONE ? (Step > 0 ? -1 : Count) : SelectedIndex;
	for (int32 Tries = 0; Tries < Count; ++Tries)
	{
		Candidate = (Candidate + Step + Count) % Count;
		if (Items[Candidate].bEnabled)
		{
			SelectItem(Candidate, SelectedIndex != INDEX_NONE);
			return;
		}
	}
}

void ULBMenuWidgetBase::HandleRowHovered(int32 Index)
{
	if (!IsCapturingKey())
	{
		SelectItem(Index, true);
	}
}

void ULBMenuWidgetBase::HandleRowClicked(int32 Index)
{
	if (IsCapturingKey() || !Items.IsValidIndex(Index) || !Items[Index].bEnabled)
	{
		return;
	}
	SelectItem(Index, false);
	ActivateItem(Index);
}

void ULBMenuWidgetBase::ActivateItem(int32 Index)
{
	if (!Items.IsValidIndex(Index) || !Items[Index].bEnabled)
	{
		return;
	}
	FLBMenuItem& Item = Items[Index];
	switch (Item.Kind)
	{
	case ELBMenuItemKind::Button:
		PlaySound(ELBUISound::Select);
		if (TFunction<void()> Callback = Item.OnActivate)
		{
			Callback();
		}
		break;
	case ELBMenuItemKind::Toggle:
	case ELBMenuItemKind::Choice:
		if (!Item.Options.IsEmpty())
		{
			PlaySound(ELBUISound::Select);
			{
				// Only the selectable options are steps; from a display-only state (Custom) the next step is the first option.
				const int32 Selectable = (Item.SelectableCount > 0 && Item.SelectableCount <= Item.Options.Num()) ? Item.SelectableCount : Item.Options.Num();
				SetChoiceIndex(Index, Item.Index >= Selectable ? 0 : (Item.Index + 1) % Selectable, true);
			}
		}
		break;
	case ELBMenuItemKind::KeyBinding:
		PlaySound(ELBUISound::Select);
		BeginKeyCapture(Index);
		break;
	case ELBMenuItemKind::Slider:
		break;
	}
}

void ULBMenuWidgetBase::AdjustItem(int32 Index, int32 Direction)
{
	if (!Items.IsValidIndex(Index) || !Items[Index].bEnabled || Direction == 0)
	{
		return;
	}
	FLBMenuItem& Item = Items[Index];
	const int32 Step = Direction > 0 ? 1 : -1;
	switch (Item.Kind)
	{
	case ELBMenuItemKind::Slider:
		SetSliderValue(Index, Item.Value + static_cast<float>(Step) * Item.Step, true);
		// A key press is a complete adjustment: report it as final too.
		if (Items.IsValidIndex(Index) && !FMath::IsNearlyEqual(Items[Index].FinalValue, Items[Index].Value))
		{
			Items[Index].FinalValue = Items[Index].Value;
			if (Items[Index].OnSlide)
			{
				TFunction<void(float, bool)> Callback = Items[Index].OnSlide;
				Callback(Items[Index].Value, true);
			}
		}
		break;
	case ELBMenuItemKind::Toggle:
	case ELBMenuItemKind::Choice:
		if (!Item.Options.IsEmpty())
		{
			const int32 Selectable = (Item.SelectableCount > 0 && Item.SelectableCount <= Item.Options.Num()) ? Item.SelectableCount : Item.Options.Num();
			// From a display-only state, back goes to the last selectable option and forward to the first.
			const int32 NewIndex = Item.Index >= Selectable ? (Step > 0 ? 0 : Selectable - 1) : FMath::Clamp(Item.Index + Step, 0, Selectable - 1);
			if (NewIndex != Item.Index)
			{
				PlaySound(ELBUISound::SliderTick);
				SetChoiceIndex(Index, NewIndex, true);
			}
		}
		break;
	default:
		break;
	}
}

void ULBMenuWidgetBase::SetChoiceIndex(int32 ItemIndex, int32 NewIndex, bool bNotify)
{
	if (!Items.IsValidIndex(ItemIndex) || Items[ItemIndex].Options.IsEmpty())
	{
		return;
	}
	FLBMenuItem& Item = Items[ItemIndex];
	Item.Index = FMath::Clamp(NewIndex, 0, Item.Options.Num() - 1);
	UpdateValueText(ItemIndex);
	if (bNotify)
	{
		if (TFunction<void(int32)> Callback = Item.OnChoose)
		{
			Callback(Item.Index);
		}
	}
}

void ULBMenuWidgetBase::SetToggleValue(int32 ItemIndex, bool bOn, bool bNotify)
{
	SetChoiceIndex(ItemIndex, bOn ? 1 : 0, bNotify);
}

void ULBMenuWidgetBase::SetSliderValue(int32 ItemIndex, float NewValue, bool bNotify)
{
	if (!Items.IsValidIndex(ItemIndex) || Items[ItemIndex].Kind != ELBMenuItemKind::Slider)
	{
		return;
	}
	FLBMenuItem& Item = Items[ItemIndex];
	Item.Value = FMath::Clamp(NewValue, Item.Min, Item.Max);
	if (Item.Slider)
	{
		Item.Slider->SetValue(Item.Value);
	}
	UpdateValueText(ItemIndex);
	if (bNotify)
	{
		if (FMath::Abs(Item.Value - LastSliderTickValue) >= Item.Step * 0.99f)
		{
			LastSliderTickValue = Item.Value;
			PlaySound(ELBUISound::SliderTick);
		}
		if (TFunction<void(float, bool)> Callback = Item.OnSlide)
		{
			Callback(Item.Value, false);
		}
	}
}

void ULBMenuWidgetBase::SetItemEnabled(int32 ItemIndex, bool bEnabled)
{
	if (!Items.IsValidIndex(ItemIndex))
	{
		return;
	}
	Items[ItemIndex].bEnabled = bEnabled;
	if (Items[ItemIndex].Button)
	{
		Items[ItemIndex].Button->SetIsEnabled(bEnabled);
	}
	if (!bEnabled && SelectedIndex == ItemIndex)
	{
		SelectedIndex = INDEX_NONE;
		MoveSelection(1);
	}
	ApplyItemVisuals(ItemIndex, 1.f);
}

void ULBMenuWidgetBase::SetItemLabel(int32 ItemIndex, const FText& Label)
{
	if (Items.IsValidIndex(ItemIndex) && Items[ItemIndex].Label)
	{
		Items[ItemIndex].Label->SetText(Label);
	}
}

void ULBMenuWidgetBase::SetItemDanger(int32 ItemIndex, bool bDanger)
{
	if (Items.IsValidIndex(ItemIndex))
	{
		Items[ItemIndex].bDanger = bDanger;
		ApplyItemVisuals(ItemIndex, 1.f);
	}
}

void ULBMenuWidgetBase::RefreshKeyItem(int32 ItemIndex)
{
	if (Items.IsValidIndex(ItemIndex) && Items[ItemIndex].KeyIcon)
	{
		Items[ItemIndex].KeyIcon->Refresh();
	}
}

void ULBMenuWidgetBase::HandleSliderMoved(int32 Index, float NewValue)
{
	if (!Items.IsValidIndex(Index))
	{
		return;
	}
	FLBMenuItem& Item = Items[Index];
	Item.Value = FMath::Clamp(NewValue, Item.Min, Item.Max);
	UpdateValueText(Index);
	if (FMath::Abs(Item.Value - LastSliderTickValue) >= Item.Step * 0.99f)
	{
		LastSliderTickValue = Item.Value;
		PlaySound(ELBUISound::SliderTick);
	}
	if (TFunction<void(float, bool)> Callback = Item.OnSlide)
	{
		Callback(Item.Value, false);
	}
}

void ULBMenuWidgetBase::HandleSliderReleased(int32 Index)
{
	if (!Items.IsValidIndex(Index))
	{
		return;
	}
	FLBMenuItem& Item = Items[Index];
	Item.FinalValue = Item.Value;
	if (TFunction<void(float, bool)> Callback = Item.OnSlide)
	{
		Callback(Item.Value, true);
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// Key capture
// ---------------------------------------------------------------------------------------------------------------------

void ULBMenuWidgetBase::BeginKeyCapture(int32 ItemIndex)
{
	if (!Items.IsValidIndex(ItemIndex) || Items[ItemIndex].Kind != ELBMenuItemKind::KeyBinding)
	{
		return;
	}
	CaptureItem = ItemIndex;
	FLBMenuItem& Item = Items[ItemIndex];
	if (Item.KeyIcon)
	{
		Item.KeyIcon->SetVisibility(ESlateVisibility::Collapsed);
	}
	if (Item.ValueText)
	{
		Item.ValueText->SetText(NSLOCTEXT("LastBellUI", "PressAKey", "Press a key..."));
		Item.ValueText->SetVisibility(ESlateVisibility::HitTestInvisible);
	}
}

void ULBMenuWidgetBase::EndKeyCapture()
{
	if (Items.IsValidIndex(CaptureItem))
	{
		FLBMenuItem& Item = Items[CaptureItem];
		if (Item.KeyIcon)
		{
			Item.KeyIcon->SetVisibility(ESlateVisibility::HitTestInvisible);
			Item.KeyIcon->Refresh();
		}
		if (Item.ValueText)
		{
			Item.ValueText->SetVisibility(ESlateVisibility::Collapsed);
		}
	}
	CaptureItem = INDEX_NONE;
}

// ---------------------------------------------------------------------------------------------------------------------
// Input
// ---------------------------------------------------------------------------------------------------------------------

FReply ULBMenuWidgetBase::NativeOnKeyDown(const FGeometry& InGeometry, const FKeyEvent& InKeyEvent)
{
	const FKey Key = InKeyEvent.GetKey();

	if (IsCapturingKey())
	{
		if (!InKeyEvent.IsRepeat() && OnKeyCaptured(CaptureItem, Key))
		{
			EndKeyCapture();
		}
		return FReply::Handled();
	}

	if (Key == EKeys::Up)
	{
		MoveSelection(-1);
		return FReply::Handled();
	}
	if (Key == EKeys::Down)
	{
		MoveSelection(1);
		return FReply::Handled();
	}
	if (Key == EKeys::Left || Key == EKeys::Right)
	{
		AdjustItem(SelectedIndex, Key == EKeys::Right ? 1 : -1);
		return FReply::Handled();
	}
	if (!InKeyEvent.IsRepeat())
	{
		if (Key == EKeys::Enter || Key == EKeys::SpaceBar)
		{
			ActivateItem(SelectedIndex);
			return FReply::Handled();
		}
		if (Key == EKeys::Escape)
		{
			if (ULBUISubsystem* UI = GetUI())
			{
				UI->HandleBack();
			}
			else
			{
				HandleBack();
			}
			return FReply::Handled();
		}
	}
	return Super::NativeOnKeyDown(InGeometry, InKeyEvent);
}

FReply ULBMenuWidgetBase::NativeOnPreviewMouseButtonDown(const FGeometry& InGeometry, const FPointerEvent& InMouseEvent)
{
	if (IsCapturingKey())
	{
		if (OnKeyCaptured(CaptureItem, InMouseEvent.GetEffectingButton()))
		{
			EndKeyCapture();
		}
		return FReply::Handled();
	}
	return Super::NativeOnPreviewMouseButtonDown(InGeometry, InMouseEvent);
}
