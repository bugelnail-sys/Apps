# Momentum Heimkino für Kodi

Eine Oberfläche für die lokale Kodi-Bibliothek. Der Ausgangsstand wurde am 9. November 2026 vom Fire TV Stick gelesen. Dieses Projekt enthält die bearbeitbaren Änderungen für Cloud-Entwicklung, Tests und spätere lokale Installation.

## Funktionsumfang

- Drei Profile mit Comic-Avataren, eigenen Akzentfarben und gemeinsamer Bibliothek samt Wiedergabeständen. Das Kinderprofil zeigt nur bestätigte FSK 0, 6 und 12 und schließt Horror aus. Die Profile verwenden keine PIN.
- „Weiterschauen“ zeigt angefangene Filme und je laufender Serie die angefangene oder nächste Folge. Bei mehreren Filmfassungen gehört der Speicherpunkt zur konkreten Datei.
- „Kinoabend“ liefert auf Abruf drei ungesehene Vorschläge. Es gibt Familienabend, Filme bis 90 Minuten und eine Zufallsauswahl. Für mehrteilige Dateien wird die belegte Gesamtlaufzeit verwendet.
- Auf der Film-Infoseite öffnet „Fassung auswählen“ die registrierten Varianten. Bestätigte Fassungsmerkmale wie 3D oder Schnitt können aus dem lokalen Register angezeigt werden. Trailer-, Film- und Personensuche öffnen auf Fire TV die native YouTube-App.
- Der eigene Dolby-Digital-5.1-Clip startet nach der ersten Profilwahl und kurzer Wartezeit. Die Wiedergabe lässt sich überspringen.
- Die Bibliothek der Referenzinstallation verwendet SMB-Quellen, lokale NFOs und ergänzte Bilder. IMDb ist bei vorhandener Zuordnung die bevorzugte Bewertung. Für weitere Einträge bleiben die vorhandenen Ersatzbewertungen erhalten. Bibliothekspflege und Metadatenimport gehören zum lokalen Betrieb.

## Referenzinstallation

Fire TV Stick 4K Max der ersten Generation, Fire OS 7.7.1.3 und **Kodi 21.3 Omega**. Das Skin-Paket ist **Arctic: Zephyr – Reloaded 3.0.3**. **Skin Shortcuts 2.0.3** baut die Startmenüs. Die installierten Versionen der Such-, Scraper- und Hilfs-Add-ons sowie die ausgewählten Kodi-Einstellungen stehen in [installation.json](kodi/reference/installation.json). Für YouTube und O2 TV werden native Apps aufgerufen. Home on Fire 1.5.2 übernimmt im Referenzgerät die Rückkehr zu Kodi. Die neuen Menüfunktionen benötigen keinen Hintergrunddienst.

Auf dem Referenzgerät waren MediaCodec mit Surface, 1080p für die Oberfläche, Bildfrequenzanpassung mit zwei Sekunden Verzögerung und Netzwerkcache mit 96 MiB, 4× Leserate und 256 KiB Blöcken eingestellt. Der Ton nutzt am vorhandenen HDMI-ARC-Aufbau Kodi IEC und AC-3-Passthrough bzw. AC-3-Transkodierung. Gerätespezifische Werte dienen als Vergleich bei Tests.

## Aufbau und Zielpfade

Die folgenden Zielpfade sind relativ zum Kodi-Datenverzeichnis. Auf dem Fire TV liegt es unter `/sdcard/Android/data/org.xbmc.kodi/files/.kodi/`.

| Im Projekt | Auf dem Gerät |
| --- | --- |
| `kodi/skin/patches/` | Unter `addons/skin.arctic.zephyr.mod/` in `1080i/`: `DialogVideoInfo.xml`, `Home.xml`, `Includes.xml`, `Includes_DialogVideoInfo.xml`, `LoginScreen.xml` und `Startup.xml`. Außerdem `shortcuts/template.xml`. |
| `kodi/overlay/addons/skin.arctic.zephyr.mod/1080i/Custom_Momentum_Intro.xml` | Dialog für den Startclip. |
| `kodi/overlay/addons/plugin.video.momentum.home/` | Lokales Add-on für Weiterschauen und Kinoabend. Es liest die Kodi-21-Videodatenbank im Nur-Lesen-Modus. |
| `kodi/overlay/userdata/family/` | Python-Skripte für Intro, Fassungen und YouTube, dazu die vorbereiteten Profilgrafiken und der Startclip. |
| `kodi/profiles/` | Vorlagen für `addon_data/script.skinshortcuts/` und `playlists/video/` des Hauptprofils und der zwei weiteren Profile. |
| `kodi/reference/` | Referenzwerte, Abhängigkeiten und ein synthetisches Fassungsregister als Formatbeispiel. |
| `tools/`, `tests/` | Overlay-Build und Tests für Bibliotheksabfragen mit synthetischer SQLite-Datenbank. |

`script-skinshortcuts-includes.xml` wird auf dem Gerät aus den Menüquellen generiert. `profiles.xml`, `guisettings.xml`, echte Fassungsdaten, Bibliotheken und Wiedergabestände gehören zur lokalen Installation. Das lokale Fassungsregister `userdata/family/versions-manifest.json` wird aus der jeweiligen Bibliothek gepflegt. Seine IDs und Medienpfade müssen zum konkreten Kodi-Bestand passen.

