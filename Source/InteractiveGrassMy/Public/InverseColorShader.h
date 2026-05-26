#pragma once

#include "GlobalShader.h"
#include "ScreenPass.h"
#include "ShaderParameterStruct.h"

BEGIN_SHADER_PARAMETER_STRUCT(FInverseColorPSParameters, )
	SHADER_PARAMETER_STRUCT(FScreenPassTextureSliceInput, Input)
	SHADER_PARAMETER(FScreenTransform, SvPositionToInputTextureUV)
	RENDER_TARGET_BINDING_SLOTS()
END_SHADER_PARAMETER_STRUCT()

class FInverseColorPS : public FGlobalShader
{
public:
	DECLARE_GLOBAL_SHADER(FInverseColorPS);
	SHADER_USE_PARAMETER_STRUCT(FInverseColorPS, FGlobalShader);

	using FParameters = FInverseColorPSParameters;

	static bool ShouldCompilePermutation(const FGlobalShaderPermutationParameters& Parameters)
	{
		return IsFeatureLevelSupported(Parameters.Platform, ERHIFeatureLevel::SM5);
	}
};
