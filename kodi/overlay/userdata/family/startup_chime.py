"""One local 5.1 cue after the first profile's Home, with bounded readiness delay."""
import os,json,time
import xbmc,xbmcgui,xbmcvfs
NAME='Momentum-Kino-Start-Dolby-5.1-Ready.mkv'
RUNNING='Momentum.Intro.Running';CANCEL='Momentum.Intro.Cancel';DIALOG=11196

class IntroPlayer(xbmc.Player):
 def __init__(self):super().__init__();self.started=False;self.ended=False;self.error=False
 def onAVStarted(self):self.started=True
 def onPlayBackEnded(self):self.ended=True
 def onPlayBackStopped(self):self.ended=True
 def onPlayBackError(self):self.error=True;self.ended=True

def main():
 base=xbmcvfs.translatePath('special://masterprofile/family/')
 with open('/proc/self/stat') as f:start=f.read().rsplit(')',1)[1].split()[19]
 token=str(os.getpid())+':'+start;marker=os.path.join(base,'surround-intro-after-profile.json')
 try:
  with open(marker) as f:previous=json.load(f)
 except (OSError,ValueError):previous={}
 if previous.get('process')==token:return
 # Home's onload is the trigger; inspect the settled window after the delay.
 if xbmcgui.getCurrentWindowId()==10029:return
 receipt={'process':token,'requested_at':time.time(),'state':'WAITING_AFTER_PROFILE','profile':xbmc.getInfoLabel('System.ProfileName'),'clip':NAME,'home_settle_seconds':3,'ac3_silence_seconds':2.5}
 def save():
  temp=marker+'.new'
  with open(temp,'w') as f:json.dump(receipt,f)
  os.replace(temp,marker)
 save();monitor=xbmc.Monitor()
 if monitor.waitForAbort(3):return
 # Never interrupt a film already started or follow a user into another window.
 if not xbmc.getCondVisibility('System.LoggedOn') or xbmc.Player().isPlaying() or xbmcgui.getCurrentWindowId()!=10000 or xbmc.getCondVisibility('System.ScreenSaverActive'):
  receipt['state']='SKIPPED_USER_ACTIVITY';save();return
 clip=os.path.join(base,NAME)
 if not os.path.isfile(clip):receipt['state']='MISSING_CLIP';save();return
 home=xbmcgui.Window(10000);player=IntroPlayer();home.clearProperty(CANCEL);home.setProperty(RUNNING,'1')
 def owns_playback():
  try:return player.isPlaying() and player.getPlayingFile()==clip
  except RuntimeError:return False
 try:
  xbmc.executebuiltin('ActivateWindow('+str(DIALOG)+')')
  item=xbmcgui.ListItem(label='Momentum Kino-Start',path=clip);item.setContentLookup(False);item.setMimeType('video/x-matroska')
  tag=item.getVideoInfoTag();tag.setTitle('Momentum Kino-Start');tag.setDuration(8)
  receipt['state']='STARTING';receipt['play_requested_at']=time.time();save()
  player.play(clip,item,windowed=True)
  begin=time.monotonic();measured=False;cancel_at=None
  while not monitor.waitForAbort(.10):
   if home.getProperty(CANCEL) or xbmcgui.getCurrentWindowId()!=10000:
    cancel_at=cancel_at or time.monotonic()
    if owns_playback():player.stop()
    # Keep callbacks alive briefly to consume an already queued play request.
    if player.ended or time.monotonic()-cancel_at>3:receipt['state']='SKIPPED';break
   if player.started and not measured:
    measured=True;receipt['av_started_at']=time.time()
    receipt['stream']={label:xbmc.getInfoLabel(label) for label in ['VideoPlayer.AudioCodec','VideoPlayer.AudioChannels','Player.Process(audiodecoder)','System.CurrentWindow']}
    receipt['state']='PLAYING';save()
   if player.ended:
    receipt['state']='SKIPPED' if cancel_at else ('FAILED' if player.error or not player.started else 'COMPLETE');break
   if time.monotonic()-begin>15:
    if owns_playback():player.stop()
    receipt['state']='TIMEOUT';break
  else:receipt['state']='KODI_EXIT'
 except Exception as error:
  if owns_playback():player.stop()
  receipt['state']='FAILED';receipt['error']=str(error);xbmc.log('Momentum intro: '+str(error),xbmc.LOGWARNING)
 finally:
  home.clearProperty(RUNNING);home.clearProperty(CANCEL)
  xbmc.executebuiltin('Dialog.Close('+str(DIALOG)+',true)')
  receipt['finished_at']=time.time();save()

try:main()
except Exception as error:
 xbmcgui.Window(10000).clearProperty(RUNNING)
 xbmc.executebuiltin('Dialog.Close('+str(DIALOG)+',true)')
 xbmc.log('Momentum intro: '+str(error),xbmc.LOGWARNING)
