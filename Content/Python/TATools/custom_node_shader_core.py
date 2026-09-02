# -*- coding: utf-8 -*-
"""Pure-Python parsing helpers for the Custom Node shader paste tool."""

from __future__ import annotations

from dataclasses import dataclass
import html
import re


_OUTPUT_TYPE_RE = re.compile(
    r"output\s*type\s*:\s*(?:cmot[\s_-]*)?float\s*([1-4])?",
    re.IGNORECASE,
)
_INPUT_HEADER_RE = re.compile(r"^\s*//\s*inputs?\b", re.IGNORECASE)
_COMMENT_RE = re.compile(r"^\s*//\s?(.*)$")
_INPUT_RE = re.compile(
    r"^\s*(?:(?:float|half|double|int|uint|bool)(?:[1-4](?:x[1-4])?)?\s+)?"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:[-:–—]\s*.*)?$"
)
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_FENCE_RE = re.compile(r"^\s*```(?:hlsl|glsl|c|cpp|shader)?\s*$", re.IGNORECASE)

DEFAULT_NODE_TEXTURE = "texture"
DEFAULT_NODE_VECTOR = "vector"
DEFAULT_NODE_SCALAR = "scalar"


@dataclass(frozen=True)
class ParsedShader:
    code: str
    inputs: tuple[str, ...]
    output_components: int
    description: str


def clean_shader_text(text: str) -> str:
    """Normalize common HTML/Markdown damage introduced while copying HLSL."""
    cleaned = html.unescape(text or "")
    cleaned = cleaned.replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n")

    lines = cleaned.split("\n")
    if lines and _FENCE_RE.match(lines[0]):
        lines.pop(0)
    if lines and _FENCE_RE.match(lines[-1]):
        lines.pop()
    cleaned = "\n".join(lines)

    # Chat/Markdown often escapes these HLSL characters.  Do not touch escapes
    # such as \n or Windows/include paths.
    cleaned = re.sub(r"\\([_*+])", r"\1", cleaned)
    return cleaned.strip()


def parse_output_components(text: str, default: int = 1) -> int:
    match = _OUTPUT_TYPE_RE.search(text or "")
    if not match:
        return default
    return int(match.group(1) or "1")


def parse_description(text: str, default: str = "Pasted Custom HLSL") -> str:
    for line in (text or "").splitlines():
        match = _COMMENT_RE.match(line)
        if not match:
            if line.strip():
                break
            continue
        value = match.group(1).strip().rstrip(".")
        if not value:
            continue
        lowered = value.lower()
        if lowered.startswith(("custom node settings", "output type", "inputs")):
            continue
        return value[:128]
    return default


def parse_commented_inputs(text: str) -> tuple[str, ...]:
    """Read an ``// Inputs`` block, preserving declaration order."""
    inputs: list[str] = []
    in_inputs = False

    for line in (text or "").splitlines():
        if _INPUT_HEADER_RE.match(line):
            in_inputs = True
            continue
        if not in_inputs:
            continue

        comment = _COMMENT_RE.match(line)
        if not comment:
            if line.strip():
                break
            continue

        value = comment.group(1).strip()
        if not value:
            if inputs:
                break
            continue

        match = _INPUT_RE.match(value)
        if not match:
            if inputs:
                break
            continue

        name = match.group(1)
        if name not in inputs:
            inputs.append(name)

    return tuple(inputs)


def normalize_manual_inputs(text: str) -> tuple[str, ...]:
    """Parse one input name per line (commas are also accepted)."""
    inputs: list[str] = []
    for raw in re.split(r"[,\n]", text or ""):
        name = raw.strip()
        if not name:
            continue
        if not _IDENTIFIER_RE.match(name):
            raise ValueError("无效的输入名：{}".format(name))
        if name not in inputs:
            inputs.append(name)
    return tuple(inputs)


def infer_default_node_kind(code: str, input_name: str) -> str:
    """Infer a useful Material node type for an unconnected Custom input."""
    escaped_name = re.escape(input_name)

    for line in (code or "").splitlines():
        comment = _COMMENT_RE.match(line)
        if not comment:
            continue
        value = comment.group(1).strip()
        match = re.match(
            r"^(?:(?:float|half|double|int|uint|bool)(?:[1-4])?\s+)?"
            + escaped_name
            + r"\s*(?:[-:–—]\s*(.*))?$",
            value,
            re.IGNORECASE,
        )
        if not match:
            continue
        description = (match.group(1) or "").lower()
        if any(word in description for word in ("texture", "贴图", "纹理")):
            return DEFAULT_NODE_TEXTURE
        if any(word in description for word in ("rgb", "rgba", "colour", "color", "颜色")):
            return DEFAULT_NODE_VECTOR

    vector_member = re.compile(
        r"\b" + escaped_name + r"\s*\.\s*(?:rgb|rgba|rg|xyz|xyzw|xy|yz|zw)\b",
        re.IGNORECASE,
    )
    vector_declaration = re.compile(
        r"\b(?:float|half|double|int|uint)(?:2|3|4)\s+"
        + escaped_name
        + r"\b",
        re.IGNORECASE,
    )
    if vector_member.search(code or "") or vector_declaration.search(code or ""):
        return DEFAULT_NODE_VECTOR
    return DEFAULT_NODE_SCALAR


def build_top_to_bottom_layout(
    inputs: tuple[str, ...] | list[str],
    custom_x: int,
    custom_y: int,
    spacing_y: int = 130,
    x_offset: int = 460,
) -> tuple[tuple[str, int, int], ...]:
    """Lay inputs out top-to-bottom without changing their declaration order."""
    if not inputs:
        return ()
    start_y = custom_y - ((len(inputs) - 1) * spacing_y) // 2
    return tuple(
        (name, custom_x - x_offset, start_y + index * spacing_y)
        for index, name in enumerate(inputs)
    )


def parse_shader(text: str) -> ParsedShader:
    code = clean_shader_text(text)
    return ParsedShader(
        code=code,
        inputs=parse_commented_inputs(code),
        output_components=parse_output_components(code),
        description=parse_description(code),
    )
