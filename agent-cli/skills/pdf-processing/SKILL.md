---
name: pdf-processing
description: Use for any task involving PDF files — extracting text or tables, merging or splitting PDFs, creating new PDFs, adding watermarks, or reading scanned documents via OCR. Trigger whenever a .pdf file is mentioned or requested as output.
---

# PDF Processing

## Extracting text

`pdfplumber` preserves layout better than `pypdf` for real-world documents:

```python
import pdfplumber

with pdfplumber.open("input.pdf") as pdf:
    text = "\n".join(page.extract_text() or "" for page in pdf.pages)
```

## Extracting tables

```python
with pdfplumber.open("input.pdf") as pdf:
    for page in pdf.pages:
        for table in page.extract_tables():
            print(table)   # list of rows, each a list of cell strings
```

## Merging PDFs

```python
from pypdf import PdfWriter, PdfReader

writer = PdfWriter()
for f in ["a.pdf", "b.pdf"]:
    for page in PdfReader(f).pages:
        writer.add_page(page)
writer.write("merged.pdf")
```

## Splitting a PDF — one file per page

```python
reader = PdfReader("input.pdf")
for i, page in enumerate(reader.pages):
    writer = PdfWriter()
    writer.add_page(page)
    writer.write(f"page_{i+1}.pdf")
```

## Creating a new PDF — worked example (copy this shape for any cheat-sheet or reference PDF)

Two things matter more than the reportlab API itself: **you handle page breaks
yourself** — reportlab does nothing automatic, text past the bottom margin just
silently doesn't appear — and **stay ASCII-safe** — reportlab's built-in fonts don't
reliably render smart quotes, em-dashes, or emoji; they render as a box glyph instead,
with no error raised.

```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

def build_cheat_sheet(filename, title, sections):
    """sections: list of (heading, [code_lines]) tuples"""
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    y = height - inch

    c.setFont("Helvetica-Bold", 18)
    c.drawString(inch, y, title)
    y -= 0.4 * inch

    for heading, raw_lines in sections:
        # Clean up lines upfront so page break math is accurate
        lines = []
        for raw_line in raw_lines:
            lines.extend(str(raw_line).replace('\t', '    ').split('\n'))

        if y < inch:                     # new page before we run off the bottom
            c.showPage()
            y = height - inch

        c.setFont("Helvetica-Bold", 13)
        c.drawString(inch, y, heading)
        y -= 0.25 * inch

        c.setFont("Courier", 10)         # monospace for code, also ASCII-safe
        for line in lines:
            if y < inch:
                c.showPage()
                y = height - inch
            c.drawString(inch + 0.2 * inch, y, line)
            y -= 0.18 * inch
        y -= 0.2 * inch

    c.save()


sections = [
    ("Variables", ['name = "Alice"   # str', 'age = 30         # int']),
    ("Control Flow", ['if x > 0:', '    print("positive")']),
]
build_cheat_sheet("example.pdf", "Example Cheat Sheet", sections)
```

**Rules for the content you put in `sections`:**
- Use `'` and `"` (straight quotes) — never curly/smart quotes
- Use `-` or `--` — never an em-dash `—` or en-dash `–`
- No emoji or symbol characters — write "Note:" not "📝"
- Wrap long lines yourself before passing them in — `drawString` does not wrap text
- Never include HTML tags or markdown syntax (`` `code` ``, `**bold**`, `<code>`) in
  the strings — `drawString` renders characters literally, it does not interpret or
  strip markup. Plain text only.

## Adding design — colors, a header bar, section accents

Design costs generation tokens only when the *model* has to invent the styling logic
line by line. Put the styling inside the fixed function instead — same 3-argument
call signature as the plain version above, so the model's job stays "supply content,"
not "compute colors." Verified: 1 page, clean text extraction, no glyph corruption.

