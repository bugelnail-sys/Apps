"""Kodi plugin entry point. Runs when the widget loads or a command is selected."""
import json
import math
import random
import sqlite3
import sys
from urllib.parse import parse_qs

import xbmc
import xbmcgui
import xbmcplugin
import xbmcvfs

from library import Library, media_path, version_label

PRESETS = [('Familienabend', 'family'), ('Bis 90 Minuten', 'short'),
           ('Überrasch mich', 'any')]


def library(force_child=False):
    return Library(xbmcvfs.translatePath('special://masterprofile/Database/MyVideos131.db'),
                   xbmcvfs.translatePath('special://masterprofile/family/versions-manifest.json'),
                   force_child or xbmc.getInfoLabel('System.ProfileName').casefold() not in ('@@MOMENTUM_ADULT_A@@'.casefold(), '@@MOMENTUM_ADULT_B@@'.casefold()))


def minutes(seconds):
    return math.ceil(seconds / 60)


def progress_label(row):
    remaining = (row['total'] or row['duration'] or 0) - (row['resume'] or 0)
    if remaining > 0 and row['resume']:
        return 'Noch {} Min.'.format(minutes(remaining))
    if row['resume']:
        return 'Fortsetzen'
    return 'Nächste Folge'


def progress_item(lib, row):
    title = row['title']
    if row['kind'] == 'episode':
        title = '{} · S{:02d}E{:02d}'.format(row['showtitle'], row['season'], row['episode'])
    status = progress_label(row)
    item = xbmcgui.ListItem(label=title + ' · ' + status, label2=status, offscreen=True)
    item.setArt(lib.art(row))
    item.setProperty('IsPlayable', 'true')
    # The resolved playback path and resume marker refer to the underlying file.
    tag = item.getVideoInfoTag()
    tag.setTitle(title + ' · ' + status)
    tag.setPlot(status if row['kind'] == 'movie' else row['title'] + ' · ' + status)
    tag.setMediaType(row['kind'])
    tag.setFilenameAndPath(media_path(row))
    if row['resume']:
        tag.setResumePoint(row['resume'], row['total'] or 0)
    item.setProperty('MomentumResumeKey', '{}-{}-{}'.format(row['kind'], row['id'], row['fileid']))
    return media_path(row), item, False


def widget(lib, handle):
    rows = lib.continue_watching()
    xbmcplugin.addDirectoryItems(handle, [progress_item(lib, row) for row in rows], len(rows))
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)


def resume(lib, key):
    row = next((r for r in lib.continue_watching()
                if key == '{}-{}-{}'.format(r['kind'], r['id'], r['fileid'])), None)
    if row is None:
        xbmcgui.Dialog().notification('Weiterschauen', 'Die Liste wurde inzwischen aktualisiert.')
        return
    play(row, 'Weiterschauen')


def play(row, heading):
    request = {'jsonrpc': '2.0', 'id': 1, 'method': 'Player.Open',
               'params': {'item': {'file': media_path(row)}, 'options': {'resume': True}}}
    response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    if 'error' in response:
        xbmcgui.Dialog().notification(heading, 'Die Datei konnte nicht gestartet werden.')
        return False
    return True


def suggestion(lib, versions):
    row = next((r for r in versions if r['fileid'] == r['defaultfile']), versions[0])
    lengths = sorted({minutes(r['duration']) for r in versions if r['duration'] > 0})
    details = []
    if row['premiered']:
        details.append(row['premiered'][:4])
    if not lengths:
        details.append('Laufzeit offen')
    if lengths:
        details.append(('%s–%s Min.' % (lengths[0], lengths[-1])) if len(lengths) > 1
                       else ('%s Min.' % lengths[0]))
    if row['rating']:
        source = {'imdb': 'IMDb', 'tmdb': 'TMDB'}.get(row['rating_type'], '')
        details.append(('{} {:.1f}'.format(source, row['rating'])).strip().replace('.', ','))
    item = xbmcgui.ListItem(label=row['title'], label2=' · '.join(details), offscreen=True)
    item.setArt(lib.art(row))
    return item


def open_movie(dialog, versions):
    if len(versions) > 1:
        labels = [version_label(r) + (' · {} Min.'.format(minutes(r['duration']))
                                      if r['duration'] > 0 else '') for r in versions]
        selected = dialog.select('Fassung auswählen', labels)
        if selected < 0:
            return False
    else:
        selected = 0
    return play(versions[selected], 'Kinoabend')


def movie_night(lib):
    dialog = xbmcgui.Dialog()
    while True:
        preset = dialog.select('Kinoabend · Worauf habt ihr Lust?', [p[0] for p in PRESETS])
        if preset < 0:
            return
        pool = [versions for versions in lib.movie_night(PRESETS[preset][1]) if versions]
        if not pool:
            dialog.ok('Kinoabend', 'Für diese Auswahl sind gerade keine passenden Filme vorhanden.')
            continue
        previous = []
        while True:
            rest = [item for item in pool if item not in previous]
            picks = random.sample(rest, min(3, len(rest)))
            if len(picks) < 3:
                picks += random.sample(previous, min(3 - len(picks), len(previous)))
            previous = picks
            items = [suggestion(lib, versions) for versions in picks]
            reroll = xbmcgui.ListItem(label='Neue Vorschläge', offscreen=True)
            reroll.setArt({'icon': 'DefaultPlaylist.png'})
            items.append(reroll)
            selected = dialog.select('Kinoabend · ' + PRESETS[preset][0], items, useDetails=True)
            if selected < 0:
                break
            if selected < len(picks) and open_movie(dialog, picks[selected]):
                return


def main():
    if sys.argv[1:] == ['kinoabend']:
        movie_night(library())
        return
    if len(sys.argv) == 3 and sys.argv[1] == 'resume':
        resume(library(), sys.argv[2])
        return
    handle = int(sys.argv[1])
    args = parse_qs(sys.argv[2].lstrip('?'))
    if args.get('action') == ['empty']:
        xbmcplugin.endOfDirectory(handle, cacheToDisc=False)
    else:
        widget(library(args.get('profile') == ['kids']), handle)


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, ValueError, LookupError, sqlite3.Error) as error:
        xbmc.log('Momentum Heimkino: ' + str(error), xbmc.LOGERROR)
