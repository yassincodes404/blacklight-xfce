#!/usr/bin/python3
"""Fixed XFCE audio card. Event-driven controls; 12-fps record motion only while playing."""
import argparse
from pathlib import Path
import re
import math
import time

from desktop_layer import anchor_audio

import gi
gi.require_version('Gtk','3.0');gi.require_version('Gdk','3.0');gi.require_version('GdkPixbuf','2.0')
from gi.repository import Gtk, Gdk, Gio, GLib, Pango, GdkPixbuf


class AudioCard(Gtk.Application):
    def __init__(self, preview=False):
        super().__init__(application_id='org.galinia.AudioCard.Preview' if preview else 'org.galinia.AudioCard')
        self.preview=preview; self.window=None; self.players={};self.selected=None
        self.animation=0;self.obscured=False;self.is_playing=False;self.frame=0;self.position_base=0.;self.position_time=time.monotonic();self.duration=0.;self.track_key=None
        self.volume_job=0;self.refresh_job=0;self.syncing=False;self.closed=False;self.pending=[]

    def do_activate(self):
        if self.window:
            return
        self.window=Gtk.ApplicationWindow(application=self,title='Galinia Audio')
        win=self.window;win.set_name('galinia-audio');win.set_decorated(False);win.set_resizable(False)
        win.set_app_paintable(True)
        visual=win.get_screen().get_rgba_visual()
        if visual:win.set_visual(visual)
        self.wayland = Gdk.Display.get_default().__gtype__.name == 'GdkWaylandDisplay'
        if self.wayland:
            self.layer = anchor_audio(win)
        else:
            win.set_type_hint(Gdk.WindowTypeHint.UTILITY);win.set_skip_taskbar_hint(True);win.set_skip_pager_hint(True)
            win.set_keep_below(True);win.stick()
        win.set_focus_on_map(False)
        css=Gtk.CssProvider();css.load_from_data(b'''
        #galinia-audio { background: transparent; color: #f0f0f6; border: none; box-shadow: none; }
        #galinia-audio .heading { color: #bcbcc8; font-size: 9px; font-weight: bold; letter-spacing: 2px; }
        #galinia-audio .track { color: #f0f0f6; font-size: 16px; font-weight: bold; }
        #galinia-audio .muted { color: #bcbcc8; font-size: 10px; }
        #galinia-audio button { background: transparent; color: #f0f0f6; border: none; box-shadow: none; border-radius: 18px; padding: 7px; transition: background-color 120ms ease; }
        #galinia-audio button:hover { background: rgba(255,255,255,.12); }
        #galinia-audio button:focus { outline: 1px solid #bcbcc8; }
        #galinia-audio .play { background: rgba(255,255,255,.16); color: #f0f0f6; }
        #galinia-audio .play:hover { background: rgba(255,255,255,.25); }
        #galinia-audio scale trough { background: rgba(255,255,255,.18); min-height: 3px; border-radius: 3px; }
        #galinia-audio scale highlight { background: #f0f0f6; }
        #galinia-audio scale slider { min-width: 8px; min-height: 8px; background: #f0f0f6; border: none; box-shadow: none; }
        #galinia-audio progressbar trough { min-height: 3px; background: rgba(255,255,255,.18); border: none; }
        #galinia-audio progressbar progress { min-height: 3px; background: #f0f0f6; border: none; }
        ''')
        Gtk.StyleContext.add_provider_for_screen(win.get_screen(),css,800)
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8,margin=16);box.set_size_request(320,-1);win.add(box)
        row=Gtk.Box(spacing=12)
        self.record_frames=[self.record_frame(0)]
        self.record=Gtk.Image.new_from_pixbuf(self.record_frames[0]);self.record.set_size_request(84,84)
        row.pack_start(self.record,False,False,0)
        details=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6)
        details.pack_start(self.label('01 / NOW PLAYING','heading'),False,False,2)
        self.title=self.label('Nothing playing','track');self.artist=self.label('Open your music player','muted')
        self.title.set_width_chars(20);self.title.set_max_width_chars(20)
        self.artist.set_width_chars(28);self.artist.set_max_width_chars(28)
        details.pack_start(self.title,False,False,0);details.pack_start(self.artist,False,False,0)
        row.pack_start(details,True,True,0);box.pack_start(row,False,False,0)
        self.progress=Gtk.ProgressBar();self.progress.set_fraction(0);box.pack_start(self.progress,False,False,2)
        times=Gtk.Box();self.elapsed=self.label('00:00','muted');self.total=self.label('--:--','muted')
        times.pack_start(self.elapsed,False,False,0);times.pack_end(self.total,False,False,0);box.pack_start(times,False,False,0)
        controls=Gtk.Box(spacing=8);controls.set_halign(Gtk.Align.CENTER)
        self.previous=self.button('media-skip-backward-symbolic','Previous track',lambda:self.player_call('Previous'))
        self.play=self.button('media-playback-start-symbolic','Play or pause',lambda:self.player_call('PlayPause'));self.play.get_style_context().add_class('play')
        self.next=self.button('media-skip-forward-symbolic','Next track',lambda:self.player_call('Next'))
        for button in [self.previous,self.play,self.next]:controls.pack_start(button,False,False,0);button.set_sensitive(False)
        box.pack_start(controls,False,False,0)
        volume=Gtk.Box(spacing=8)
        self.mute=self.button('audio-volume-high-symbolic','Mute or unmute output',lambda:self.command(['wpctl','set-mute','@DEFAULT_AUDIO_SINK@','toggle']))
        self.scale=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,0,100,1);self.scale.set_draw_value(False)
        self.scale.get_accessible().set_name('Output volume');self.scale.connect('value-changed',self.volume_changed)
        self.percent=self.label('--','muted');self.percent.set_width_chars(5)
        volume.pack_start(self.mute,False,False,0);volume.pack_start(self.scale,True,True,0);volume.pack_start(self.percent,False,False,0)
        settings=self.button('preferences-system-symbolic','Open sound settings',lambda:self.command(['pavucontrol']))
        volume.pack_end(settings,False,False,0);box.pack_start(volume,False,False,0)
        if not self.wayland:
            win.add_events(Gdk.EventMask.VISIBILITY_NOTIFY_MASK)
            win.connect('visibility-notify-event',self.visibility)
            win.get_screen().connect('monitors-changed',self.position)
            win.connect('realize',self.position)
        win.connect('destroy',self.shutdown)
        win.show_all()
        if self.preview:
            self.title.set_text('GALINIA MIX');self.artist.set_text('AUDIO CHANNEL / STEREO')
            self.duration=214.;self.position_base=72.;self.update_progress()
            self.scale.set_value(45);self.percent.set_text('45%');return
        self.bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
        self.bus.signal_subscribe('org.freedesktop.DBus','org.freedesktop.DBus','NameOwnerChanged','/org/freedesktop/DBus',None,Gio.DBusSignalFlags.NONE,self.owner_changed)
        self.bus.call('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','ListNames',None,None,Gio.DBusCallFlags.NONE,3000,None,self.got_names)
        self.refresh_volume();self.subscribe_audio()

    def label(self,text,style):
        label=Gtk.Label(label=text,xalign=0);label.set_ellipsize(Pango.EllipsizeMode.END);label.set_max_width_chars(34)
        label.get_style_context().add_class(style);return label

    def button(self,icon,label,callback):
        button=Gtk.Button();button.set_image(Gtk.Image.new_from_icon_name(icon,Gtk.IconSize.BUTTON))
        button.set_tooltip_text(label);button.get_accessible().set_name(label);button.connect('clicked',lambda *_:callback());return button

    def position(self,*_):
        if self.wayland or self.window is None:return
        display=Gdk.Display.get_default();monitor=display.get_primary_monitor() or display.get_monitor(0)
        if monitor:
            area=monitor.get_workarea();self.window.move(area.x+area.width-self.window.get_allocated_width()-24,area.y+area.height-self.window.get_allocated_height()-24)

    def shutdown(self,*_):
        self.closed=True
        if self.animation:GLib.source_remove(self.animation);self.animation=0
        if hasattr(self,'subscription'):self.subscription.force_exit()
        self.window=None

    def command(self,argv,callback=None):
        if self.closed or self.preview:return
        try:
            process=Gio.Subprocess.new(argv,Gio.SubprocessFlags.STDOUT_PIPE|Gio.SubprocessFlags.STDERR_PIPE)
            self.pending.append(process)
            def done(proc,result):
                if proc in self.pending:self.pending.remove(proc)
                try:
                    ok,out,error=proc.communicate_utf8_finish(result)
                    if not proc.get_successful():raise RuntimeError(error.strip() or 'Audio command failed')
                    if callback:callback(out)
                except (GLib.Error,RuntimeError) as error:
                    if self.window:self.window.set_tooltip_text(str(error)[:200])
            process.communicate_utf8_async(None,None,done)
        except GLib.Error as error:
            if self.window:self.window.set_tooltip_text(str(error))

    def volume_changed(self,*_):
        if self.syncing or self.preview:return
        self.percent.set_text(str(round(self.scale.get_value()))+'%')
        if self.volume_job:GLib.source_remove(self.volume_job)
        self.volume_job=GLib.timeout_add(150,self.set_volume)

    def set_volume(self):
        self.volume_job=0
        self.command(['wpctl','set-volume','@DEFAULT_AUDIO_SINK@',f'{self.scale.get_value()/100:.2f}'])
        return False

    def refresh_volume(self):
        self.refresh_job=0
        def update(text):
            match=re.search(r'Volume:\s*([0-9.]+)',text)
            if not match or self.closed:return
            value=round(float(match[1])*100);muted='[MUTED]' in text
            self.syncing=True;self.scale.set_value(min(value,100));self.syncing=False
            self.percent.set_text('Muted' if muted else str(value)+'%')
            self.mute.set_image(Gtk.Image.new_from_icon_name('audio-volume-muted-symbolic' if muted else 'audio-volume-high-symbolic',Gtk.IconSize.BUTTON))
        self.command(['wpctl','get-volume','@DEFAULT_AUDIO_SINK@'],update)
        return False

    def subscribe_audio(self):
        if self.closed:return False
        try:
            self.subscription=Gio.Subprocess.new(['pactl','subscribe'],Gio.SubprocessFlags.STDOUT_PIPE|Gio.SubprocessFlags.STDERR_SILENCE)
            self.events=Gio.DataInputStream.new(self.subscription.get_stdout_pipe())
            self.events.read_line_async(GLib.PRIORITY_DEFAULT,None,self.audio_event)
        except GLib.Error:
            GLib.timeout_add_seconds(5,self.subscribe_audio)
        return False

    def audio_event(self,stream,result):
        if self.closed:return
        try:
            line,_=stream.read_line_finish_utf8(result)
            if line is None:
                GLib.timeout_add_seconds(5,self.subscribe_audio);return
            if (' on sink ' in line or ' on server ' in line) and not self.refresh_job:
                self.refresh_job=GLib.timeout_add(100,self.refresh_volume)
            stream.read_line_async(GLib.PRIORITY_DEFAULT,None,self.audio_event)
        except GLib.Error:
            GLib.timeout_add_seconds(5,self.subscribe_audio)

    def got_names(self,bus,result):
        try:
            for name in bus.call_finish(result).unpack()[0]:
                if name.startswith('org.mpris.MediaPlayer2.'):self.add_player(name)
        except GLib.Error:pass

    def owner_changed(self,bus,sender,path,interface,signal,params):
        name,old,new=params.unpack()
        if not name.startswith('org.mpris.MediaPlayer2.'):return
        self.players.pop(name,None)
        if new:self.add_player(name)
        else:self.render_player()

    def add_player(self,name):
        def ready(source,result):
            try:
                proxy=Gio.DBusProxy.new_finish(result)
                if not proxy.get_name_owner():return
                self.players[name]=proxy
                proxy.connect('g-properties-changed',lambda *_:self.render_player())
                proxy.connect('g-signal',self.player_signal)
                self.render_player()
            except GLib.Error:pass
        Gio.DBusProxy.new(self.bus,Gio.DBusProxyFlags.NONE,None,name,'/org/mpris/MediaPlayer2','org.mpris.MediaPlayer2.Player',None,ready)

    def prop(self,proxy,name,default=None):
        value=proxy.get_cached_property(name)
        return value.unpack() if value is not None else default

    def render_player(self):
        if self.closed:return
        playing=[name for name,p in self.players.items() if self.prop(p,'PlaybackStatus')=='Playing']
        self.selected=playing[0] if playing else self.selected if self.selected in self.players else next(iter(self.players),None)
        proxy=self.players.get(self.selected)
        if proxy is None:
            self.title.set_text('Nothing playing');self.artist.set_text('Open your music player')
            self.set_playing(False);self.duration=0.;self.position_base=0.;self.update_progress()
            for button in [self.previous,self.play,self.next]:button.set_sensitive(False)
            return
        metadata=self.prop(proxy,'Metadata',{});status=self.prop(proxy,'PlaybackStatus','Stopped')
        self.title.set_text(str(metadata.get('xesam:title') or 'Ready to play')[:280])
        artists=metadata.get('xesam:artist',[])
        artist=', '.join(str(a) for a in artists) if isinstance(artists,list) else str(artists)
        self.artist.set_text((artist or self.selected.split('.')[-1])[:200])
        track=(self.selected,metadata.get('mpris:trackid'),metadata.get('xesam:title'))
        self.duration=max(0.,float(metadata.get('mpris:length',0))/1e6)
        changed=track!=self.track_key or (status=='Playing')!=self.is_playing
        if track!=self.track_key:self.position_base=0.;self.position_time=time.monotonic();self.track_key=track
        self.set_playing(status=='Playing')
        if changed:self.refresh_position(proxy,track)
        self.update_progress()
        self.title.set_tooltip_text(self.title.get_text())
        self.play.set_image(Gtk.Image.new_from_icon_name('media-playback-pause-symbolic' if status=='Playing' else 'media-playback-start-symbolic',Gtk.IconSize.BUTTON))
        can=self.prop(proxy,'CanControl',False)
        self.previous.set_sensitive(can and self.prop(proxy,'CanGoPrevious',False))
        self.next.set_sensitive(can and self.prop(proxy,'CanGoNext',False))
        self.play.set_sensitive(can and self.prop(proxy,'CanPause' if status=='Playing' else 'CanPlay',False))

    def record_frame(self,angle):
        # Rasterize this tiny procedural graphic once. Subsequent frames copy
        # 28 KiB and update only the glint; no repeated SVG renderer or decoder.
        if not hasattr(self,'record_pixels'):
            pixels=bytearray(84*84*4);glints=[]
            for y in range(84):
                for x in range(84):
                    dx,dy=x-41.5,y-41.5;radius=math.hypot(dx,dy);offset=(y*84+x)*4
                    alpha=max(0.,min(1.,29.5-radius))*.12
                    groove=max(0.,1.-min(abs(radius-22),abs(radius-26)))*.10
                    alpha=max(alpha,groove) if radius<29.5 else 0.
                    if radius<9.5:alpha=max(alpha,min(1.,9.5-radius))
                    pixels[offset:offset+4]=bytes((250,250,249,round(alpha*255)))
                    if abs(radius-25)<1.1:glints.append((offset,math.atan2(dy,dx),min(1.,1.1-abs(radius-25))))
            self.record_pixels,self.record_glints=pixels,glints
        pixels=bytearray(self.record_pixels);radians=math.radians(angle)
        for offset,direction,coverage in self.record_glints:
            if math.cos(direction-radians)>.94:
                pixels[offset:offset+4]=bytes((220,220,225,round((.12+.4*coverage)*255)))
        return GdkPixbuf.Pixbuf.new_from_bytes(GLib.Bytes.new(bytes(pixels)),GdkPixbuf.Colorspace.RGB,True,8,84,84,84*4)

    def current_position(self):
        return max(0.,self.position_base+(time.monotonic()-self.position_time if self.is_playing else 0.))

    def update_progress(self):
        def stamp(seconds):return f'{int(seconds)//60:02d}:{int(seconds)%60:02d}'
        value=min(self.current_position(),self.duration) if self.duration else 0.
        self.progress.set_fraction(value/self.duration if self.duration else 0.)
        self.elapsed.set_text(stamp(value));self.total.set_text(stamp(self.duration) if self.duration else '--:--')

    def set_playing(self,playing):
        if self.is_playing!=playing:
            self.position_base=self.current_position();self.position_time=time.monotonic()
        self.is_playing=playing
        if playing and not self.obscured and not self.animation:
            if len(self.record_frames)==1:self.record_frames=[self.record_frame(n*7.5) for n in range(48)]
            self.animation=GLib.timeout_add(83,self.animate)
        elif (not playing or self.obscured) and self.animation:GLib.source_remove(self.animation);self.animation=0

    def visibility(self,window,event):
        self.obscured=event.state==Gdk.VisibilityState.FULLY_OBSCURED
        self.set_playing(self.is_playing)
        if not self.obscured:self.update_progress()
        return False

    def animate(self):
        if self.closed or not self.is_playing:self.animation=0;return False
        self.frame+=1;self.record.set_from_pixbuf(self.record_frames[self.frame%len(self.record_frames)])
        if self.frame%12==0:self.update_progress()
        return True

    def refresh_position(self,proxy,track):
        def done(bus,result):
            try:
                value=bus.call_finish(result).unpack()[0]
                if self.track_key!=track or self.closed:return
                self.position_base=max(0.,float(value)/1e6);self.position_time=time.monotonic();self.update_progress()
            except (GLib.Error,ValueError,TypeError):pass
        self.bus.call(proxy.get_name(),'/org/mpris/MediaPlayer2','org.freedesktop.DBus.Properties','Get',
            GLib.Variant('(ss)',('org.mpris.MediaPlayer2.Player','Position')),None,Gio.DBusCallFlags.NONE,3000,None,done)

    def player_signal(self,proxy,sender,signal,parameters):
        if signal=='Seeked' and self.players.get(self.selected) is proxy:
            self.position_base=max(0.,parameters.unpack()[0]/1e6);self.position_time=time.monotonic();self.update_progress()

    def player_call(self,method):
        proxy=self.players.get(self.selected)
        if not proxy:return
        def done(source,result):
            try:source.call_finish(result)
            except GLib.Error as error:
                if self.window:self.window.set_tooltip_text(str(error)[:200])
        proxy.call(method,None,Gio.DBusCallFlags.NONE,3000,None,done)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--preview',action='store_true');args=parser.parse_args()
    raise SystemExit(AudioCard(args.preview).run([]))
