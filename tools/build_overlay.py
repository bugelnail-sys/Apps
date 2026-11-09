"""Render a local Kodi overlay from the pinned upstream skin and reviewed files."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
KODI = PROJECT / 'kodi'
SKIN = 'skin.arctic.zephyr.mod'
ROLE_NAMES = {'ADULT_A': 'Erwachsen A', 'ADULT_B': 'Erwachsen B', 'KIDS': 'Kinder'}
PATCH_TARGETS = (
    '1080i/DialogVideoInfo.xml', '1080i/Home.xml', '1080i/Includes.xml',
    '1080i/Includes_DialogVideoInfo.xml', '1080i/LoginScreen.xml', '1080i/Startup.xml',
    'shortcuts/template.xml',
)


def inputs():
    names = {role: os.environ.get('MOMENTUM_' + role, default) for role, default in ROLE_NAMES.items()}
    folders = {role: os.environ.get('MOMENTUM_' + role + '_DIR', names[role])
               for role in ('ADULT_B', 'KIDS')}
    for value in [*names.values(), *folders.values()]:
        if (value.strip() != value or value in ('.', '..')
                or not re.fullmatch(r'[\w -]{1,45}', value)):
            raise ValueError('Profilnamen und Ordner brauchen 1–45 Buchstaben, Ziffern, Leerzeichen, _ oder -.')
    if len({value.casefold() for value in names.values()}) != 3:
        raise ValueError('Die Anzeigenamen müssen eindeutig sein.')
    if folders['ADULT_B'].casefold() == folders['KIDS'].casefold():
        raise ValueError('Die Profilordner müssen eindeutig sein.')
    return names, folders


def build(skin_zip, output):
    if output.exists():
        raise FileExistsError(f'Das Ziel muss neu sein: {output}')
    if output.is_relative_to(PROJECT) and output != PROJECT / 'build' and not output.is_relative_to(PROJECT / 'build'):
        raise ValueError('Innerhalb des Projekts muss das Ziel unter build/ liegen.')
    names, folders = inputs()
    upstream = json.loads((KODI / 'skin/upstream.json').read_text(encoding='utf-8'))
    with skin_zip.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != upstream['sha256']:
            raise ValueError('Die Prüfsumme des Skin-ZIPs weicht von der freigegebenen Version ab.')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as work:
        work = Path(work)
        stage = work / 'overlay'
        shutil.copytree(KODI / 'overlay', stage)
        skin = stage / 'addons' / SKIN
        with zipfile.ZipFile(skin_zip) as archive:
            for name in PATCH_TARGETS:
                f = skin / name
                f.parent.mkdir(parents=True, exist_ok=True)
                baseline = archive.read(SKIN + '/' + name).decode('utf-8-sig')
                f.write_text((baseline.replace('\r\n', '\n').rstrip('\n') + '\n'), encoding='utf-8', newline='\n')
        for name in PATCH_TARGETS:
            patch = KODI / 'skin/patches' / (name.replace('/', '__') + '.patch')
            subprocess.run(['git', 'apply', '--whitespace=nowarn', str(patch)],
                           cwd=skin, check=True)
        destinations = {'adult-a': stage / 'userdata',
                        'adult-b': stage / 'userdata/profiles' / folders['ADULT_B'],
                        'kids': stage / 'userdata/profiles' / folders['KIDS']}
        for role, destination in destinations.items():
            shutil.copytree(KODI / 'profiles' / role, destination, dirs_exist_ok=True)
        for path in stage.rglob('*'):
            if path.suffix not in {'.py', '.xml', '.xsp', '.properties'}:
                continue
            data = path.read_text(encoding='utf-8')
            for role, name in names.items():
                data = data.replace('@@MOMENTUM_' + role + '@@', name)
            if '@@MOMENTUM_' in data:
                raise ValueError(f'Unbekannter Profilplatzhalter in {path.name}')
            if path.suffix == '.py':
                compile(data, path.name, 'exec')
            elif path.suffix in {'.xml', '.xsp'}:
                ET.fromstring(data)
            else:
                json.loads(data)
            path.write_text(data, encoding='utf-8', newline='\n')
        stage.rename(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skin-zip', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    build(args.skin_zip.resolve(), args.out.resolve())
    print(f'Lokales Overlay erzeugt: {args.out}')
