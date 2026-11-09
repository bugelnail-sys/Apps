import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest

SOURCE = (Path(__file__).resolve().parents[1] / 'kodi/overlay/addons'
          / 'plugin.video.momentum.home/library.py')
SPEC = importlib.util.spec_from_file_location('momentum_library', SOURCE)
LIB = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LIB)


class LocalLibraryTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        folder = Path(tmp.name)
        self.db = folder / 'sample.db'
        self.manifest = folder / 'versions-manifest.json'
        self.manifest.write_text(
            '{"1":{"versions":['
            '{"fileid":10,"path":"file:///demo/default.mkv","mpaa":"FSK 6","genre":["Familie"]},'
            '{"fileid":11,"path":"file:///demo/alternate.mkv","mpaa":"FSK 16","genre":["Horror"]}]}}',
            encoding='utf-8')
        connection = sqlite3.connect(self.db)
        try:
            connection.executescript("""
                CREATE TABLE movie_view(
                    hasVideoVersions, idMovie, videoVersionIdFile, idFile,
                    c00, c12, c14, premiered, idSet, rating, rating_type,
                    videoVersionTypeName, strPath, strFilename, lastPlayed, playCount,
                    resumeTimeInSeconds, totalTimeInSeconds, c11);
                CREATE TABLE episode_view(
                    idEpisode, idFile, idShow, c00, strTitle, mpaa, genre,
                    c12, c13, strPath, strFilename, lastPlayed, playCount,
                    resumeTimeInSeconds, totalTimeInSeconds, c09);
                CREATE TABLE episode(idShow,idFile);
                CREATE TABLE files(idFile,lastPlayed);
                CREATE TABLE bookmark(idFile,type,timeInSeconds);
                CREATE TABLE streamdetails(idFile,iStreamType,iVideoDuration);
                CREATE TABLE stacktimes(idFile,times);
                CREATE TABLE art(media_id,media_type,type,url);
                INSERT INTO movie_view VALUES
                    (1,1,10,10,'Film A','FSK 6','Familie','2001',NULL,7,'imdb',
                     'Standard Edition','file:///demo/','default.mkv',NULL,0,NULL,NULL,6000),
                    (1,1,11,10,'Film A','FSK 6','Familie','2001',NULL,7,'imdb',
                     'Alternative','file:///demo/','alternate.mkv','2026-01-01',0,1200,6000,6000),
                    (0,2,20,20,'Film B','FSK 12','Horror','2002',NULL,6,'imdb',
                     'Standard Edition','file:///demo/','b.mkv',NULL,0,NULL,NULL,4800),
                    (0,3,30,30,'Film C','FSK 6','Familie','2003',NULL,8,'imdb',
                     'Standard Edition','file:///demo/','stack://file:///demo/a.avi , file:///demo/b.avi',
                     NULL,0,NULL,NULL,2464),
                    (0,4,40,40,'Film D','FSK 0','Familie','2004',NULL,8,'imdb',
                     'Standard Edition','file:///demo/','stack://file:///demo/c.avi , file:///demo/d.avi',
                     NULL,0,NULL,NULL,2400);
                INSERT INTO stacktimes VALUES (40,'2400,5100');
                INSERT INTO episode_view VALUES
                    (101,1001,1,'Folge 1','Serie','FSK 6','Familie',
                     1,1,'file:///demo/','e1.mkv','2026-01-02',1,NULL,NULL,1400),
                    (102,1002,1,'Folge 2','Serie','FSK 6','Familie',
                     1,2,'file:///demo/','e2.mkv',NULL,0,NULL,NULL,1400);
                INSERT INTO episode VALUES (1,1001),(1,1002);
                INSERT INTO files VALUES (1001,'2026-01-02'),(1002,NULL);
            """)
        finally:
            connection.close()

    def library(self, child=False):
        return LIB.Library(self.db, self.manifest, child)

    def test_next_episode_and_exact_resume(self):
        episode, movie = self.library().continue_watching()
        self.assertEqual((episode['kind'], episode['episode']), ('episode', 2))
        self.assertEqual((LIB.media_path(movie), movie['resume']), ('file:///demo/alternate.mkv', 1200))

    def test_child_excludes_horror_and_adult_cuts(self):
        child = self.library(child=True)
        self.assertEqual([row['kind'] for row in child.continue_watching()], ['episode'])
        suggested_files = {row['fileid'] for group in child.movie_night('any') for row in group}
        self.assertEqual(suggested_files, {10, 30, 40})

    def test_short_preset_uses_total_runtime(self):
        short = {row['fileid']: row['duration']
                 for group in self.library().movie_night('short') for row in group}
        self.assertEqual(short, {20: 4800, 40: 5100.0})


if __name__ == '__main__':
    unittest.main()
