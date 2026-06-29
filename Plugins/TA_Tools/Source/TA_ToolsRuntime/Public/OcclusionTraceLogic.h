// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"

class UTreeFadeComponent;

struct FOcclusionTraceFadeActions
{
	UTreeFadeComponent* FadeInTarget = nullptr;
	UTreeFadeComponent* FadeOutTarget = nullptr;
	bool bClearLastHit = false;
};

/** Pure single-target state machine for occlusion trace results (see PRD). */
TA_TOOLSRUNTIME_API FOcclusionTraceFadeActions EvaluateOcclusionTrace(
	UTreeFadeComponent* LastHit,
	UTreeFadeComponent* HitComponent);