```python
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas

# Fixed palette — decided once, here, not regenerated per document
HEADER_BG = colors.HexColor("#1F2937")   # dark slate
HEADER_FG = colors.white
HEADING_FG = colors.HexColor("#2563EB")  # blue accent
CODE_BG = colors.HexColor("#F3F4F6")     # light gray
CODE_FG = colors.HexColor("#111827")     # near-black
RULE = colors.HexColor("#E5E7EB")        # thin divider


def build_cheat_sheet_styled(filename, title, sections):
    """Same signature as build_cheat_sheet — sections: list of (heading, [code_lines])."""
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    def draw_header():
        c.setFillColor(HEADER_BG)
        c.rect(0, height - 0.75 * inch, width, 0.75 * inch, fill=1, stroke=0)
        c.setFillColor(HEADER_FG)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(inch, height - 0.5 * inch, title)

    draw_header()
    y = height - 1.15 * inch

    for heading, raw_lines in sections:
        # Clean up lines upfront so block_height and page breaks are accurate
        lines = []
        for raw_line in raw_lines:
            lines.extend(str(raw_line).replace('\t', '    ').split('\n'))

        block_height = len(lines) * 0.18 * inch
        needed = 0.35 * inch + block_height + 0.3 * inch

        if y - needed < 0.6 * inch:      # whole section must fit, not just the next line —
            c.showPage()                  # a colored block cut across a page break looks broken
            draw_header()
            y = height - 1.15 * inch

        c.setFillColor(HEADING_FG)
        c.rect(inch, y - 0.03 * inch, 0.06 * inch, 0.22 * inch, fill=1, stroke=0)  # accent bar
        c.setFont("Helvetica-Bold", 13)
        c.setFillColor(colors.black)
        c.drawString(inch + 0.15 * inch, y, heading)
        y -= 0.32 * inch

        c.setFillColor(CODE_BG)          # code block background, drawn before the text
        c.rect(inch, y - block_height + 0.12 * inch, width - 2 * inch, block_height, fill=1, stroke=0)

        c.setFillColor(CODE_FG)
        c.setFont("Courier", 10)
        for line in lines:
            c.drawString(inch + 0.15 * inch, y, line)
            y -= 0.18 * inch

        y -= 0.15 * inch
        c.setStrokeColor(RULE)
        c.setLineWidth(0.5)
        c.line(inch, y, width - inch, y)
        y -= 0.25 * inch

    c.save()
```

Use `build_cheat_sheet` for a quick/plain reference, `build_cheat_sheet_styled` when the
output is meant to be read or shared, not just generated. Same ASCII-safety rules apply
to both — color doesn't fix a font-encoding problem, it just makes the box glyph more
visible.

## Scanned PDFs — no extractable text, needs OCR

```python
from pdf2image import convert_from_path
import pytesseract

for img in convert_from_path("scanned.pdf"):
    print(pytesseract.image_to_string(img))
```

## Command-line alternative (no Python needed, already in the image)

```bash
pdftotext -layout input.pdf output.txt      # extract text
qpdf --empty --pages a.pdf b.pdf -- out.pdf # merge
qpdf input.pdf --pages . 1-5 -- out.pdf     # first 5 pages
```

## Workflow — generate, verify content quality, retry if it's thin

Opening without error isn't enough. A PDF can be perfectly valid and still be nearly
empty, or cut off mid-section — this happens when generation runs out of output
tokens partway through. Check the actual content, not just that the file exists.

```python
import re
import pdfplumber

def verify_pdf_quality(path: str, min_words: int = 150) -> str:
    with pdfplumber.open(path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    word_count = len(text.split())
    bad_chars = "\ufffd" in text or "■" in text        # tofu / replacement glyphs
    has_markup = bool(re.search(r"</?\w+>", text))      # <code>, <b>, <div> etc leaked through

    issues = []
    if word_count < min_words:
        issues.append(f"Only {word_count} words — content is likely incomplete or truncated")
    if bad_chars:
        issues.append("Found replacement/box glyphs — a non-ASCII character broke the font encoding")
    if has_markup:
        issues.append("Found HTML-like tags in extracted text — markup leaked into content instead of plain text")

    return "FAILED: " + " | ".join(issues) if issues else f"PASSED: {word_count} words, no encoding or markup issues"
```

1. `write_file` the generation script into the mounted workspace
2. `bash("python script.py")` to run it
3. `bash("python -c \"...verify_pdf_quality('output.pdf')...\"")` — run the check above
4. **If it says FAILED** — read the specific reason, fix that exact problem (add the
   missing sections if too short, remove the offending character if encoding broke),
   regenerate, verify again. Cap this at 2 retries — if it still fails after that,
   report the specific failure instead of claiming the task is done.
5. Only report the task complete after a PASSED result — never after the script
   just exits with code 0.