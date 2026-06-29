// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "OcclusionTraceActor.generated.h"

class UTreeFadeComponent;

UCLASS(Blueprintable, BlueprintType, meta = (DisplayName = "Occlusion Trace Actor"))
class TA_TOOLSRUNTIME_API AOcclusionTraceActor : public AActor
{
	GENERATED_BODY()

public:
	AOcclusionTraceActor();

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	UFUNCTION(BlueprintCallable, Category = "Occlusion Trace")
	void StartTrace();

	UFUNCTION(BlueprintCallable, Category = "Occlusion Trace")
	void StopTrace();

	UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category = "Occlusion Trace")
	TObjectPtr<AActor> TargetActor;

	/** When TargetActor is unset, assign Player Character 0 on BeginPlay. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Occlusion Trace")
	bool bAutoAssignPlayerCharacter = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Occlusion Trace", meta = (ClampMin = "0"))
	int32 PlayerIndex = 0;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Occlusion Trace", meta = (ClampMin = "0.01"))
	float TraceInterval = 0.05f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Occlusion Trace", meta = (ClampMin = "0.0"))
	float SweepRadius = 25.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Occlusion Trace")
	float TargetZOffset = 80.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Occlusion Trace")
	bool bDrawDebugTrace = false;

private:
	UPROPERTY()
	TObjectPtr<UTreeFadeComponent> LastHitFadeComponent;

	FTimerHandle TraceTimerHandle;

	bool ResolveTargetActor();
	void PerformTrace();
	void ApplyTraceResult(UTreeFadeComponent* HitComponent);
	void DrawDebugTrace(const FVector& TraceStart, const FVector& TraceEnd, bool bHitTree) const;
};
