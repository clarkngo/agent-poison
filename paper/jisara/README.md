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
  `.docx` files directly.
- `build_jisara_docx.py` — reads `paper-jisara.md` and populates a fresh
  copy of `ISCAPProceedingsTemplate.docx`.
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

- Body word count (excluding References): 2,712 words (limit: 5,000)
- Abstract: 197 words (limit: 250)
- Keywords: 5 (range: 4-6)
- Margins: 1.0" top/bottom/left/right, single column, US Letter
- Font: Verdana throughout (9pt body, 18pt title, 12pt author block)
- Section headings: centered, bold, ALL CAPS, manually numbered (no Word
  auto-numbering field)
- Table captions: bold, centered, placed below each table, auto-numbered
  by the build script
- References: APA 7th edition, alphabetized, hanging indent
- No headers, footers, page numbers, or footnotes
