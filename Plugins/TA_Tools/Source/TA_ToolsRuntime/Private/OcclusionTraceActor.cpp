// Copyright Epic Games, Inc. All Rights Reserved.

#include "OcclusionTraceActor.h"
#include "OcclusionTraceLogic.h"
#include "TreeFadeComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "DrawDebugHelpers.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"

AOcclusionTraceActor::AOcclusionTraceActor()
{
	PrimaryActorTick.bCanEverTick = false;
}

void AOcclusionTraceActor::BeginPlay()
{
	Super::BeginPlay();

	ResolveTargetActor();

	if (IsValid(TargetActor))
	{
		StartTrace();
	}
	else
	{
		UE_LOG(LogTemp, Warning, TEXT("AOcclusionTraceActor '%s': TargetActor is null, trace not started."), *GetName());
	}
}

bool AOcclusionTraceActor::ResolveTargetActor()
{
	if (IsValid(TargetActor))
	{
		return true;
	}

	if (!bAutoAssignPlayerCharacter)
	{
		return false;
	}

	UWorld* World = GetWorld();
	if (!World)
	{
		return false;
	}

	if (ACharacter* PlayerCharacter = UGameplayStatics::GetPlayerCharacter(World, PlayerIndex))
	{
		TargetActor = PlayerCharacter;
		return true;
	}

	return false;
}

void AOcclusionTraceActor::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	StopTrace();
	Super::EndPlay(EndPlayReason);
}

void AOcclusionTraceActor::StartTrace()
{
	UWorld* World = GetWorld();
	if (!World || !IsValid(TargetActor))
	{
		return;
	}

	World->GetTimerManager().SetTimer(
		TraceTimerHandle,
		this,
		&AOcclusionTraceActor::PerformTrace,
		TraceInterval,
		true);
}

void AOcclusionTraceActor::StopTrace()
{
	if (UWorld* World = GetWorld())
	{
		World->GetTimerManager().ClearTimer(TraceTimerHandle);
	}
}

void AOcclusionTraceActor::PerformTrace()
{
	if (!IsValid(TargetActor))
	{
		ApplyTraceResult(nullptr);
		return;
	}

	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}

	APlayerController* PlayerController = UGameplayStatics::GetPlayerController(World, PlayerIndex);
	if (!PlayerController || !PlayerController->PlayerCameraManager)
	{
		ApplyTraceResult(nullptr);
		return;
	}

	const FVector TraceStart = TargetActor->GetActorLocation() + FVector(0.0f, 0.0f, TargetZOffset);
	const FVector TraceEnd = PlayerController->PlayerCameraManager->GetCameraLocation();

	FHitResult HitResult;
	FCollisionQueryParams QueryParams(NAME_None, false);
	QueryParams.AddIgnoredActor(this);
	QueryParams.AddIgnoredActor(TargetActor);

	const bool bHit = World->SweepSingleByChannel(
		HitResult,
		TraceStart,
		TraceEnd,
		FQuat::Identity,
		ECC_Visibility,
		FCollisionShape::MakeSphere(SweepRadius),
		QueryParams);

	UTreeFadeComponent* HitComponent = nullptr;
	if (bHit && HitResult.GetActor())
	{
		HitComponent = HitResult.GetActor()->FindComponentByClass<UTreeFadeComponent>();
	}

	if (bDrawDebugTrace)
	{
		DrawDebugTrace(TraceStart, TraceEnd, IsValid(HitComponent));
	}

	ApplyTraceResult(HitComponent);
}

void AOcclusionTraceActor::ApplyTraceResult(UTreeFadeComponent* HitComponent)
{
	const FOcclusionTraceFadeActions Actions = EvaluateOcclusionTrace(LastHitFadeComponent, HitComponent);

	if (IsValid(Actions.FadeInTarget))
	{
		Actions.FadeInTarget->StartFadeIn();
	}

	if (IsValid(Actions.FadeOutTarget))
	{
		LastHitFadeComponent = Actions.FadeOutTarget;
		LastHitFadeComponent->StartFadeOut();
	}
	else if (Actions.bClearLastHit)
	{
		LastHitFadeComponent = nullptr;
	}
}

void AOcclusionTraceActor::DrawDebugTrace(const FVector& TraceStart, const FVector& TraceEnd, bool bHitTree) const
{
#if ENABLE_DRAW_DEBUG
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}

	const FColor Color = bHitTree ? FColor::Green : FColor::Red;
	const float Lifetime = TraceInterval;

	DrawDebugLine(World, TraceStart, TraceEnd, Color, false, Lifetime, 0, 1.5f);
	DrawDebugSphere(World, TraceStart, SweepRadius, 12, Color, false, Lifetime);
	DrawDebugSphere(World, TraceEnd, SweepRadius, 12, Color, false, Lifetime);
#endif
}
