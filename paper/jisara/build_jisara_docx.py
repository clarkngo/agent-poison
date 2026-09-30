"""Build a JISARA/ISCAP-formatted .docx from paper-jisara.md, inside the real
ISCAPProceedingsTemplate.docx (single column, Verdana, direct run-level
formatting -- the template avoids named styles per its own guidelines).

Usage: python3 build_jisara_docx.py [--final]
  (no flag)  blind initial-submission version: author block left as 5 blank
             lines, per "Initial Submission: Leave space ... for Author
             Information to be inserted later."
  --final    fills in the real author block (both authors), for use once
             the paper is accepted and a Journal/Conference invite asks for
             the non-blind version.

Run from this directory (paper/jisara/) against a freshly-unpacked
`unpacked/word/document.xml` copied from ISCAPProceedingsTemplate.docx.
"""

import re
import sys
from xml.sax.saxutils import escape

MD_PATH = "paper-jisara.md"
DOC_PATH = "unpacked/word/document.xml"
FINAL = "--final" in sys.argv

FONT = "Verdana"

AUTHORS = [
    {"name": "Clark Ngo", "email": "ngoclarkjason@cityuniversity.edu",
     "org": "City University of Seattle", "loc": "Seattle, WA, USA"},
    {"name": "Sam Chung", "email": "chungsam@cityu.edu",
     "org": "City University of Seattle", "loc": "Seattle, WA, USA"},
]

# Column widths (twips) for the two tables, single column body is ~9360 twips
# wide (12240 page width - 2*1440 margins).
TABLE_COL_WIDTHS = {
    "Scenarios": [2200, 2000, 2600, 2560],
    "Defenses": [2400, 6960],
    "Initial single-trial sweep (temperature 0, n=1)": [2200, 3160, 2000, 2000],
    "Replication protocol (temperature 0.7, 8 trials/cell)": [2200, 3160, 2000, 2000],
}


def esc(s):
    return escape(s)


def rpr(bold=False, italic=False, sz=18, extra=""):
    b = "<w:b/><w:bCs/>" if bold else ""
    i = "<w:i/><w:iCs/>" if italic else ""
    return (f'<w:rPr><w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:cs="{FONT}"/>'
            f'{b}{i}<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>{extra}</w:rPr>')


def parse_inline_runs(text, sz=18, base_bold=False, base_italic=False):
    """Parse **bold** / *italic* markers into <w:r> runs, all in Verdana at `sz`."""
    tokens = re.split(r'(\*\*.+?\*\*|\*.+?\*)', text)
    runs = []
    for tok in tokens:
        if not tok:
            continue
        if tok.startswith('**') and tok.endswith('**'):
            content, bold, italic = tok[2:-2], True, base_italic
        elif tok.startswith('*') and tok.endswith('*'):
            content, bold, italic = tok[1:-1], base_bold, True
        else:
            content, bold, italic = tok, base_bold, base_italic
        if content == "":
            continue
        runs.append(f'<w:r>{rpr(bold, italic, sz)}<w:t xml:space="preserve">{esc(content)}</w:t></w:r>')
    return "".join(runs)


def para(text, sz=18, bold=False, italic=False, jc="both", extra_pPr=""):
    runs = parse_inline_runs(text, sz=sz, base_bold=bold, base_italic=italic)
    jc_xml = f'<w:jc w:val="{jc}"/>' if jc else ""
    # CT_PPrBase child order requires <w:ind> before <w:jc>.
    return f'<w:p><w:pPr>{extra_pPr}{jc_xml}</w:pPr>{runs}</w:p>'


def blank(sz=18):
    return f'<w:p><w:pPr></w:pPr><w:r>{rpr(sz=sz)}<w:t></w:t></w:r></w:p>'


def heading(text, level=1):
    """Major (level 1, ALL CAPS centered) or sub (level 2, initial-caps left) heading."""
    if level == 1:
        return para(text.upper(), sz=18, bold=True, jc="center")
    return para(text, sz=18, bold=True, jc="left")


def reference(text):
    hang = '<w:ind w:left="432" w:hanging="432"/>'
    return para(text, sz=18, jc="both", extra_pPr=hang)


def table_caption(text):
    return para(text, sz=18, bold=True, jc="center")


def table(headers, rows, col_widths):
    total = sum(col_widths)
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in col_widths)

    def cell(text, w, is_header=False):
        runs = parse_inline_runs(text, sz=18, base_bold=is_header)
        return (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>'
                f'<w:tcMar><w:top w:w="40" w:type="dxa"/><w:start w:w="60" w:type="dxa"/>'
                f'<w:bottom w:w="40" w:type="dxa"/><w:end w:w="60" w:type="dxa"/></w:tcMar>'
                f'<w:vAlign w:val="center"/></w:tcPr>'
                f'<w:p><w:pPr><w:jc w:val="start"/></w:pPr>{runs}</w:p></w:tc>')

    head_row = "<w:tr>" + "".join(cell(h, w, True) for h, w in zip(headers, col_widths)) + "</w:tr>"
    body_rows = "".join(
        "<w:tr>" + "".join(cell(str(c), w) for c, w in zip(row, col_widths)) + "</w:tr>"
        for row in rows
    )
    return (f'<w:tbl><w:tblPr><w:tblW w:w="{total}" w:type="dxa"/>'
            f'<w:tblBorders>'
            f'<w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
            f'<w:start w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
            f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
            f'<w:end w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
            f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
            f'<w:insideV w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
            f'</w:tblBorders><w:tblLayout w:type="fixed"/>'
            f'<w:tblLook w:val="04A0" w:firstRow="1" w:noHBand="0" w:noVBand="1"/>'
            f'</w:tblPr><w:tblGrid>{grid}</w:tblGrid>{head_row}{body_rows}</w:tbl>')


