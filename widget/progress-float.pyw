"""Progress Float — OpenCode floating progress ball.
State machine: GREEN(active) → AMBER(thinking) → GRAY(idle) → RED(waiting)"""

import tkinter as tk
import threading, time, math, sys, os, atexit, ctypes, subprocess
import json as _json
import urllib.request, urllib.error
from PIL import Image, ImageDraw, ImageTk

_SPRITE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprites")

# Config from config.json
_config = {"port":19822,"cacheDir":"","thinkingTimeoutS":8,"staleThresholdS":60,"heartbeatThresholdS":15}
try:
    _cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.json")
    if os.path.exists(_cfg_path):
        with open(_cfg_path) as _f:
            _config.update(_json.load(_f))
except: pass

def _resolve_cache_dir():
    if sys.platform == "win32":
        _base = os.environ.get("APPDATA") or os.path.join(os.environ.get("USERPROFILE",""), "AppData", "Roaming")
        return os.path.join(_base, "progress-float")
    return os.path.join(os.environ.get("HOME",""), ".progress-float")

PORT = _config["port"]
CACHE_DIR = _config["cacheDir"] or _resolve_cache_dir()
THINKING_TIMEOUT = _config["thinkingTimeoutS"]
STALE_THRESHOLD = _config["staleThresholdS"]
HEARTBEAT_THRESHOLD = _config["heartbeatThresholdS"]
API = f"http://127.0.0.1:{PORT}/state"
LOCK_FILE = os.path.join(os.environ.get("TEMP","."), "opencode-progress-float.pid")

# Singleton
def _singleton():
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE) as f:
                pid = int(f.read().strip())
            if sys.platform == "win32":
                h = ctypes.windll.kernel32.OpenProcess(0x0400, False, pid)
                if h: ctypes.windll.kernel32.CloseHandle(h); return True
            else:
                try: os.kill(pid, 0); return True
                except OSError: pass
        except: pass
    with open(LOCK_FILE,"w") as f: f.write(str(os.getpid()))
    atexit.register(lambda: os.path.exists(LOCK_FILE) and os.remove(LOCK_FILE))
    return False
if _singleton(): sys.exit(0)

def _is_opencode_running():
    hb = os.path.join(CACHE_DIR, "heartbeat")
    sf = os.path.join(CACHE_DIR, "progress-state.json")
    try:
        if os.path.exists(hb):
            return (time.time() - os.path.getmtime(hb)) < HEARTBEAT_THRESHOLD
    except: pass
    try:
        if os.path.exists(sf):
            return (time.time() - os.path.getmtime(sf)) < STALE_THRESHOLD
    except: pass
    if sys.platform == "win32":
        try:
            r = subprocess.run(['tasklist','/fi','imagename eq OpenCode.exe','/fo','csv','/nh'],
                capture_output=True,text=True,timeout=3,
                creationflags=subprocess.CREATE_NO_WINDOW)
            return 'OpenCode.exe' in r.stdout or 'opencode.exe' in r.stdout.lower()
        except: pass
    else:
        try:
            r = subprocess.run(['pgrep','-x','OpenCode'], capture_output=True,text=True,timeout=3)
            return r.returncode == 0
        except: pass
    return True

# ── Theme ──
class T:
    BG="#0d0d1a"; CARD="#141428"; BORDER="#2a2a55"
    TEXT="#e4e4f0"; MUTED="#6b6b8a"
    GREEN="#10b981"; GREEN2="#34d399"
    AMBER="#f59e0b"; AMBER2="#fbbf24"
    GRAY="#4a4a6a"
    RED="#ef4444"; DONE_CLR="#6366f1"
    MAGENTA="#ff00ff"

CAT_COLORS={
    "bash":"#06b6d4","read":"#3b82f6","write":"#f59e0b",
    "edit":"#8b5cf6","grep":"#ec4899","glob":"#14b8a6",
    "task":"#6366f1","webfetch":"#ef4444","question":"#f97316",
    "todowrite":"#22c55e","skill":"#a855f7",
    "opencode":"#7c3aed","explore":"#06b6d4","general":"#f59e0b",
    "dreamer":"#a855f7","historian":"#ec4899","sidekick":"#14b8a6",
}

CAT_ICONS={
    "bash":">_","read":"\u25a7","write":"+","edit":"\u2710",
    "grep":"\u229e","glob":"\u25a6","task":"\u2691",
    "webfetch":"\u21c4","question":"?","todowrite":"\u2261","skill":"\u2666",
}

