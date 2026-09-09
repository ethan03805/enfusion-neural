"""Build a portable static documentation site from canonical Markdown."""
from html import escape
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
import shutil
from urllib.parse import urlsplit, unquote
import markdown
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
PAGES=[('index','Overview'),('vision','Objectives'),('getting-started','Get started'),('reference-scenes','Reference scenes'),('capture-controls','Capture controls'),('material-room','Material room'),('lighting-study','Lighting study'),('lighting-motion','Scene transfer & motion'),('lighting-diversity','Scene diversity'),('arma-scenes','Arma scenes'),('comparisons','Comparisons'),
       ('architecture','Architecture'),('integration','Enfusion integration'),('feasibility','Technical feasibility'),
       ('evidence','Evidence'),('evaluation','Evaluation'),('roadmap','Roadmap'),
       ('decisions','Decisions'),('status','Handoff'),('contributing','Contributing'),('sources','Sources')]
REPO='https://github.com/ethan03805/enfusion-neural'


def copy_media(output):
    source = ROOT/'docs/media'
    manifest = json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    if manifest['schema_version'] != 1:
        raise RuntimeError('Unsupported media manifest')
    expected = {'manifest.json'}
    for entry in manifest['images']:
        name = entry['file']
        if not re.fullmatch(r'[a-z0-9-]+\.png', name) or name in expected:
            raise RuntimeError('Invalid or duplicate media filename: '+name)
        expected.add(name)
        path = source/name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise RuntimeError('Media differs from reviewed manifest: '+name)
        if path.stat().st_size != entry['bytes']:
            raise RuntimeError('Media byte count differs: '+name)
        with Image.open(path) as image:
            if image.format != 'PNG' or list(image.size) != entry['dimensions']:
                raise RuntimeError('Media dimensions or format differ: '+name)
            image.verify()
        record = (ROOT/entry['source_record']).resolve()
        if not record.is_relative_to((ROOT/'evidence').resolve()) or not record.is_file():
            raise RuntimeError('Missing or invalid media source record: '+name)
    for entry in manifest.get('videos',[]):
        name = entry['file']
        if not re.fullmatch(r'[a-z0-9-]+\.mp4',name) or name in expected:
            raise RuntimeError('Invalid or duplicate video filename')
        expected.add(name)
        path = source/name
        if path.is_symlink() or path.stat().st_size != entry['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise RuntimeError('Video differs from reviewed manifest: '+name)
        with path.open('rb') as stream:
            if stream.read(12)[4:8] != b'ftyp': raise RuntimeError('Video is not an MP4 container')
        record = (ROOT/entry['source_record']).resolve()
        if not record.is_relative_to((ROOT/'evidence').resolve()) or not record.is_file():
            raise RuntimeError('Missing video source record')
    if {path.name for path in source.iterdir()} != expected:
        raise RuntimeError('Review unexpected files in docs/media before publishing')
    destination = output/'media'
    if destination.is_symlink():
        raise RuntimeError('Media output must not be a symlink')
    destination.mkdir(exist_ok=True)
    if {path.name for path in destination.iterdir()}-expected:
        raise RuntimeError('Review stale media output before publishing')
    for name in expected:
        shutil.copyfile(source/name, destination/name)
    print(f'Verified {len(manifest["images"])} images and {len(manifest.get("videos",[]))} videos against the reviewed media manifest.')


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.ids=set()
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs: self.ids.add(attrs['id'])
        if tag in ('a','link') and 'href' in attrs: self.links.append(attrs['href'])
        if tag in ('img','script','video','source') and 'src' in attrs: self.links.append(attrs['src'])
        if tag == 'video' and 'poster' in attrs: self.links.append(attrs['poster'])


def main():
    output=ROOT/'dist'; output.mkdir(exist_ok=True)
    expected={slug+'.html' for slug,_ in PAGES}|{'style.css','theme.js','compare.js','media','.nojekyll'}
    stale={path.name for path in output.iterdir()}-expected
    if stale: raise RuntimeError('Unexpected files in dist; review before publishing: '+str(sorted(stale)))
    copy_media(output)
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
        title_link='<a class="site-title" href="index.html">Enfusion Neural</a>'
        theme='<label class="theme-label">Theme<select data-theme-control aria-label="Color theme"><option value="system">System</option><option value="light">Light</option><option value="dark">Dark</option></select></label>'
        nextpage=PAGES[position+1] if position+1<len(PAGES) else PAGES[0]
        title='Enfusion Neural' if slug=='index' else label+' · Enfusion Neural'
        comparison_script='<script src="compare.js" defer></script>' if slug in ('comparisons','lighting-study','arma-scenes') else ''
        page=f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title><meta name="description" content="Enfusion Neural documentation: reference scenes, capture procedures, model implementation and evaluation.">
<script src="theme.js"></script>{comparison_script}<link rel="stylesheet" href="style.css"></head><body>
<a class="skip" href="#content">Skip to content</a>
<aside class="sidebar">{title_link}<nav aria-label="Documentation">{nav}</nav><div class="rail-footer">{theme}<a href="{REPO}">GitHub ↗</a></div></aside>
<header class="mobile"><div class="mobile-head">{title_link}{theme}</div><details><summary>Contents</summary><nav aria-label="Mobile documentation">{nav}</nav></details></header>
<main><div class="topline"><span>Documentation</span><a href="{REPO}/blob/main/docs/{slug}.md">Page source ↗</a></div>
<article id="content">{content}</article>
<footer class="page-footer"><a href="{REPO}/blob/main/LICENSE">Code license</a><a href="{nextpage[0]}.html">{escape(nextpage[1])} →</a></footer></main></body></html>'''
        (output/f'{slug}.html').write_text(page,encoding='utf-8')
    shutil.copyfile(ROOT/'site/style.css',output/'style.css')
    shutil.copyfile(ROOT/'site/theme.js',output/'theme.js')
    shutil.copyfile(ROOT/'site/compare.js',output/'compare.js')
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
