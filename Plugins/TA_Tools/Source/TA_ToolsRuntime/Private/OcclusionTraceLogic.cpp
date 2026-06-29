// Copyright Epic Games, Inc. All Rights Reserved.

#include "OcclusionTraceLogic.h"
#include "TreeFadeComponent.h"

FOcclusionTraceFadeActions EvaluateOcclusionTrace(UTreeFadeComponent* LastHit, UTreeFadeComponent* HitComponent)
{
	FOcclusionTraceFadeActions Actions;

	if (IsValid(HitComponent))
	{
		if (HitComponent != LastHit)
		{
			if (IsValid(LastHit))
			{
				Actions.FadeInTarget = LastHit;
			}
			Actions.FadeOutTarget = HitComponent;
		}
	}
	else if (IsValid(LastHit))
	{
		Actions.FadeInTarget = LastHit;
		Actions.bClearLastHit = true;
	}

	return Actions;
}
