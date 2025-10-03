import fitz, re
from pathlib import Path

p = Path('tests') / 'snake_test.pdf'
if not p.exists():
    print('snake_test.pdf not found, please run the test first to generate it')
    raise SystemExit(1)

doc = fitz.open(str(p))
page = doc[0]
chars = page.get_text('chars')

norm_page_chars = []
norm_map = []
prev_space = False
skip_space = False
for idx, (x0,y0,x1,y1,ch,b,l,sp) in enumerate(chars):
    c = ch.lower()
    if c == '-':
        skip_space = True
        continue
    if (not c.isalnum()) or c.isspace():
        if skip_space:
            skip_space = False
            continue
        if not prev_space and norm_page_chars:
            norm_page_chars.append(' ')
            norm_map.append(idx)
        prev_space = True
        continue
    prev_space = False
    skip_space = False
    norm_page_chars.append(c)
    norm_map.append(idx)

norm_page = ''.join(norm_page_chars).strip()
print('NORM_PAGE:')
print(norm_page)
print('--- END NORM_PAGE ---\n')

content = ("A concept is a plug-and-play device with plugs at both ends. It provides an interface between the informational models and content-specific computations of special-purpose systems, at one end, and the general-purpose compositionality and content-general reasoning of deliberate thought, at the other")
content_norm = content.lower().replace('-', '')
content_norm = re.sub(r"[^a-z0-9]+", " ", content_norm)
content_norm = re.sub(r"\s+", " ", content_norm).strip()
print('CONTENT_NORM:')
print(content_norm)
print('--- END CONTENT_NORM ---\n')
print('FOUND INDEX:', norm_page.find(content_norm))

doc.close()
