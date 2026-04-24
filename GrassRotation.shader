Shader "Custom/URP/GrassRotation"
{
    Properties
    {
        _BaseMap       ("Albedo Texture",  2D)            = "white" {}
        _BaseColor     ("Base Color",      Color)         = (0.25, 0.75, 0.15, 1)
        _Cutoff        ("Alpha Cutoff",    Range(0, 1))   = 0.5
        _RotationSpeed ("Rotation Speed",  Float)         = 1.0
    }

    SubShader
    {
        Tags
        {
            "RenderType"     = "TransparentCutout"
            "RenderPipeline" = "UniversalPipeline"
            "Queue"          = "AlphaTest"
        }

        // ─────────────────────────────────────────────────────
        //  Forward Lit
        // ─────────────────────────────────────────────────────
        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }
            Cull Off

            HLSLPROGRAM
            #pragma vertex   vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE
            #pragma multi_compile_instancing

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            TEXTURE2D(_BaseMap);
            SAMPLER(sampler_BaseMap);

            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;
                half4  _BaseColor;
                half   _Cutoff;
                float  _RotationSpeed;
            CBUFFER_END

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS   : NORMAL;
                float2 uv         : TEXCOORD0;
                float2 pivotXZ    : TEXCOORD1; // UV2: blade root X,Z in object space
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv         : TEXCOORD0;
                float3 normalWS   : TEXCOORD1;
                float3 positionWS : TEXCOORD2;
                float  fogFactor  : TEXCOORD3;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            // 绕 Y 轴旋转，pivot 来自 UV2
            void RotateAroundPivot(inout float3 posOS, inout float3 normalOS, float2 pivotXZ, float angle)
            {
                float3 pivot = float3(pivotXZ.x, 0.0, pivotXZ.y);
                float  s = sin(angle), c = cos(angle);

                float3 p = posOS - pivot;
                posOS.x = p.x * c - p.z * s;
                posOS.z = p.x * s + p.z * c;
                posOS.y = p.y;
                posOS  += pivot;

                float3 n = normalOS;
                normalOS.x = n.x * c - n.z * s;
                normalOS.z = n.x * s + n.z * c;
            }

            Varyings vert(Attributes input)
            {
                UNITY_SETUP_INSTANCE_ID(input);
                Varyings output = (Varyings)0;
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(output);

                float3 posOS    = input.positionOS.xyz;
                float3 normalOS = input.normalOS;

                float angle = _Time.y * _RotationSpeed;
                RotateAroundPivot(posOS, normalOS, input.pivotXZ, angle);

                output.positionCS = TransformObjectToHClip(posOS);
                output.positionWS = TransformObjectToWorld(posOS);
                output.normalWS   = TransformObjectToWorldNormal(normalOS);
                output.uv         = TRANSFORM_TEX(input.uv, _BaseMap);
                output.fogFactor  = ComputeFogFactor(output.positionCS.z);
                return output;
            }

            half4 frag(Varyings input) : SV_Target
            {
                half4 albedo = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv) * _BaseColor;
                clip(albedo.a - _Cutoff);

                float3 normalWS    = normalize(input.normalWS);
                float4 shadowCoord = TransformWorldToShadowCoord(input.positionWS);
                Light  mainLight   = GetMainLight(shadowCoord);

                half3 diffuse = LightingLambert(mainLight.color * mainLight.shadowAttenuation,
                                                mainLight.direction, normalWS);
                half3 color = albedo.rgb * (diffuse + SampleSH(normalWS));
                color = MixFog(color, input.fogFactor);
                return half4(color, 1.0);
            }
            ENDHLSL
        }

        // ─────────────────────────────────────────────────────
        //  Shadow Caster
        // ─────────────────────────────────────────────────────
        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode" = "ShadowCaster" }
            Cull Off
            ColorMask 0

            HLSLPROGRAM
            #pragma vertex   vertShadow
            #pragma fragment fragShadow
            #pragma multi_compile_instancing

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;
                half4  _BaseColor;
                half   _Cutoff;
                float  _RotationSpeed;
            CBUFFER_END

            float3 _LightDirection;

            struct AttributesShadow
            {
                float4 positionOS : POSITION;
                float3 normalOS   : NORMAL;
                float2 uv         : TEXCOORD0;
                float2 pivotXZ    : TEXCOORD1;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            void RotateAroundPivot(inout float3 posOS, inout float3 normalOS, float2 pivotXZ, float angle)
            {
                float3 pivot = float3(pivotXZ.x, 0.0, pivotXZ.y);
                float  s = sin(angle), c = cos(angle);
                float3 p = posOS - pivot;
                posOS.x = p.x * c - p.z * s;
                posOS.z = p.x * s + p.z * c;
                posOS.y = p.y;
                posOS  += pivot;
                float3 n = normalOS;
                normalOS.x = n.x * c - n.z * s;
                normalOS.z = n.x * s + n.z * c;
            }

            float4 vertShadow(AttributesShadow input) : SV_POSITION
            {
                UNITY_SETUP_INSTANCE_ID(input);
                float3 posOS    = input.positionOS.xyz;
                float3 normalOS = input.normalOS;
                RotateAroundPivot(posOS, normalOS, input.pivotXZ, _Time.y * _RotationSpeed);

                float3 posWS    = TransformObjectToWorld(posOS);
                float3 normalWS = TransformObjectToWorldNormal(normalOS);
                float4 posCS    = TransformWorldToHClip(ApplyShadowBias(posWS, normalWS, _LightDirection));
                #if UNITY_REVERSED_Z
                    posCS.z = min(posCS.z, posCS.w * UNITY_NEAR_CLIP_VALUE);
                #else
                    posCS.z = max(posCS.z, posCS.w * UNITY_NEAR_CLIP_VALUE);
                #endif
                return posCS;
            }

            half fragShadow(float4 posCS : SV_POSITION) : SV_Target { return 0; }
            ENDHLSL
        }
    }
    FallBack "Hidden/Universal Render Pipeline/FallbackError"
}
