"""On-demand native Kodi version chooser. No background service or database writes."""
import pathlib,json,re
import xbmc,xbmcgui,xbmcvfs

def main():
 ident=xbmc.getInfoLabel('ListItem.DBID')
 try:
  data=json.loads(pathlib.Path(xbmcvfs.translatePath('special://masterprofile/family/versions-manifest.json')).read_text(encoding='utf-8'))
 except (OSError, ValueError):
  xbmcgui.Dialog().notification('Kodi','Das lokale Fassungsregister ist nicht verfügbar.');return
 group=data.get(ident)
 if not group:
  xbmc.executebuiltin('SendClick(12003,8)');return
 versions=group['versions']
 if xbmc.getInfoLabel('System.ProfileName').casefold()=='@@MOMENTUM_KIDS@@'.casefold():
  versions=[v for v in versions if re.search(r'(?:FSK|Rated)\s*(?:0|6|12)\b',v.get('mpaa',''),re.I) and 'horror' not in [g.casefold() for g in v.get('genre',[])]]
 if not versions:
  xbmcgui.Dialog().notification('Kodi','Keine passende Fassung für dieses Profil.');return
 items=[]
 for number,version in enumerate(versions,1):
  item=xbmcgui.ListItem(label='Fassung '+str(number)+' · '+re.sub(r' · #[0-9]+$','',version['label']),label2=version['path']);item.setArt({'icon':'DefaultVideo.png'});items.append(item)
 selected=xbmcgui.Dialog().select(group['title']+' – Fassung auswählen',items,useDetails=True)
 if selected<0:return
 path=versions[selected]['path']
 # Use the registered file URL so per-file resume positions and watched state remain Kodi-owned.
 response=json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':'Player.Open','params':{'item':{'file':path},'options':{'resume':True}}})))
 if 'error' in response:xbmcgui.Dialog().notification('Kodi','Die gewählte Fassung konnte nicht gestartet werden.')
 else:xbmc.executebuiltin('Dialog.Close(all,true)')
if __name__=='__main__':main()