BR=30; CW,CH=120,120; PW,PH=320,400
SR=55; SC=140  # sprite radius, sprite canvas size
FEATHER=10

def _load_sprites(size=110, feather=10):
    """Load PNG sprites, resize and apply radial-gradient circular mask. Returns {phase: PhotoImage}."""
    import numpy as np
    sprites = {}
    # Build radial gradient mask: 255 at center, 0 at edge, smooth transition
    mask = np.zeros((size, size), dtype=np.uint8)
    cy = cx = size / 2.0
    radius = size / 2.0
    inner = radius - feather
    for y in range(size):
        dy = y - cy
        for x in range(size):
            dist = math.sqrt((x - cx)**2 + dy*dy)
            if dist <= inner:
                mask[y, x] = 255
            elif dist <= radius:
                t = (radius - dist) / feather
                mask[y, x] = int(t * 255)
    pil_mask = Image.fromarray(mask, mode="L")
    for phase, fn in [("executing","working"), ("thinking","thinking"), ("idle","idle"), ("waiting","alert")]:
        p = os.path.join(_SPRITE_DIR, fn + ".png")
        if not os.path.exists(p): continue
        img = Image.open(p).convert("RGBA").resize((size, size), Image.LANCZOS)
        img.putalpha(pil_mask)
        sprites[phase] = ImageTk.PhotoImage(img)
    return sprites

