"""Read-only access to the shared Kodi 21 video library."""
import json
import re
import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path

SAFE_RATINGS = {'fsk 0', 'fsk 6', 'fsk 12', 'rated 0', 'rated 6', 'rated 12'}
MOVIES = """
    SELECT hasVideoVersions AS has_versions, idMovie AS id, videoVersionIdFile AS fileid, idFile AS defaultfile,
           c00 AS title, c12 AS mpaa, c14 AS genre, premiered, idSet AS setid,
           rating, rating_type, videoVersionTypeName AS version, strPath AS folder,
           strFilename AS filename, lastPlayed AS played, playCount AS watched,
           resumeTimeInSeconds AS resume, totalTimeInSeconds AS total,
           (SELECT times FROM stacktimes WHERE idFile=m.videoVersionIdFile) AS stacktimes,
           COALESCE(
              (SELECT MAX(iVideoDuration) FROM streamdetails
               WHERE idFile=m.videoVersionIdFile AND iStreamType=0 AND iVideoDuration>0),
              CASE WHEN videoVersionIdFile=idFile THEN CAST(c11 AS INTEGER) END, 0
           ) AS duration
    FROM movie_view m
"""
EPISODES = """
    SELECT idEpisode AS id, idFile AS fileid, idShow AS showid, c00 AS title,
           strTitle AS showtitle, mpaa, genre, CAST(c12 AS INTEGER) AS season,
           CAST(c13 AS INTEGER) AS episode, strPath AS folder, strFilename AS filename,
           lastPlayed AS played, playCount AS watched, resumeTimeInSeconds AS resume,
           totalTimeInSeconds AS total, CAST(c09 AS INTEGER) AS duration
    FROM episode_view
"""


def safe(mpaa, genre):
    return (mpaa or '').strip().casefold() in SAFE_RATINGS and not any(
        'horror' in name.casefold() for name in (genre or []))


def media_path(row):
    filename = row['filename']
    if '://' in filename:
        return filename
    folder, sep, options = row['folder'].partition('|')
    return folder + filename + (sep + options)


def version_label(row):
    return re.sub(r' · #[0-9]+$', '', row['version'])


class Library:
    def __init__(self, database, manifest, child):
        self.database = database
        self.child = child
        try:
            self.versions = json.loads(Path(manifest).read_text(encoding='utf-8'))
        except (OSError, ValueError):
            self.versions = {}
        self.group_ids = {int(movieid) for movieid in self.versions}
        self.version_files = {
            (int(movieid), version['fileid']): version
            for movieid, group in self.versions.items()
            for version in group['versions']
        }

    def rows(self, sql, args=()):
        with closing(sqlite3.connect(Path(self.database).resolve().as_uri() + '?mode=ro',
                                     uri=True, timeout=0.5)) as db:
            db.row_factory = sqlite3.Row
            return [dict(row) for row in db.execute(sql, args)]

    def allowed_movie(self, row, family=False):
        if not (self.child or family):
            return True
        if not safe(row['mpaa'], (row['genre'] or '').split(' / ')):
            return False
        original = self.version_files.get((row['id'], row['fileid']))
        if original:
            return (original['path'] == media_path(row)
                    and safe(original.get('mpaa'), original.get('genre')))
        # A standalone film has its own rating. A new or unrecognized cut of
        # a grouped title needs a rating tied to that cut.
        return row['id'] not in self.group_ids and not row['has_versions']

    def allowed_episode(self, row):
        return not self.child or safe(row['mpaa'], (row['genre'] or '').split(' / '))

    def movies(self, suffix='', args=()):
        rows = self.rows(MOVIES + suffix, args)
        for row in rows:
            if row['filename'].startswith('stack://'):
                # A stream-details runtime can describe only the first part.
                times = (row['stacktimes'] or '').split(',')
                row['duration'] = float(times[-1]) if len(times) > 1 else (row['total'] or 0)
        return rows

    def next_episodes(self):
        rows = self.rows(EPISODES + """
            WHERE idShow IN (
                SELECT DISTINCT e.idShow FROM episode e
                JOIN files f ON f.idFile=e.idFile
                WHERE f.lastPlayed IS NOT NULL AND f.lastPlayed <> ''
                UNION
                SELECT DISTINCT e.idShow FROM episode e
                JOIN bookmark b ON b.idFile=e.idFile WHERE b.type=1 AND b.timeInSeconds>0
            )
            AND CAST(c12 AS INTEGER)>0 AND CAST(c13 AS INTEGER)>0
            ORDER BY idShow, season, episode, idEpisode
        """)
        shows = defaultdict(list)
        for row in rows:
            if self.allowed_episode(row):
                shows[row['showid']].append(row)
        for episodes in shows.values():
            # Kodi shares progress for files covering several episodes.
            started = [row for row in episodes if row['played'] or row['resume']]
            if not started:
                continue
            last = max(started, key=lambda row: (row['played'] or '', row['season'], row['episode']))
            date = last['played'] or ''
            chosen = last
            if last['resume']:
                chosen = next(row for row in episodes if row['fileid'] == last['fileid'])
            elif last['watched']:
                last_number = (last['season'], last['episode'])
                chosen = next((row for row in episodes
                               if (row['season'], row['episode']) > last_number
                               and row['fileid'] != last['fileid'] and not row['watched']), None)
            if chosen is not None:
                yield dict(chosen, kind='episode', order=date)

    def continue_watching(self):
        latest = {}
        for row in self.movies(' WHERE resumeTimeInSeconds>0 ORDER BY lastPlayed DESC, videoVersionIdFile'):
            if self.allowed_movie(row):
                latest.setdefault(row['id'], dict(row, kind='movie', order=row['played'] or ''))
        return sorted([*latest.values(), *self.next_episodes()],
                      key=lambda row: row['order'], reverse=True)[:12]

    def movie_night(self, preset):
        family = preset == 'family'
        movies = defaultdict(list)
        for row in self.movies():
            movies[row['id']].append(row)
        available = []
        first_in_set = {}
        for versions in movies.values():
            if any(row['watched'] for row in versions):
                continue
            representative = versions[0]
            eligible = [row for row in versions if self.allowed_movie(row, family)]
            if not eligible:
                continue
            # Use release order only when the catalog has a date for the title.
            setid = representative['setid']
            date = representative['premiered']
            if setid and date:
                first_in_set[setid] = min(first_in_set.get(setid, date), date)
            available.append(eligible)
        return [
            [row for row in versions if preset != 'short' or 0 < row['duration'] <= 5400]
            for versions in available
            if not versions[0]['setid'] or not versions[0]['premiered']
            or versions[0]['premiered'] == first_in_set[versions[0]['setid']]
        ]

    def art(self, row):
        kind = row.get('kind', 'movie')
        art = {entry['type']: entry['url'] for entry in self.rows(
            'SELECT type,url FROM art WHERE media_id=? AND media_type=?',
            (row['id'], kind)) if entry['url']}
        if kind == 'episode':
            show_art = self.rows(
                "SELECT type,url FROM art WHERE media_id=? AND media_type='tvshow' "
                "AND type IN ('poster','fanart')", (row['showid'],))
            for entry in show_art:
                art.setdefault(entry['type'], entry['url'])
        if 'poster' in art:
            art['icon'] = art['poster']
        elif 'thumb' in art:
            art['icon'] = art['thumb']
        return art
