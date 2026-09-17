"""Build agent-poison-paper-draft.docx from paper.md, inside the IEEE conference
template's own styles (Heading1-5, Abstract, Keywords, references, tablehead, etc.).

paper.md is the single source of truth for the paper's *content*. This script owns
everything the template needs that markdown can't express: column widths for the
three tables, and the section-break trick that lets a table span the full page width
inside an otherwise two-column body.

Usage: python3 build_docx.py [source.md] [unpacked/word/document.xml]
(run from this directory, against a freshly-unpacked template — see the
README-style comment at the bottom.)
"""

import re
import sys
from xml.sax.saxutils import escape

MD_PATH = sys.argv[1] if len(sys.argv) > 1 else "paper.md"
DOC_PATH = sys.argv[2] if len(sys.argv) > 2 else "unpacked/word/document.xml"

# Column widths (twips) for each table, keyed by its caption text. Falls back to an
# even split of the full-width table area if a caption isn't listed here.
FULLW = 10450  # total twips available at full page width (within margins)
TABLE_COL_WIDTHS = {
    "Scenarios": [2200, 2500, 2750, 3000],
    "Initial single-trial sweep (temperature 0, N=1)": [2200, 3350, 1600, 1650, 1650],
    "Replication protocol (temperature 0.7, 8 trials/cell)": [2200, 3350, 1600, 1650, 1650],
}


# ---------------------------------------------------------------------------
# LOW-LEVEL OOXML HELPERS
# ---------------------------------------------------------------------------

def esc(s):
    return escape(s)


def parse_inline_runs(text, extra_rpr=""):
    """Parse **bold**, *italic*, `code` (monospace) markers into a list of <w:r> runs."""
    tokens = re.split(r'(\*\*.+?\*\*|\*.+?\*|`.+?`)', text)
    runs = []
    for tok in tokens:
        if not tok:
            continue
        if tok.startswith('**') and tok.endswith('**'):
            content = tok[2:-2]
            rpr = f"<w:rPr>{extra_rpr}<w:b/><w:bCs/></w:rPr>"
        elif tok.startswith('*') and tok.endswith('*'):
            content = tok[1:-1]
            rpr = f"<w:rPr>{extra_rpr}<w:i/><w:iCs/></w:rPr>"
        elif tok.startswith('`') and tok.endswith('`'):
            content = tok[1:-1]
            rpr = (f"<w:rPr>{extra_rpr}<w:rFonts w:ascii=\"Courier New\" w:hAnsi=\"Courier New\" "
                   f"w:cs=\"Courier New\"/><w:sz w:val=\"16\"/><w:szCs w:val=\"16\"/></w:rPr>")
        else:
            content = tok
            rpr = f"<w:rPr>{extra_rpr}</w:rPr>" if extra_rpr else ""
        if content == "":
            continue
        runs.append(f"<w:r>{rpr}<w:t xml:space=\"preserve\">{esc(content)}</w:t></w:r>")
    return "".join(runs)


def para(style, text, extra_pPr="", extra_rpr=""):
    runs = parse_inline_runs(text, extra_rpr)
    pstyle = f'<w:pStyle w:val="{style}"/>' if style else ""
    return f'<w:p><w:pPr>{pstyle}{extra_pPr}</w:pPr>{runs}</w:p>'


def heading(level, text):
    return para(f"Heading{level}", text)


def body(text):
    return para("BodyText", text)


def bullets(items):
    return "".join(para("bulletlist", it) for it in items)


def reference(text):
    return para("references", text)


def author_para(lines):
    runs = []
    for i, line in enumerate(lines):
        if i > 0:
            runs.append('<w:r><w:br/></w:r>')
        runs.append(f'<w:r><w:t xml:space="preserve">{esc(line)}</w:t></w:r>')
    return f'<w:p><w:pPr><w:pStyle w:val="Author"/></w:pPr>{"".join(runs)}</w:p>'


def table(headers, rows, col_widths_twips):
    total = sum(col_widths_twips)
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in col_widths_twips)

    def cell(text, w, is_header=False):
        rpr = "<w:b/><w:sz w:val=\"14\"/><w:szCs w:val=\"14\"/>" if is_header else "<w:sz w:val=\"14\"/><w:szCs w:val=\"14\"/>"
        runs = parse_inline_runs(text, extra_rpr=rpr)
        shading = '<w:shd w:val="clear" w:color="auto" w:fill="E7E6E6"/>' if is_header else ""
        return (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{shading}'
                f'<w:tcMar><w:top w:w="20" w:type="dxa"/><w:start w:w="40" w:type="dxa"/>'
                f'<w:bottom w:w="20" w:type="dxa"/><w:end w:w="40" w:type="dxa"/></w:tcMar>'
                f'<w:vAlign w:val="center"/></w:tcPr>'
                f'<w:p><w:pPr><w:spacing w:after="0"/><w:jc w:val="start"/></w:pPr>{runs}</w:p></w:tc>')

    head_row = "<w:tr>" + "".join(cell(h, w, True) for h, w in zip(headers, col_widths_twips)) + "</w:tr>"
    body_rows = ""
    for row in rows:
        body_rows += "<w:tr>" + "".join(cell(str(c), w) for c, w in zip(row, col_widths_twips)) + "</w:tr>"

    return (f'<w:tbl><w:tblPr><w:tblW w:w="{total}" w:type="dxa"/>'
            f'<w:tblBorders>'
            f'<w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
            f'<w:start w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
            f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
            f'<w:end w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
            f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
            f'<w:insideV w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
            f'</w:tblBorders>'
            f'<w:tblLayout w:type="fixed"/>'
            f'<w:tblLook w:val="04A0" w:firstRow="1" w:noHBand="0" w:noVBand="1"/>'
            f'</w:tblPr><w:tblGrid>{grid}</w:tblGrid>{head_row}{body_rows}</w:tbl>')


