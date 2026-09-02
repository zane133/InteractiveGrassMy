import unittest

from TATools.custom_node_shader_core import (
    DEFAULT_NODE_SCALAR,
    DEFAULT_NODE_TEXTURE,
    DEFAULT_NODE_VECTOR,
    build_top_to_bottom_layout,
    clean_shader_text,
    infer_default_node_kind,
    normalize_manual_inputs,
    parse_shader,
)


class CustomNodeShaderCoreTests(unittest.TestCase):
    def test_parses_user_style_header(self):
        parsed = parse_shader(
            """// BG3 MSKcloth dye lookup - Unreal Engine Material Custom node code.
// Custom node settings:
//   Output Type: CMOT Float 3
// Inputs (names must match exactly):
//   DyeIdRGB         - MSKcloth texture RGB
//   ClothPrimary     - dye colour
//   ClothSecondary   - dye colour
//   ClothTertiary    - dye colour
//   AccentColor      - dye colour
//   LeatherPrimary   - dye colour
//   LeatherSecondary - dye colour
//   LeatherTertiary  - dye colour
//   Custom1          - dye colour
//   MetalPrimary     - dye colour
//   MetalSecondary   - dye colour
//   MetalTertiary    - dye colour
//   Custom2          - dye colour
//
// Connect the returned float3 to BaseColor.
float3 dyeId = DyeIdRGB.rgb;
return ClothPrimary.rgb + Custom2.rgb;
"""
        )
        self.assertEqual(parsed.output_components, 3)
        self.assertEqual(
            parsed.inputs,
            (
                "DyeIdRGB",
                "ClothPrimary",
                "ClothSecondary",
                "ClothTertiary",
                "AccentColor",
                "LeatherPrimary",
                "LeatherSecondary",
                "LeatherTertiary",
                "Custom1",
                "MetalPrimary",
                "MetalSecondary",
                "MetalTertiary",
                "Custom2",
            ),
        )
        self.assertTrue(parsed.description.startswith("BG3 MSKcloth dye lookup"))

    def test_cleans_html_markdown_and_fences(self):
        cleaned = clean_shader_text(
            "```hlsl\nfloat4 weights = max(\n&#x20;  value, 0.0);\n"
            "float ID\\_VALUE = 1;\nreturn a \\+ b;\n```"
        )
        self.assertNotIn("&#x20;", cleaned)
        self.assertNotIn("```", cleaned)
        self.assertIn("float ID_VALUE", cleaned)
        self.assertIn("return a + b", cleaned)

    def test_manual_inputs_are_validated_and_deduplicated(self):
        self.assertEqual(
            normalize_manual_inputs("A\nB, A\n_C"),
            ("A", "B", "_C"),
        )
        with self.assertRaises(ValueError):
            normalize_manual_inputs("Valid\nNot Valid")

    def test_infers_default_material_node_types(self):
        code = """// Inputs:
// DyeIdRGB - MSKcloth texture RGB
// Tint - dye colour
// Strength - scalar
return DyeIdRGB.rgb * Tint.rgb * Strength;
"""
        self.assertEqual(
            infer_default_node_kind(code, "DyeIdRGB"), DEFAULT_NODE_TEXTURE
        )
        self.assertEqual(infer_default_node_kind(code, "Tint"), DEFAULT_NODE_VECTOR)
        self.assertEqual(
            infer_default_node_kind(code, "Strength"), DEFAULT_NODE_SCALAR
        )

    def test_default_nodes_keep_input_order_from_top_to_bottom(self):
        inputs = ("DyeIdRGB", "ClothPrimary", "ClothSecondary", "Custom2")
        layout = build_top_to_bottom_layout(inputs, custom_x=400, custom_y=0)

        self.assertEqual(tuple(item[0] for item in layout), inputs)
        self.assertEqual(tuple(item[1] for item in layout), (-60, -60, -60, -60))
        self.assertEqual(tuple(item[2] for item in layout), (-195, -65, 65, 195))


if __name__ == "__main__":
    unittest.main()
