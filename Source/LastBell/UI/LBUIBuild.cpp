#include "UI/LBUIBuild.h"
#include "Blueprint/WidgetTree.h"
#include "Components/TextBlock.h"

FSlateBrush LBUIBuild::SolidBrush(const FLinearColor& Fill)
{
	FSlateBrush Brush;
	Brush.DrawAs = ESlateBrushDrawType::Image;
	Brush.TintColor = FSlateColor(Fill);
	return Brush;
}

FSlateBrush LBUIBuild::RoundedBrush(const FLinearColor& Fill, float Radius, const FLinearColor& Outline, float OutlineWidth)
{
	FSlateBrush Brush;
	Brush.DrawAs = ESlateBrushDrawType::RoundedBox;
	Brush.TintColor = FSlateColor(Fill);
	Brush.OutlineSettings = FSlateBrushOutlineSettings(Radius, FSlateColor(Outline), OutlineWidth);
	return Brush;
}

UTextBlock* LBUIBuild::MakeText(UWidgetTree& Tree, const FText& Text, const FSlateFontInfo& Font, const FLinearColor& Colour, ETextJustify::Type Justify)
{
	UTextBlock* Block = Tree.ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
	Block->SetFont(Font);
	Block->SetColorAndOpacity(FSlateColor(Colour));
	Block->SetJustification(Justify);
	Block->SetText(Text);
	return Block;
}

FSlateFontInfo LBUIBuild::WithOutline(FSlateFontInfo Font, int32 OutlineSize, const FLinearColor& OutlineColour)
{
	Font.OutlineSettings.OutlineSize = OutlineSize;
	Font.OutlineSettings.OutlineColor = OutlineColour;
	return Font;
}