def table_caption(text):
    return para("tablehead", text)


def spacer():
    return '<w:p><w:pPr><w:spacing w:after="0"/></w:pPr></w:p>'


# ---------------------------------------------------------------------------
# SECTION-BREAK HELPERS (for full-width tables inside the 2-column body)
# ---------------------------------------------------------------------------

SECTPR_2COL = ('<w:sectPr><w:type w:val="continuous"/><w:pgSz w:w="612pt" w:h="792pt" w:code="1"/>'
               '<w:pgMar w:top="54pt" w:right="44.65pt" w:bottom="72pt" w:left="44.65pt" w:header="36pt" '
               'w:footer="36pt" w:gutter="0pt"/><w:cols w:num="2" w:space="18pt"/>'
               '<w:docGrid w:linePitch="360"/></w:sectPr>')

SECTPR_1COL = ('<w:sectPr><w:type w:val="continuous"/><w:pgSz w:w="612pt" w:h="792pt" w:code="1"/>'
               '<w:pgMar w:top="54pt" w:right="44.65pt" w:bottom="72pt" w:left="44.65pt" w:header="36pt" '
               'w:footer="36pt" w:gutter="0pt"/><w:cols w:space="36pt"/>'
               '<w:docGrid w:linePitch="360"/></w:sectPr>')


def close_section(sectpr_xml):
    return f'<w:p><w:pPr>{sectpr_xml}</w:pPr></w:p>'


def full_width_table(caption_text, headers, rows, col_widths_twips):
    """A table that temporarily breaks out to 1-column full width, then resumes 2-column."""
    return (
        close_section(SECTPR_2COL)
        + table_caption(caption_text)
        + table(headers, rows, col_widths_twips)
        + spacer()
        + close_section(SECTPR_1COL)
    )


# ---------------------------------------------------------------------------
# MARKDOWN -> OOXML PARSER
# ---------------------------------------------------------------------------

def parse_pipe_table(lines):
    def split_row(line):
        cells = line.strip().strip("|").split("|")
        return [c.strip() for c in cells]

    header = split_row(lines[0])
    # lines[1] is the "| --- | --- |" separator row; skip it
    rows = [split_row(l) for l in lines[2:] if l.strip()]
    return header, rows


