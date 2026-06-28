from __future__ import annotations

import re


def normalize_superscript_citations(text: str) -> str:
    text = re.sub(r'\$\^\{([^}]+)\}(?=[A-Za-z])', r'$^{\1}$ ', text)
    text = re.sub(r'\$\^\{\s+', r'$^{', text)
    text = re.sub(r'\s+\}\$', r'}$', text)
    return text


def normalize_inline_math_delimiters(text: str) -> str:
    text = re.sub(r'\$\s+', '$', text)
    text = re.sub(r'\s+\$', '$', text)
    text = re.sub(r'\$\s*_\{\s*', r'$_{', text)
    text = re.sub(r'\s*\}\s*\$', r'}$', text)
    return text


_RELOP_PATTERN = re.compile(
    r'(?:\\geq|\\leq|\\sim|\\approx|\\gg|\\ll|>|<)\s*$'
)

_GREEK_LETTER = re.compile(r'\\(?:[a-zA-Z]+)')


def normalize_math_prose_boundaries(text: str) -> str:
    result: list[str] = []
    dollar_count = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '$' and i + 1 < len(text) and text[i + 1] == '$':
            result.append('$$')
            i += 2
            continue
        if ch == '$':
            dollar_count += 1
            is_opening = (dollar_count % 2 == 1)
            if is_opening:
                if i > 0 and text[i - 1].isalnum() and text[i - 1] not in '-–—':
                    result.append(' $')
                else:
                    result.append('$')
            else:
                result.append('$')
        else:
            result.append(ch)
        i += 1

    text = ''.join(result)

    def _after_space(m: re.Match) -> str:
        content = m.group(1)
        nxt = m.group(2)

        if nxt.isdigit():
            return f"${content}$ {nxt}"

        if _RELOP_PATTERN.search(content):
            return f"${content}$ {nxt}"

        if _GREEK_LETTER.fullmatch(content.strip()):
            return f"${content}${nxt}"

        if nxt.islower():
            return f"${content}$ {nxt}"

        return f"${content}${nxt}"

    text = re.sub(
        r'(?<!\$)\$([^$]+?)\$(?!\$)([a-zA-Z0-9])',
        _after_space,
        text,
    )
    return text


def normalize_display_math(text: str) -> str:
    text = re.sub(r'\$\$\s+', '$$', text)
    text = re.sub(r'\s+\$\$', '$$', text)
    return text


def normalize_ocr_math_text(text: str) -> str:
    text = normalize_display_math(text)
    text = normalize_inline_math_delimiters(text)
    text = normalize_superscript_citations(text)
    text = normalize_math_prose_boundaries(text)
    return text
