# JISARA / ISCAP submission

Formatted per the real [ISCAP Proceedings Template](https://iscap.us/docs/submissions/ISCAPProceedingsTemplate.docx)
and [submission guidelines](https://iscap.us/docs/submissions/ISCAPProceedingsSubmissions.pdf)
(both mirrored here), which JISARA shares with the CONISAR conference track.
This is a different format from the IEEE template used for the SaTML
version in `../`: single column, Verdana 9pt body text, 1" margins all
around, manually-typed section numbers (the guidelines explicitly say not
to rely on Word's auto-numbering), captions placed *below* tables, and
APA 7th-edition in-text citations and references instead of numbered
brackets.

## Files

- `paper-jisara.md` — the content source (Markdown). Edit this, not the
  `.docx` files directly. A `![caption](path.png)` line embeds a figure at
  that point, centered at full text width with an auto-numbered "Figure N."
  caption below it, matching the table-caption convention.
- `figure1-process-flow.svg` / `figure1-process-flow.png` — the Section 3
  process-flow diagram (source SVG and the rasterized PNG actually embedded
  in the document). Regenerate the PNG with `rsvg-convert -w 1800 -h 1200
  --keep-aspect-ratio -b white figure1-process-flow.svg -o
  figure1-process-flow.png` after editing the SVG.
- `build_jisara_docx.py` — reads `paper-jisara.md` and populates a fresh
  copy of `ISCAPProceedingsTemplate.docx`, embedding any referenced images
  into `word/media/` and registering them in the package's relationships
  and content-types parts.
- `agent-poison-jisara-BLIND.docx` — **the file to actually submit.**
  Author information is left as blank placeholder lines in the document
  body, per the template's own instruction ("Initial Submission: Leave
  space ... for Author Information to be inserted later"). JISARA/ISCAP
  is double-blind; real author identity goes into the submission portal
  separately, not into the manuscript body.
- `agent-poison-jisara-FINAL.docx` — the same content with both authors'
  real names, emails, and affiliation filled in. This is for later, once
  a paper is accepted and the conference/journal asks for the non-blind
  version — do not submit this one for initial review.

## Rebuilding after an edit to `paper-jisara.md`

```bash
cd paper/jisara
rm -rf unpacked && unzip -q ISCAPProceedingsTemplate.docx -d unpacked && find unpacked -type l -delete
python3 build_jisara_docx.py            # blind version -> unpacked/word/document.xml
(cd unpacked && zip -Xrq ../agent-poison-jisara-BLIND.docx . -x '.*')

rm -rf unpacked && unzip -q ISCAPProceedingsTemplate.docx -d unpacked && find unpacked -type l -delete
python3 build_jisara_docx.py --final    # final (real author block) version
(cd unpacked && zip -Xrq ../agent-poison-jisara-FINAL.docx . -x '.*')

rm -rf unpacked
```

## Compliance checked against the actual rendered document

- Body word count (excluding References): 2,712 words (limit: 5,000) —
  unaffected by the embedded figure, since it adds no body text
- Abstract: 197 words (limit: 250)
- Keywords: 5 (range: 4-6)
- Margins: 1.0" top/bottom/left/right, single column, US Letter
- Font: Verdana throughout (9pt body, 18pt title, 12pt author block)
- Section headings: centered, bold, ALL CAPS, manually numbered (no Word
  auto-numbering field)
- Table captions: bold, centered, placed below each table, auto-numbered
  by the build script
- Figure 1 (Section 3, process-flow diagram): centered, full text width,
  with a bold centered "Figure 1." caption below it, same convention as
  the table captions
- References: APA 7th edition, alphabetized, hanging indent
- No headers, footers, page numbers, or footnotes
- Verified end-to-end: exported both `.docx` variants to PDF (6 pages
  each), confirmed the figure renders correctly on page 3, and confirmed
  the BLIND variant's author block is genuinely blank while FINAL shows
  both authors