def parse_markdown(path):
    text = open(path, encoding="utf-8").read()
    lines = text.split("\n")

    # Title: first "% " line
    title = None
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("% "):
            title = lines[i].strip()[2:].strip()
            i += 1
            break
        i += 1

    # Author block: next run of non-blank lines
    while i < len(lines) and not lines[i].strip():
        i += 1
    author_lines = []
    while i < len(lines) and lines[i].strip():
        author_lines.append(lines[i].strip())
        i += 1

    # Skip the blank line(s) between the author block and the first real
    # section so `rest` doesn't start with a stray leading newline -- that
    # extra newline shifted the blank-line block splitter below by one,
    # causing the very first block ("## Abstract") to be mis-split into a
    # leading empty line + "## Abstract" and fall through to plain-paragraph
    # handling instead of being recognized as a heading.
    while i < len(lines) and not lines[i].strip():
        i += 1
    rest = "\n".join(lines[i:])
    blocks = [b for b in re.split(r"\n\s*\n", rest) if b.strip()]

    parts = []
    last_heading = None
    reading_references = False
    pending_table_caption = None

    for block in blocks:
        block_lines = block.split("\n")
        first = block_lines[0]

        if first.startswith("Table: ") and len(block_lines) == 1:
            pending_table_caption = first[len("Table: "):].strip()
            continue

        if first.strip().startswith("|"):
            caption = pending_table_caption or ""
            pending_table_caption = None
            headers, rows = parse_pipe_table(block_lines)
            widths = TABLE_COL_WIDTHS.get(caption) or [FULLW // len(headers)] * len(headers)
            parts.append(full_width_table(caption, headers, rows, widths))
            continue

        if first.startswith("### "):
            parts.append(heading(2, first[4:].strip()))
            last_heading = None
            continue

        if first.startswith("## "):
            htext = first[3:].strip()
            last_heading = htext
            if htext in ("Abstract", "Keywords"):
                continue  # these styles carry their own inline label; no separate heading
            unnumbered_sections = ("References", "Acknowledgment", "Ethical Considerations", "Open Science", "LLM Usage Considerations")
            if htext in unnumbered_sections:
                parts.append(heading(5, htext))
                reading_references = (htext == "References")
            else:
                parts.append(heading(1, htext))
                reading_references = False
            continue

        if all(l.strip().startswith("- ") for l in block_lines if l.strip()):
            items = [l.strip()[2:].strip() for l in block_lines if l.strip()]
            parts.append(bullets(items))
            continue

        if reading_references and all(re.match(r"^\d+\.\s", l.strip()) for l in block_lines if l.strip()):
            for l in block_lines:
                if not l.strip():
                    continue
                ref_text = re.sub(r"^\d+\.\s*", "", l.strip())
                parts.append(reference(ref_text))
            reading_references = False
            continue

        # Plain paragraph (join wrapped lines with a space)
        ptext = " ".join(l.strip() for l in block_lines if l.strip())
        if last_heading == "Abstract":
            parts.append(para("Abstract", "Abstract—" + ptext))
        elif last_heading == "Keywords":
            parts.append(para("Keywords", "Keywords—" + ptext))
        else:
            parts.append(body(ptext))
        last_heading = None

    return title, author_lines, parts


# ---------------------------------------------------------------------------
# SPLICE INTO THE TEMPLATE
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    title, author_lines, parts = parse_markdown(MD_PATH)
    print(f"parsed {len(parts)} content blocks from {MD_PATH}")

    xml = open(DOC_PATH, encoding="utf-8").read()

    body_start = xml.index("<w:body>") + len("<w:body>")
    # End of paragraph 106 in the *original* template (the one embedding the
    # 2-column-closing sectPr) — located by its distinctive rsid signature, which is
    # unique to that single paragraph.
    marker = 'w:rsidSect="00C919A4"'
    marker_idx = xml.index(marker)
    end_of_p106 = xml.index("</w:p>", marker_idx) + len("</w:p>")

    head = xml[:body_start]
    tail = xml[end_of_p106:]

    # The template's section-1 sectPr (title page, 1-column, titlePg) is the FIRST
    # sectPr in the file; reuse it verbatim to keep the title page single-column.
    sect1_xml = re.search(r"<w:sectPr.*?</w:sectPr>", xml[body_start:], re.S).group(0)

    new_middle = (
        para("papertitle", title, extra_pPr='<w:spacing w:before="5pt" w:after="5pt"/>')
        + author_para(author_lines)
        + close_section(sect1_xml)
        + "".join(parts)
    )

    # The document-level trailing sectPr (in `tail`) governs the LAST section of the
    # document. In the original template that section was empty filler, so it was
    # 1-column; in our rebuilt paper it now holds the back half of Results, Discussion,
    # Limitations, Conclusion, and References, so it must be 2-column like the rest of
    # the body.
    tail = tail.replace('<w:cols w:space="36pt"/>', '<w:cols w:num="2" w:space="18pt"/>', 1)

    new_xml = head + new_middle + tail
    open(DOC_PATH, "w", encoding="utf-8").write(new_xml)
    print("wrote", DOC_PATH, "new length", len(new_xml))

    # Scrub the template's own leftover author metadata (docProps/core.xml carried
    # "IEEE" / a stale editor's name from the original template file) and replace it
    # with neutral values reflecting this document, not either the template author or
    # us specifically -- avoids leaking an unrelated third party's name in our output.
    unpack_root = DOC_PATH.split("/word/")[0]
    core_path = f"{unpack_root}/docProps/core.xml"
    core_xml = open(core_path, encoding="utf-8").read()
    core_xml = re.sub(r"<dc:title>.*?</dc:title>", f"<dc:title>{title}</dc:title>", core_xml)
    core_xml = re.sub(r"<dc:creator>.*?</dc:creator>", "<dc:creator></dc:creator>", core_xml)
    core_xml = re.sub(r"<cp:lastModifiedBy>.*?</cp:lastModifiedBy>", "<cp:lastModifiedBy></cp:lastModifiedBy>", core_xml)
    open(core_path, "w", encoding="utf-8").write(core_xml)

    app_path = f"{unpack_root}/docProps/app.xml"
    app_xml = open(app_path, encoding="utf-8").read()
    app_xml = re.sub(r"<vt:lpstr>Paper Title.*?</vt:lpstr>", f"<vt:lpstr>{title}</vt:lpstr>", app_xml)
    app_xml = re.sub(r"<Company>.*?</Company>", "<Company></Company>", app_xml)
    open(app_path, "w", encoding="utf-8").write(app_xml)
    print("scrubbed docProps metadata")
