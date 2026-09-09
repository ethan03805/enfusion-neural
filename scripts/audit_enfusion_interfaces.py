"""Inventory installed documented members; names alone do not prove runtime capability."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import re


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    path.write_bytes((json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode('utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-root', type=Path, required=True,
                        help='Installed Workbench/docs directory; read only')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('Use a new output directory')
    roots = ['EnfusionScriptAPI/html', 'ArmaReforgerScriptAPIPublic/html']
    terms = {
        'custom_gpu': r'ComputeShader|DispatchCompute|CompileShader|D3D|Vulkan|RenderDevice|CommandQueue|CommandBuffer|GraphicsFence|GPUFence|GBuffer|MotionVector|SharedTexture|NativeTexture',
        'render_and_pixels': r'RenderTarget|RenderView|RawData|Screenshot|CameraPostProcess|TextureResource|Shader',
    }
    patterns = {name: re.compile(expression, re.I) for name, expression in terms.items()}
    files, matches, counts = [], {name: [] for name in terms}, []
    html_files, html_matches, html_counts = [], {name: [] for name in terms}, []
    encoding_anomalies = []
    static_controls = {'interfaceMaterial.Create':False, 'interfaceSystem.MakeScreenshot':False}
    row_pattern = re.compile(r'<td\s+class="memItemRight"[^>]*>(.*?)</td>', re.S)
    member_pattern = re.compile(r'<a\s+class="el"\s+href="#([^"]+)">([^<]+)</a>')
    for relative in roots:
        folder = args.sdk_root / relative
        if not (folder / 'annotated.html').is_file():
            raise ValueError('Missing documented interface index: ' + relative)
        source_paths = sorted(folder.glob('interface*.js'))
        if not source_paths:
            raise ValueError('No documented member indexes: ' + relative)
        members_count = 0
        for path in source_paths:
            raw = path.read_bytes()
            text = raw.decode('utf-8-sig').strip()
            if not re.match(r'^var\s+interface\w+\s*=', text) or not text.endswith(';'):
                raise ValueError('Unexpected generated member index: ' + path.name)
            members = json.loads(text.split('=', 1)[1].rstrip(';').strip())
            if not isinstance(members, list):
                raise ValueError('Member index is not a list')
            files.append({'file':relative + '/' + path.name, 'sha256':digest(raw), 'bytes':len(raw), 'members':len(members)})
            members_count += len(members)
            for member in members:
                if not isinstance(member, list) or len(member) != 3 or not isinstance(member[0], str) or not isinstance(member[1], str):
                    raise ValueError('Unexpected member record: ' + path.name)
                for category, pattern in patterns.items():
                    if pattern.search(member[0]):
                        matches[category].append({'interface':path.stem, 'member':member[0], 'documentation':relative+'/'+member[1]})
        counts.append({'root':relative, 'member_index_files':len(source_paths), 'documented_members':members_count})
        own_rows = 0
        html_paths = sorted(path for path in folder.glob('interface*.html') if not path.name.endswith('-members.html'))
        for path in html_paths:
            raw = path.read_bytes()
            names = []
            try:
                html_text = raw.decode('utf-8-sig')
            except UnicodeDecodeError as error:
                encoding_anomalies.append({'file':relative+'/'+path.name, 'sha256':digest(raw), 'first_invalid_byte_offset':error.start, 'byte':raw[error.start:error.start+1].hex()})
                # Preserve undecodable bytes. They must not occur in an extracted member name.
                html_text = raw.decode('utf-8-sig', errors='surrogateescape')
            for row in row_pattern.findall(html_text):
                member = member_pattern.search(row)
                if not member:
                    continue  # Inherited rows link to another interface, not this document.
                anchor, name = member.groups()
                name = html.unescape(name)
                name.encode('utf-8')
                names.append(name)
                key = path.stem + '.' + name
                if key in static_controls:
                    static_controls[key] = True
                for category, pattern in patterns.items():
                    if pattern.search(name):
                        html_matches[category].append({'interface':path.stem, 'member':name, 'documentation':relative+'/'+path.name+'#'+anchor})
            own_rows += len(names)
            html_files.append({'file':relative+'/'+path.name, 'sha256':digest(raw), 'bytes':len(raw), 'own_member_rows':len(names)})
        html_counts.append({'root':relative, 'full_interface_files':len(html_paths), 'own_member_rows':own_rows})
        print(json.dumps({'completed_root':relative, 'full_interface_files':len(html_paths), 'own_member_rows':own_rows}), flush=True)
    if not all(static_controls.values()):
        raise ValueError('Full HTML scan missed a known static-method control')
    selected = [
        'EnfusionScriptAPI/html/interfaceBaseWorld.html',
        'EnfusionScriptAPI/html/interfaceMaterial.html',
        'EnfusionScriptAPI/html/interfaceRenderTargetWidget.html',
        'EnfusionScriptAPI/html/interfaceRTTextureWidget.html',
        'EnfusionScriptAPI/html/interfaceImageWidget.html',
        'EnfusionScriptAPI/html/interfaceSystem.html',
        'EnfusionScriptAPI/html/interfaceResourceManager.html',
        'EnfusionScriptAPI/html/interfaceTextureResourceInfo.html',
        'EnfusionScriptAPI/html/interfaceExportTextureResourceRequest.html',
        'EnfusionScriptAPI/html/interfaceMeshObject.html',
        'EnfusionScriptAPI/html/group__World.html',
        'ArmaReforgerScriptAPIPublic/html/interfaceSCR__CameraPostProcessEffect.html',
    ]
    references = []
    for name in selected:
        raw = (args.sdk_root / name).read_bytes()
        references.append({'file':name, 'sha256':digest(raw), 'bytes':len(raw)})
    args.out.mkdir(parents=True)
    write(args.out / 'member-index-files.json', files)
    write(args.out / 'full-interface-files.json', html_files)
    result = {
        'schema_version':1, 'operation':'documented-renderer-member-inventory',
        'status':'succeeded', 'scanner_sha256':digest(Path(__file__).read_bytes()),
        'scope':'Two installed generated interface-member index sets and their full interface HTML documents, including static methods omitted from indexes. This is neither a complete engine API nor a runtime capability test.',
        'roots':counts, 'search_expressions':terms, 'matches':matches,
        'member_index_manifest_sha256':digest((args.out / 'member-index-files.json').read_bytes()),
        'full_html_roots':html_counts, 'full_html_matches':html_matches,
        'full_html_manifest_sha256':digest((args.out / 'full-interface-files.json').read_bytes()),
        'static_method_controls':static_controls,
        'source_encoding_anomalies':encoding_anomalies,
        'selected_full_documentation':references,
        'limits':[
            'Names are discovery leads; overload signatures, descriptions and native behavior require separate inspection.',
            'A missing keyword cannot prove that an undocumented, differently named or private interface is unavailable.',
            'Generated .js indexes contain declared members, not implementation source. Inherited members can be in their parent interface.',
            'Some full source pages contain invalid UTF-8 bytes. Their original hashes and offsets are retained; lossless surrogate escaping is used only for parsing, and extracted names must be valid UTF-8.',
            'No engine process, GPU work, modification, asset extraction or message to Bohemia was performed.',
        ],
    }
    write(args.out / 'run.json', result)
    print(json.dumps({'roots':counts, 'html_roots':html_counts, 'html_matches':{key:len(value) for key,value in html_matches.items()}, 'custom_gpu':html_matches['custom_gpu']}))


if __name__ == '__main__':
    main()
