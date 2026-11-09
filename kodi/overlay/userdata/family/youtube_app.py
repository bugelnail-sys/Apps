"""On-demand Kodi info-page integration with the existing Fire TV YouTube app.

No background service, network requests, personal API keys, or shell commands.
"""
import json
import pathlib
import re
import sys
import urllib.parse


def clean_title(value):
    return next((line.strip() for line in str(value).replace('\\n', '\n').splitlines()
                 if line.strip() and not line.casefold().startswith(('alternativtitel', 'alternativ:'))), '')


def video_id(value):
    try:
        uri = urllib.parse.urlsplit(value)
        query = urllib.parse.parse_qs(uri.query)
        host = (uri.hostname or '').casefold()
        if uri.scheme == 'plugin' and host == 'plugin.video.youtube':
            possibilities = [query.get(k, [''])[0] for k in ['video_id', 'videoid', 'v']]
        elif host in ['youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be']:
            possibilities = [query.get('v', [''])[0]]
            if host == 'youtu.be' or uri.path.startswith(('/shorts/', '/embed/')):
                possibilities.append(uri.path.rstrip('/').split('/')[-1])
        else:
            return None
        return next((v for v in possibilities if re.fullmatch(r'[A-Za-z0-9_-]{11}', v)), None)
    except (ValueError, TypeError):
        return None


def build_uri(title, year='', trailer='', mode='search'):
    if mode == 'trailer':
        ident = video_id(trailer)
        if ident:
            return 'https://www.youtube.com/watch?v=' + ident
    terms = [clean_title(title)]
    if mode != 'person' and re.fullmatch(r'(?:18|19|20)\d{2}', str(year)):
        terms.append(str(year))
    if mode == 'trailer':
        terms.extend(['Trailer', 'Deutsch'])
    query = ' '.join(x for x in terms if x)
    return 'youtube://search?query=' + urllib.parse.quote(query, safe='') if query else None


def main():
    import xbmc
    import xbmcgui
    import xbmcvfs

    mode = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ['search', 'trailer', 'person'] else 'search'
    labels = {key: xbmc.getInfoLabel(key) for key in [
        'ListItem.Title', 'ListItem.Label', 'ListItem.Year', 'ListItem.Trailer', 'ListItem.DBID', 'ListItem.DBTYPE',
        'Container(10051).ListItem.Label']}
    title = labels['ListItem.Title'] or labels['ListItem.Label']
    if mode == 'person':
        title = labels['Container(10051).ListItem.Label'] or title
    uri = build_uri(title, labels['ListItem.Year'], labels['ListItem.Trailer'], mode)
    if not uri:
        xbmcgui.Dialog().notification('YouTube', 'Für diesen Eintrag ist kein Suchname vorhanden.')
        return
    path = pathlib.Path(xbmcvfs.translatePath('special://masterprofile/family/youtube-app-last.json'))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'mode': mode, 'title': clean_title(title), 'year': labels['ListItem.Year'],
                                'dbid': labels['ListItem.DBID'], 'dbtype': labels['ListItem.DBTYPE'],
                                'uri': uri}, ensure_ascii=False, indent=2), encoding='utf-8')
    # All metadata is confined to a percent-encoded URI. Package/action are
    # constants, and no metadata is interpolated into a shell or script call.
    xbmc.executebuiltin('StartAndroidActivity(com.amazon.firetv.youtube,android.intent.action.VIEW,,' + uri + ')')


if __name__ == '__main__':
    main()