class App:
    def __init__(self):
        self.root=tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost",True)
        self.root.attributes("-transparentcolor",T.MAGENTA)
        self.root.configure(bg=T.MAGENTA)
        sw,sh=self.root.winfo_screenwidth(),self.root.winfo_screenheight()
        self.root.geometry(f"{CW}x{CH}+{sw-CW-30}+{sh-CH-80}")
        self.canvas=tk.Canvas(self.root,width=CW,height=CH,bg=T.MAGENTA,highlightthickness=0)
        self.canvas.pack()
        self.canvas.bind("<Button-1>",self._click)
        self.canvas.bind("<Button-3>",self._right_click)
        self.canvas.bind("<B1-Motion>",self._drag)

        # data
        self.tc=0; self.phase="idle"; self.waiting=False
        self.projects={}; self.sessions={}; self.tools=[]
        self.task_count=0; self.pulse=0.0
        self.panel=None; self.pc=None; self.popen=False; self.running=True

        # sprite mode
        self.sprite_mode = False
        self._skin_var = tk.StringVar(value="ball")
        self.sprites = _load_sprites()
        self.zzzs = []         # idle Zzz float particles
        self._decor_timer = 0  # ticks for decor animations

        threading.Thread(target=self._poll,daemon=True).start()
        self._anim()
        self.root.protocol("WM_DELETE_WINDOW",self._close)
        self.root.mainloop()

    # ── Poll ──
    def _poll(self):
        _dead_ticks=0
        while self.running:
            # Auto-close if OpenCode is gone for 60s
            if not _is_opencode_running():
                _dead_ticks+=1
                if _dead_ticks>120:
                    self.root.after(0,self._close)
                    return
            else:
                _dead_ticks=0
            try:
                req=urllib.request.Request(API)
                with urllib.request.urlopen(req,timeout=3) as r:
                    d=_json.loads(r.read().decode())
                self.tc=d.get("toolCount",0)
                self.tools=d.get("activeTools",[])
                self.sessions=d.get("sessions",{})
                self.projects=d.get("projects",{})
                if self.projects:
                    tmp = []
                    for p in self.projects.values():
                        tmp.extend(p.get("activeTools", []))
                    self.tools = tmp
                self.task_count=d.get("taskCount",0)
                self.last_updated = d.get("lastUpdated", "")
                self.phase = d.get("phase", "idle")
                self.waiting = d.get("waitingForUser", False)
            except Exception:
                pass
            time.sleep(0.5)

    # ── Draw ──
    def _draw(self):
        c=self.canvas; c.delete("all")
        p=self.phase

        if self.sprite_mode and p in self.sprites:
            self._draw_sprite(c, p)
        else:
            cx, cy = CW//2, CH//2
            self._draw_ball(c, cx, cy, BR, p)

    def _draw_sprite(self, c, p):
        cx = cy = SC // 2; r = SR
        # glow ring — dynamic radius around sprite
        glow_map = {"executing":(0x34,0xd3,0x99),"thinking":(0xf5,0x9e,0x0b),"waiting":(0xef,0x44,0x44)}
        if p in glow_map:
            gr2,gg2,gb2 = glow_map[p]
            for i in range(3):
                pi=(self.pulse+i*0.33)%1.0; gr2_=r+4+pi*18
                alpha=int((1-pi)*200+55)
                c.create_oval(cx-gr2_,cy-gr2_,cx+gr2_,cy+gr2_,
                    outline=f"#{gr2:02x}{gg2:02x}{min(255,gb2+alpha):02x}",width=2)
        # sprite image
        c.create_image(cx, cy, image=self.sprites[p])
        # decor: state-specific indicators outside sprite
        self._draw_decor(c, p, cx, cy, r)
        # badge — top-right
        if self.tc > 0:
            bx, by = cx + r - 2, cy - r + 12
            c.create_oval(bx-11,by-11,bx+11,by+11,fill=T.RED,outline="#ffffff",width=1)
            txt=str(self.tc) if self.tc<100 else "99"; fs=9 if len(txt)<=1 else 8
            c.create_text(bx,by+1,text=txt,fill="#ffffff",font=("Segoe UI",fs,"bold"))

    def _draw_decor(self, c, p, cx, cy, r):
        """Draw phase-specific decorations outside the sprite portrait."""
        if p == "executing":
            # rotating dots around the sprite edge
            for i in range(4):
                a = (self.pulse * 3 + i * 1.57) % 6.283
                dx = math.cos(a) * (r + 10)
                dy = math.sin(a) * (r + 10)
                sz = 3
                c.create_oval(cx+dx-sz, cy+dy-sz, cx+dx+sz, cy+dy+sz,
                    fill=T.GREEN2, outline="")
        elif p == "thinking":
            ps = (math.sin(self.pulse * 2) + 1) / 2
            fs = 11 + int(ps * 4)
            c.create_text(cx, cy + r + 12, text="?", fill=T.AMBER2,
                font=("Segoe UI", fs, "bold"))
        elif p == "waiting":
            ps = (math.sin(self.pulse * 3) + 1) / 2
            fs = 15 + int(ps * 6)
            c.create_text(cx, cy + r + 10, text="!", fill=T.RED,
                font=("Segoe UI", fs, "bold"))
        else:  # idle
            for z in self.zzzs:
                fs = max(7, 11 - z["age"] // 15)
                c.create_text(z["x"], z["y"], text="z",
                    fill=T.MUTED, font=("Segoe UI", fs, "bold"))

    def _draw_ball(self, c, cx, cy, r, p):
        # body color
        bc={"executing":T.GREEN,"thinking":T.AMBER,"idle":T.GRAY,"waiting":T.RED}.get(p,T.GRAY)
        hl=self._lerp(bc,"#ffffff",0.12)

        # glow
        if p in ("executing","thinking","waiting"):
            glow_r,glow_g,glow_b={
                "executing":(0x34,0xd3,0x99),"thinking":(0xf5,0x9e,0x0b),"waiting":(0xef,0x44,0x44),
            }.get(p,(0xf5,0x9e,0x0b))
            for i in range(3):
                pi=(self.pulse+i*0.33)%1.0; gr2=r+4+pi*20
                alpha=int((1-pi)*200+55)
                c.create_oval(cx-gr2,cy-gr2,cx+gr2,cy+gr2,outline=f"#{glow_r:02x}{glow_g:02x}{min(255,glow_b+alpha):02x}",width=3)

        # shadow
        c.create_oval(cx-r-1,cy-r+2,cx+r-1,cy+r+2,fill="#1a1a2e",outline="",stipple="gray25")

        # body
        c.create_oval(cx-r,cy-r,cx+r,cy+r,fill=bc,outline=hl,width=2)

        # inner highlight
        c.create_oval(int(cx-r*0.6),int(cy-r*0.6),int(cx+r*0.1),int(cy+r*0.1),fill="#4a4a7a",outline="",stipple="gray50")

        # center icon
        if p=="executing":
            for i in range(4):
                a=(self.pulse*3+i*1.57)%6.283
                dx=math.cos(a)*r*.35; dy=math.sin(a)*r*.35; sz=3
                c.create_oval(cx+dx-sz,cy+dy-sz,cx+dx+sz,cy+dy+sz,fill="#e0e0ff",outline="")
        elif p=="thinking":
            ps=(math.sin(self.pulse*2)+1)/2; sz=4+ps*3
            c.create_oval(cx-sz,cy-sz,cx+sz,cy+sz,fill=T.AMBER2,outline="")
        elif p=="waiting":
            ps=(math.sin(self.pulse*3)+1)/2; fs=14+int(ps*4)
            c.create_text(cx,cy,text="!",fill="#ffffff",font=("Segoe UI",fs,"bold"))
        else:
            c.create_oval(cx-7,cy-7,cx+7,cy+7,fill="",outline="#a0a0c0",width=2)

        # badge
        if self.tc>0:
            bx,by=cx+r-2,cy-r-2; br=11
            c.create_oval(bx-br-3,by-br-3,bx+br+3,by+br+3,fill=T.RED,outline="",stipple="gray50")
            c.create_oval(bx-br,by-br,bx+br,by+br,fill=T.RED,outline="#aaaaaa",width=1)
            txt=str(self.tc) if self.tc<100 else "99"; fs=9 if len(txt)<=1 else 8
            c.create_text(bx,by+1,text=txt,fill="#ffffff",font=("Segoe UI",fs,"bold"))

    def _anim(self):
        self.pulse += 0.05
        self._decor_timer += 1

        # idle Zzz float animation: spawn every ~3s, drift up, shrink, expire
        if self.sprite_mode and self.phase == "idle" and self._decor_timer % 90 == 0:
            cx = SC // 2
            self.zzzs.append({"x": cx - 30, "y": SC - 10, "age": 0})
        # update existing zzz particles
        for z in self.zzzs[:]:
            z["y"] -= 0.4
            z["age"] += 1
            if z["age"] > 80:
                self.zzzs.remove(z)
        if self.phase != "idle":
            self.zzzs.clear()

        self._draw()
        if self.running: self.root.after(33, self._anim)

    def _lerp(self,c1,c2,t):
        r1,g1,b1=int(c1[1:3],16),int(c1[3:5],16),int(c1[5:7],16)
        r2,g2,b2=int(c2[1:3],16),int(c2[3:5],16),int(c2[5:7],16)
        return f"#{int(r1+(r2-r1)*t):02x}{int(g1+(g2-g1)*t):02x}{int(b1+(b2-b1)*t):02x}"

    def _elapsed(self,iso):
        if not iso: return ""
        try:
            dt=max(0,time.time()-time.mktime(time.strptime(iso[:19],"%Y-%m-%dT%H:%M:%S")))
            if dt<60: return f"{int(dt)}s"
            if dt<3600: return f"{int(dt//60)}m{int(dt%60)}s"
            return f"{int(dt//3600)}h{int(dt%3600//60)}m"
        except: return ""

    # ── Panel ──
    def _show_panel(self):
        if self.panel: return
        self.popen=True
        self.panel=tk.Toplevel(self.root)
        self.panel.overrideredirect(True); self.panel.attributes("-topmost",True)
        self.panel.attributes("-transparentcolor",T.MAGENTA); self.panel.configure(bg=T.MAGENTA)
        bx,by=self.root.winfo_x(),self.root.winfo_y()
        w = SC if self.sprite_mode else CW
        self.panel.geometry(f"{PW}x{PH}+{max(0,bx-PW+w)}+{max(0,by-PH-12)}")
        self.pc=tk.Canvas(self.panel,width=PW,height=PH,bg=T.MAGENTA,highlightthickness=0)
        self.pc.pack()
        self.panel.bind("<FocusOut>",lambda e:self._hide_panel())
        self.root.after(50,lambda:self.panel and self.panel.focus_force())
        self._refresh()

    def _rrect(self,c,x1,y1,x2,y2,r,**kw):
        pts=[x1+r,y1, x2-r,y1, x2,y1, x2,y1+r, x2,y2-r, x2,y2, x2-r,y2, x1+r,y2, x1,y2, x1,y2-r, x1,y1+r, x1,y1]
        c.create_polygon(pts,smooth=True,**kw)

    def _refresh(self):
        if not self.pc: return
        c=self.pc; c.delete("all"); w,h=PW,PH; pad=12

        # bg
        self._rrect(c,pad,pad,w-pad,h-pad,18,fill=T.CARD,outline=T.BORDER,width=1)

        # header
        hy=pad+16; p=self.phase
        if p=="executing": dot,dc,title="\u25cf",T.GREEN,"Active"
        elif p=="thinking": dot,dc,title="\u25cf",T.AMBER,"Thinking"
        elif p=="waiting": dot,dc,title="\u25cf",T.RED,"Waiting for you"
        else: dot,dc,title="\u25cb",T.MUTED,"Idle"
        c.create_text(pad+22,hy,text=dot,fill=dc,font=("Segoe UI",12),anchor="w")
        nproj=len(self.projects or {})
        if nproj>1: title+=f" \u2014 {nproj} projects"
        c.create_text(pad+44,hy,text=title,fill=T.TEXT,font=("Segoe UI",13,"bold"),anchor="w")
        c.create_text(w-pad-16,hy,text=f"{self.tc} active" if self.phase in ("executing","waiting") else str(self.task_count),fill=T.MUTED,font=("Segoe UI",10),anchor="e")
        dy=hy+16; c.create_line(pad+16,dy,w-pad-16,dy,fill=T.BORDER,width=1)

        ly=dy+12; projs=self.projects or {}
        tools=self.tools or []

        # Build groups
        groups=[]
        if len(projs)>1:
            for pn in sorted(projs):
                p=projs[pn]
                groups.append(("project",pn,p.get("active",False),p.get("toolCount",0),p.get("taskCount",0),p.get("activeTools",[]),p.get("sessions",{}),pn,"","",[]))
        elif len(projs)==1:
            pn,p=next(iter(projs.items()))
            ss=p.get("sessions",{}) or self.sessions
            pt=p.get("activeTools",[]) or tools
            if ss:
                for sid,si in sorted(ss.items(),key=lambda kv:kv[1].get("runningCount",0),reverse=True):
                    a=si.get("agent","?"); st=[t for t in pt if t.get("sessionID")==sid]
                    pname=si.get("projectName","")
                    stat=si.get("status","idle")
                    act=si.get("activity","Idle")
                    rdescs=si.get("runningDescriptions",[])
                    groups.append(("agent",a,si.get("active",False),si.get("runningCount",0),si.get("taskCount",0),st,{},pname,stat,act,rdescs))
            elif pt:
                groups=self._fallback(pt)
        elif self.sessions:
            for sid,si in sorted(self.sessions.items(),key=lambda kv:kv[1].get("runningCount",0),reverse=True):
                a=si.get("agent","?"); st=[t for t in tools if t.get("sessionID")==sid]
                pname=si.get("projectName","")
                stat=si.get("status","idle")
                act=si.get("activity","Idle")
                rdescs=si.get("runningDescriptions",[])
                groups.append(("agent",a,si.get("active",False),si.get("runningCount",0),si.get("taskCount",0),st,{},pname,stat,act,rdescs))
        else:
            groups=self._fallback(tools)

        if not groups:
            c.create_text(w//2,ly+60,text="Waiting for tasks...",fill=T.MUTED,font=("Segoe UI",11))
        else:
            ch=106
            for kind,label,is_a,run,total,tasks,gt,_,pname,stat,act,rdescs in groups:
                if ly+ch>h-pad-40: break
                lc=CAT_COLORS.get(label,T.ACCENT2 if kind=="project" else "#7c3aed")
                self._rrect(c,pad+6,ly,w-pad-6,ly+ch-4,10,fill="#1a1a30",outline="#2a2a55",width=1)
                # badge row
                bw=max(60,len(label)*9+20)
                self._rrect(c,pad+20,ly+6,pad+20+bw,ly+24,6,fill=lc+"44",outline=lc+"88",width=1)
                c.create_text(pad+20+bw//2,ly+15,text=label,fill=lc,font=("Segoe UI",10,"bold"))
                if kind=="project":
                    c.create_text(pad+20+bw+8,ly+15,text="project",fill=T.MUTED,font=("Segoe UI",8),anchor="w")
                elif pname:
                    c.create_text(pad+20+bw+8,ly+15,text="@"+pname,fill=T.MUTED,font=("Segoe UI",8),anchor="w")
                # activity description
                icon={"executing":"\u25b6","thinking":"\u25d0","idle":"\u25cb"}.get(stat,"\u25cb")
                icon_c={"executing":T.GREEN,"thinking":T.AMBER,"idle":T.MUTED}.get(stat,T.MUTED)
                c.create_text(pad+28,ly+34,text=icon,fill=icon_c,font=("Segoe UI",8),anchor="w")
                c.create_text(pad+44,ly+34,text=act,fill=T.TEXT,font=("Segoe UI",9),anchor="w")
                # sub-item: running tool details
                sub_y=ly+52
                if rdescs:
                    first_desc=rdescs[0] if rdescs else ""
                    if len(rdescs)>1: first_desc+=f" +{len(rdescs)-1} more"
                    c.create_text(pad+44,sub_y,text=first_desc,fill=T.MUTED,font=("Segoe UI",8),anchor="w")
                # stats row
                dot="\u25cf" if (is_a or run>0) else "\u25cb"
                dc2=T.GREEN if (is_a or run>0) else T.MUTED
                c.create_text(pad+28,ly+70,text=dot,fill=dc2,font=("Segoe UI",9),anchor="w")
                c.create_text(pad+48,ly+70,text=f"{run}/{total} tools",fill=T.MUTED,font=("Segoe UI",9),anchor="w")
                c.create_text(w-pad-22,ly+70,text=f"{tasks} tasks",fill=T.MUTED,font=("Segoe UI",9),anchor="e")
                # dot bar
                dx=pad+24; max_d=(w-pad*2-50)//11; sh=0
                for t in gt[-max_d:]:
                    if sh>=max_d: c.create_text(dx+4,ly+86,text=f"+{len(gt)-sh}",fill=T.MUTED,font=("Segoe UI",8)); break
                    st=t.get("status",""); dc3=T.GREEN if st=="running" else T.DONE_CLR
                    tc2=CAT_COLORS.get(t.get("tool",""),T.MUTED)
                    c.create_oval(dx,ly+82,dx+8,ly+90,fill=tc2,outline=dc3,width=1)
                    dx+=11; sh+=1
                ly+=ch+4

        fy=h-pad-20; c.create_line(pad+16,fy-8,w-pad-16,fy-8,fill=T.BORDER,width=1)
        ts=self.tools[0].get("lastUpdated","") if self.tools else ""
        if not ts: ts=self.last_updated if hasattr(self,"last_updated") else ""
        ts=ts[:19].replace("T"," ") if ts else ""
        c.create_text(pad+22,fy+2,text=f"Updated {ts}",fill=T.MUTED,font=("Segoe UI",9),anchor="w")
        if self.panel: self.root.after(1000,self._refresh)

    def _fallback(self,tools):
        g=[]; ba={}
        for t in tools:
            a=t.get("agent","opencode")
            ba.setdefault(a,[]).append(t)
        for a,at in sorted(ba.items(),key=lambda kv:sum(1 for t in kv[1] if t.get("status")=="running"),reverse=True):
            rn=sum(1 for t in at if t.get("status")=="running")
            g.append(("agent",a,rn>0,rn,len(at),self.task_count,at,{},"","idle" if rn==0 else "executing","Idle" if rn==0 else f"{at[0].get('tool','?')}",[]))
        return g

    def _hide_panel(self):
        self.popen=False
        if self.panel:
            try: self.panel.destroy()
            except: pass
        self.panel=None; self.pc=None

    # ── Interaction ──
    def _click(self,e):
        if self.popen: self._hide_panel()
        else: self._show_panel()

    def _right_click(self,event):
        menu=tk.Menu(self.root,tearoff=0)
        appearance=tk.Menu(menu,tearoff=0)
        appearance.add_radiobutton(label="Ball", variable=self._skin_var, value="ball",
            command=lambda: self._set_skin("ball"))
        appearance.add_radiobutton(label="Sprite", variable=self._skin_var, value="sprite",
            command=lambda: self._set_skin("sprite"))
        appearance.add_separator()
        appearance.add_command(label="+ Add skin...", state="disabled")
        menu.add_cascade(label="Appearance", menu=appearance)
        menu.add_separator()
        menu.add_command(label="Exit",command=self._close)
        menu.post(event.x_root,event.y_root)

    def _set_skin(self, skin):
        self.sprite_mode = (skin == "sprite")
        w = SC if self.sprite_mode else CW
        h = SC if self.sprite_mode else CH
        self.canvas.config(width=w, height=h)
        self.root.geometry(f"{w}x{h}")
        self.zzzs.clear()

    def _drag(self,e):
        w = SC if self.sprite_mode else CW
        h = SC if self.sprite_mode else CH
        x=self.root.winfo_x()+e.x-w//2
        y=self.root.winfo_y()+e.y-h//2
        self.root.geometry(f"+{x}+{y}")
        if self.popen and self.panel:
            self.panel.geometry(f"+{max(0,x-PW+w)}+{max(0,y-PH-12)}")

    def _close(self):
        self.running=False
        self._hide_panel(); self.root.destroy()
        try: os.remove(LOCK_FILE)
        except: pass

if __name__=="__main__": App()