## Cloud-Entwicklung

Benötigt werden Git und Python 3.11 oder neuer. Für einen vollständigen Build wird das originale ZIP von [Arctic: Zephyr – Reloaded 3.0.3](https://kodi.tv/addons/omega/skin.arctic.zephyr.mod/) benötigt. Downloadquelle und SHA-256 stehen in [upstream.json](kodi/skin/upstream.json).

```sh
python -m unittest discover -s tests -v
python tools/build_overlay.py --skin-zip /pfad/zum/skin.arctic.zephyr.mod-3.0.3.zip --out build/demo
```

Der Build prüft das Upstream-ZIP, wendet die Skin-Patches an und validiert Python-Syntax, XML und Menüeigenschaften. Das Ziel muss neu sein. Die Ausgabe ist ein Overlay mit den bearbeiteten Dateien, das auf einer vorhandenen Kodi- und Skin-Installation aufsetzt. Für Änderungen an vorhandenen Skin-Dateien die betreffende Patchdatei aktualisieren. Zusätzliche eigene Dateien kommen unter `kodi/overlay/`.

Standardmäßig rendert der Build mit den Testprofilen „Erwachsen A“, „Erwachsen B“ und „Kinder“. Für ein konkretes Gerät die Anzeigenamen und Profilordner vor dem Build als lokale Prozessvariablen setzen. [.env.example](.env.example) beschreibt die Namen. Kodi-Profile über die Kodi-Oberfläche anlegen, gemeinsame Bibliothek einstellen und die neutral benannten Avatar-Dateien zuweisen. Eine vorhandene Produktionseinrichtung kann ihre bisherige Profilzuordnung beibehalten. Lokale NAS-Verbindungen und Zugangsdaten werden in Kodi am jeweiligen Gerät eingerichtet.

## Lokale Installation und Rückweg

1. Auf einem Testprofil oder einer separaten Kodi-Installation beginnen. Auf einem Fire TV mit ADB-Geräteliste das Ziel eindeutig bestätigen. Kodi- und Skin-Version prüfen. Bei einer laufenden Wiedergabe oder einem Scan auf deren Ende warten.
2. Das Overlay mit den Zielprofilen in ein neues Verzeichnis bauen. Nur die für die Änderung benötigten Dateien auswählen. Bestehende Fassungsdaten, Quellen, Kodi-Datenbanken und Kontoeinstellungen bleiben gerätespezifisch.
3. Jede betroffene Zieldatei vor dem Schreiben mit `adb pull` lokal sichern und die SHA-256 mit `adb shell sha256sum` vergleichen. In einer lokalen Liste festhalten, welche Zieldateien vorher existierten und welche neu sind. Geräte-Backups außerhalb des Git-Arbeitsbaums ablegen.
4. Kodi vor Änderungen an Skin- oder Profildateien sauber beenden. Falls Home on Fire Kodi während der Wartung wieder öffnet, dessen Umleitung für die Wartung gezielt aussetzen und danach wiederherstellen. Per ADB die neuen Dateien zunächst unter temporären Namen in das jeweilige Zielverzeichnis übertragen. Prüfsummen kontrollieren und anschließend im selben Verzeichnis auf den endgültigen Namen umbenennen. Das lokale Add-on nach Erkennung in Kodi bei Bedarf aktivieren. Skin Shortcuts das Menü beim nächsten Kodi-Start neu erzeugen lassen.
5. Bei einem Fehler Kodi erneut sauber beenden und nur die gesicherten, betroffenen Dateien zurückspielen. Neue Dateien anhand der Liste und ihrer Prüfsummen als eigene Änderungen identifizieren und entfernen. Zurückgespielte Dateien erneut prüfen, Kodi starten und die betroffenen Funktionen kontrollieren.

### Am Fire TV zu prüfen

- Profilwahl mit Fernbedienung, Akzentfarben, Rückkehr über Home on Fire und Kinderfilter auf der echten Startseite.
- „Weiterschauen“ an einem Testtitel mit Lesezeichen und mehreren Fassungen. Dateipfad und Position vergleichen und den ursprünglichen Test-Wiedergabestand wiederherstellen. Nach einer Serienfolge den Wechsel zur nächsten Folge kontrollieren.
- „Kinoabend“ in Erwachsenen- und Kinderprofilen. Vorschläge neu mischen, Fassungswahl abbrechen und einen bewusst gewählten Titel starten.
- Startclip nach der Profilwahl, Überspringen, HDMI-Synchronisierung und hörbare AC-3-Ausgabe am tatsächlichen TV-/Soundbar-Aufbau.
- Native YouTube- und O2-TV-Aufrufe, Rückkehr zu Kodi und SMB-Wiedergabe aus den tatsächlich erreichbaren Freigaben. Während eines Profilwechsels keine JSON-RPC-Abfragen senden.

## Herkunft und Lizenz

Die Skin-Patches und der Dialog im Skin basieren auf **Arctic: Zephyr – Reloaded** von jurialmunkey und beatmasterrs. Sie stehen wie der Upstream-Skin unter [CC BY-NC-SA 3.0](https://creativecommons.org/licenses/by-nc-sa/3.0/). Der [Upstream-Hinweis](kodi/skin/LICENSE.txt) liegt bei. Das eigenständige lokale Add-on deklariert MIT in seiner Add-on-Metadatei.
