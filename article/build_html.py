#!/usr/bin/env python3
"""Render the article to HTML that survives a paste into Medium.

Medium does not parse Markdown on paste. Give it raw Markdown and its language
detector decides the whole thing is source code, wraps it in a code block, and
then refuses to publish because the post has "no words but an image". Give it
rendered HTML from a browser instead and it maps the tags onto its own editor:
h1/h2 become headings, strong/em survive, links survive, and img tags are
fetched and re-hosted.

So: run this, open the output in a browser, select all, copy, paste.

The GIF placeholders in the Markdown are replaced with img tags pointing at raw
GitHub URLs, which is what lets Medium pull the images in rather than making you
upload each one by hand.

    python3 article/build_html.py                                  # Medium
    python3 article/build_html.py article/laundered-text-linkedin.md   # LinkedIn

LinkedIn is fussier than Medium: it takes the pasted text and headings, but will
not fetch remote images, so upload the two GIFs by hand where the captions sit.
"""
import os
import re

import markdown

BASE = os.path.dirname(os.path.abspath(__file__))

RAW = "https://raw.githubusercontent.com/nisaharan/ai-watermarks-3d/main/gifs/"

# Medium's editor ignores most CSS, so this only has to look right in the
# browser tab you copy from.
SHELL = """<!doctype html>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ max-width: 42rem; margin: 3rem auto; padding: 0 1.5rem;
         font: 18px/1.6 Georgia, serif; color: #222; }}
  h1 {{ font-size: 2.1rem; line-height: 1.2; }}
  h2 {{ font-size: 1.4rem; margin-top: 2.4rem; }}
  img {{ width: 100%; height: auto; display: block; margin: 1.6rem 0 0.4rem; }}
  .cap {{ font-size: 0.85rem; color: #666; text-align: center; font-style: italic; }}
  hr {{ border: 0; border-top: 1px solid #ddd; margin: 2.5rem 0; }}
  .note {{ background: #fffbe6; border: 1px solid #f0e0a0; padding: 1rem 1.2rem;
          font-family: system-ui, sans-serif; font-size: 0.9rem; line-height: 1.5; }}
</style>
<div class="note"><strong>Not part of the article.</strong> Select everything
below the line, copy, and paste into a fresh Medium draft. Medium will pull the
three GIFs in from GitHub on its own. Delete this box from the draft afterwards,
along with the title line if Medium has already used it as the headline.</div>
<hr>
{body}
"""


def main():
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "laundered-text.md")
    out = os.path.splitext(src)[0] + ".html"
    md = open(src, encoding="utf-8").read()

    # <!-- GIF 06_sentence_skyline.gif --> followed by an italic caption line
    def gif(m):
        name = m.group(1).strip()
        cap = (m.group(2) or "").strip().strip("*")
        img = f'<img src="{RAW}{name}" alt="{cap or name}">'
        return img + (f'\n<p class="cap">{cap}</p>' if cap else "")

    md = re.sub(r"<!--\s*GIF\s+([\w.]+)\s*-->\n\*([^\n]*)\*", gif, md)
    md = re.sub(r"<!--\s*GIF\s+([\w.]+)\s*-->", lambda m: gif(m), md)

    html = markdown.markdown(md, extensions=["extra", "sane_lists"])
    title = re.search(r"<h1>(.*?)</h1>", html)
    open(out, "w", encoding="utf-8").write(
        SHELL.format(title=re.sub("<[^>]+>", "", title.group(1)) if title else "article",
                     body=html))

    imgs = len(re.findall(r"<img ", html))
    words = len(re.findall(r"\w+", re.sub("<[^>]+>", " ", html)))
    print(f"wrote {out}\n  {words} words, {imgs} images, "
          f"{len(re.findall(r'<h2>', html))} section headings")
    print("  open it, select all below the rule, copy, paste into Medium")


if __name__ == "__main__":
    main()
