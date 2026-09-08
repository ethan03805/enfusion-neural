"""Build a portable static documentation site from canonical Markdown."""
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
from urllib.parse import urlsplit, unquote
import markdown

ROOT=Path(__file__).resolve().parents[1]
PAGES=[('index','Overview'),('vision','Vision'),('getting-started','Get started'),
       ('architecture','Architecture'),('integration','Enfusion integration'),
       ('evidence','Evidence'),('evaluation','Evaluation'),('roadmap','Roadmap'),
       ('decisions','Decisions'),('status','Handoff'),('contributing','Contributing'),('sources','Sources')]
REPO='https://github.com/ethan03805/enfusion-neural'


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.ids=set()
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs: self.ids.add(attrs['id'])
        if tag in ('a','link') and 'href' in attrs: self.links.append(attrs['href'])
        if tag in ('img','script') and 'src' in attrs: self.links.append(attrs['src'])


def main():
    output=ROOT/'dist'; output.mkdir(exist_ok=True)
    expected={slug+'.html' for slug,_ in PAGES}|{'style.css','.nojekyll'}
    stale={path.name for path in output.iterdir()}-expected
    if stale: raise RuntimeError('Unexpected files in dist; review before publishing: '+str(sorted(stale)))
    for position,(slug,label) in enumerate(PAGES):
        raw=(ROOT/'docs'/f'{slug}.md').read_text(encoding='utf-8')
        content=markdown.markdown(raw,extensions=['fenced_code','tables','toc'])
        def rewrite(match):
            href=match.group(1)
            if not urlsplit(href).scheme: href=re.sub(r'\.md(?=#|$)','.html',href)
            return 'href="'+href+'"'
        content=re.sub(r'href="([^"]+)"',rewrite,content)
        content=content.replace('<table>','<div class="table-wrap"><table>').replace('</table>','</table></div>')
        nav=''.join(f'<a href="{name}.html"'+(' aria-current="page"' if name==slug else '')+f'>{escape(text)}</a>' for name,text in PAGES)
        brand='<a class="brand" href="index.html"><span class="mark" aria-hidden="true">EN</span>Enfusion Neural</a>'
        nextpage=PAGES[position+1] if position+1<len(PAGES) else PAGES[0]
        title='Enfusion Neural' if slug=='index' else label+' · Enfusion Neural'
        page=f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title><meta name="description" content="Enfusion Neural engineering documentation: faithful photorealism, AMD GPU experiments and reproducible evidence.">
<link rel="stylesheet" href="style.css"></head><body>
<a class="skip" href="#content">Skip to content</a>
<aside class="sidebar">{brand}<nav aria-label="Documentation">{nav}</nav><div class="rail-footer"><a href="{REPO}">GitHub ↗</a><div class="version">Research / v0.1</div></div></aside>
<header class="mobile"><div class="mobile-head">{brand}<a href="{REPO}">GitHub ↗</a></div><details><summary>Contents</summary><nav aria-label="Mobile documentation">{nav}</nav></details></header>
<main><div class="topline"><span>Documentation</span><a href="{REPO}/blob/main/docs/{slug}.md">Page source ↗</a></div>
<article id="content">{content}</article>
<footer class="page-footer"><span>Independent research · MIT</span><a href="{nextpage[0]}.html">{escape(nextpage[1])} →</a></footer></main></body></html>'''
        (output/f'{slug}.html').write_text(page,encoding='utf-8')
    shutil.copyfile(ROOT/'site/style.css',output/'style.css')
    (output/'.nojekyll').write_text('')
    parsed={}
    for page in output.glob('*.html'):
        parser=Links(); parser.feed(page.read_text(encoding='utf-8')); parsed[page]=parser
    for page,parser in parsed.items():
        for href in parser.links:
            link=urlsplit(href)
            if link.scheme or link.netloc: continue
            target=(page.parent/unquote(link.path)).resolve() if link.path else page.resolve()
            if not target.is_relative_to(output.resolve()) or not target.is_file():
                raise RuntimeError(f'Broken or escaping link in {page.name}: {href}')
            if link.fragment and (target not in parsed or unquote(link.fragment) not in parsed[target].ids):
                raise RuntimeError(f'Broken anchor in {page.name}: {href}')
    print(f'Built {len(PAGES)} pages; all internal file links and anchors valid.')


if __name__=='__main__': main()
