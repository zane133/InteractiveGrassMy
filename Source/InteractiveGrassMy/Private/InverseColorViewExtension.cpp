#include "InverseColorViewExtension.h"
#include "InverseColorShader.h"

#include "PixelShaderUtils.h"
#include "PostProcess/PostProcessMaterialInputs.h"
#include "SceneView.h"

static TAutoConsoleVariable<int32> CVarInverseColor(
	TEXT("r.InverseColor"),
	0,
	TEXT("Enable inverse color post process effect.\n")
	TEXT("0: Disabled\n")
	TEXT("1: Enabled"),
	ECVF_RenderThreadSafe);

FInverseColorViewExtension::FInverseColorViewExtension(const FAutoRegister& AutoRegister)
	: FSceneViewExtensionBase(AutoRegister)
{
}

void FInverseColorViewExtension::SubscribeToPostProcessingPass(
	EPostProcessingPass Pass,
	const FSceneView& InView,
	FPostProcessingPassDelegateArray& InOutPassCallbacks,
	bool bIsPassEnabled)
{
	if (Pass == EPostProcessingPass::Tonemap && bIsPassEnabled)
	{
		InOutPassCallbacks.Add(
			FPostProcessingPassDelegate::CreateRaw(this, &FInverseColorViewExtension::InverseColorPass_RenderThread));
	}
}

FScreenPassTexture FInverseColorViewExtension::InverseColorPass_RenderThread(
	FRDGBuilder& GraphBuilder,
	const FSceneView& View,
	const FPostProcessMaterialInputs& Inputs)
{
	const FScreenPassTextureSlice SceneColorSlice = Inputs.GetInput(EPostProcessMaterialInput::SceneColor);
	if (!SceneColorSlice.IsValid() || CVarInverseColor.GetValueOnRenderThread() == 0)
	{
		return Inputs.ReturnUntouchedSceneColorForPostProcessing(GraphBuilder);
	}

	const FScreenPassTexture SceneColor = FScreenPassTexture::CopyFromSlice(GraphBuilder, SceneColorSlice);

	FScreenPassRenderTarget Output = Inputs.OverrideOutput;
	if (!Output.IsValid())
	{
		Output = FScreenPassRenderTarget::CreateFromInput(
			GraphBuilder,
			SceneColor,
			View.GetOverwriteLoadAction(),
			TEXT("FInverseColorViewExtension.InverseColor"));
	}

	FRHISamplerState* BilinearClampSampler = TStaticSamplerState<SF_Bilinear, AM_Clamp, AM_Clamp, AM_Clamp>::GetRHI();

	FInverseColorPS::FParameters* PassParameters = GraphBuilder.AllocParameters<FInverseColorPS::FParameters>();
	PassParameters->Input = GetScreenPassTextureInput(SceneColorSlice, BilinearClampSampler);
	PassParameters->SvPositionToInputTextureUV = (
		FScreenTransform::ChangeTextureBasisFromTo(
			FScreenPassTextureViewport(Output),
			FScreenTransform::ETextureBasis::TexelPosition,
			FScreenTransform::ETextureBasis::ViewportUV) *
		FScreenTransform::ChangeTextureBasisFromTo(
			FScreenPassTextureViewport(SceneColorSlice),
			FScreenTransform::ETextureBasis::ViewportUV,
			FScreenTransform::ETextureBasis::TextureUV));
	PassParameters->RenderTargets[0] = Output.GetRenderTargetBinding();

	TShaderMapRef<FInverseColorPS> PixelShader(GetGlobalShaderMap(View.GetFeatureLevel()));

	FPixelShaderUtils::AddFullscreenPass(
		GraphBuilder,
		GetGlobalShaderMap(View.GetFeatureLevel()),
		RDG_EVENT_NAME("FInverseColorViewExtension::InverseColor"),
		PixelShader,
		PassParameters,
		Output.ViewRect);

	return FScreenPassTexture(Output);
}