def author_block_blind():
    """Five blank lines, per the template's own instruction for initial (blind) submission."""
    return "".join(blank(sz=24) for _ in range(5))


def author_block_final():
    parts = []
    for i, a in enumerate(AUTHORS):
        if i > 0:
            parts.append(blank(sz=24))
        parts.append(para(a["name"], sz=24, jc="center"))
        parts.append(para(a["email"], sz=24, jc="center"))
        parts.append(para(a["org"], sz=24, jc="center"))
        parts.append(para(a["loc"], sz=24, jc="center"))
    return "".join(parts)


def parse_pipe_table(lines):
    def split_row(line):
        return [c.strip() for c in line.strip().strip("|").split("|")]
    header = split_row(lines[0])
    rows = [split_row(l) for l in lines[2:] if l.strip()]
    return header, rows


def parse_markdown(path):
    text = open(path, encoding="utf-8").read()
    lines = text.split("\n")

    title = None
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("% "):
            title = lines[i].strip()[2:].strip()
            i += 1
            break
        i += 1
    while i < len(lines) and not lines[i].strip():
        i += 1

    rest = "\n".join(lines[i:])
    blocks = [b for b in re.split(r"\n\s*\n", rest) if b.strip()]

    parts = []
    last_heading = None
    reading_references = False
    pending_table_caption = None
    table_num = 0

    for block in blocks:
        block_lines = block.split("\n")
        first = block_lines[0]

        if first.startswith("Table: ") and len(block_lines) == 1:
            pending_table_caption = first[len("Table: "):].strip()
            continue

        if first.strip().startswith("|"):
            caption = pending_table_caption or ""
            pending_table_caption = None
            table_num += 1
            headers, rows = parse_pipe_table(block_lines)
            widths = TABLE_COL_WIDTHS.get(caption) or [9360 // len(headers)] * len(headers)
            parts.append(table(headers, rows, widths))
            parts.append(table_caption(f"Table {table_num}. {caption}" if caption else f"Table {table_num}."))
            parts.append(blank())
            continue

        if first.startswith("### "):
            parts.append(blank())
            parts.append(heading(first[4:].strip(), level=2))
            parts.append(blank())
            last_heading = None
            continue

        if first.startswith("## "):
            htext = first[3:].strip()
            last_heading = htext
            if htext == "Abstract":
                parts.append(para("Abstract", sz=18, bold=True, jc="center"))
                continue
            if htext == "10. REFERENCES":
                parts.append(blank())
                parts.append(heading(htext, level=1))
                parts.append(blank())
                reading_references = True
            else:
                parts.append(blank())
                parts.append(heading(htext, level=1))
                parts.append(blank())
                reading_references = False
            continue

        if all(l.strip().startswith("- ") for l in block_lines if l.strip()):
            items = [l.strip()[2:].strip() for l in block_lines if l.strip()]
            parts.append(para("; ".join(items)))
            continue

        if reading_references and all(re.match(r"^\S", l.strip()) for l in block_lines if l.strip()):
            for l in block_lines:
                if not l.strip():
                    continue
                parts.append(reference(l.strip()))
            continue

        ptext = " ".join(l.strip() for l in block_lines if l.strip())
        if last_heading == "Abstract":
            parts.append(para(ptext, sz=18, jc="both"))
        elif ptext.startswith("Keywords:"):
            kw = ptext[len("Keywords:"):].strip()
            parts.append(para(f"**Keywords:** {kw}", sz=18, jc="both"))
        else:
            parts.append(para(ptext, sz=18, jc="both"))
        last_heading = None

    return title, parts


if __name__ == "__main__":
    title, parts = parse_markdown(MD_PATH)
    print(f"parsed {len(parts)} content blocks from {MD_PATH} ({'FINAL' if FINAL else 'BLIND'} author block)")

    xml = open(DOC_PATH, encoding="utf-8").read()
    body_start = xml.index("<w:body>") + len("<w:body>")
    sect_start = xml.rindex("<w:sectPr")

    head = xml[:body_start]

    author_block = author_block_final() if FINAL else author_block_blind()

    new_body = (
        blank(sz=36)  # 18pt blank line before title, 1.0in top margin per guideline
        + para(title, sz=36, jc="center")
        + blank(sz=24)
        + author_block
        + blank(sz=18)
        + "".join(parts)
    )

    # The template's final sectPr sits as a direct child of <w:body>, not
    # wrapped in a paragraph; splice our new content in before it, unchanged.
    original_tail = xml[sect_start:]
    assert original_tail.startswith("<w:sectPr") and original_tail.rstrip().endswith("</w:document>")
    new_xml = head + new_body + original_tail

    open(DOC_PATH, "w", encoding="utf-8").write(new_xml)
    print("wrote", DOC_PATH, "new length", len(new_xml))
