"""Progress Float — OpenCode floating progress ball.
State machine: GREEN(active) → AMBER(thinking 8s) → GRAY(idle)"""

import tkinter as tk
import threading, json, time, math, sys, os, atexit, ctypes, subprocess
import urllib.request, urllib.error

PORT = 19822
API = f"http://127.0.0.1:{PORT}/state"
LOCK_FILE = os.path.join(os.environ.get("TEMP","."), "opencode-progress-float.pid")

# Singleton
def _singleton():
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE) as f:
                pid = int(f.read().strip())
            import ctypes
            h = ctypes.windll.kernel32.OpenProcess(0x0400, False, pid)
            if h: ctypes.windll.kernel32.CloseHandle(h); return True
        except: pass
    with open(LOCK_FILE,"w") as f: f.write(str(os.getpid()))
    atexit.register(lambda: os.path.exists(LOCK_FILE) and os.remove(LOCK_FILE))
    return False
if _singleton(): sys.exit(0)

def _is_opencode_running():
    """Check if OpenCode is alive via state file freshness. No external heartbeat needed."""
    # 1. Heartbeat file — authoritative when it exists
    hb = "C:/.opencode/cache/heartbeat"
    try:
        if os.path.exists(hb):
            return (time.time() - os.path.getmtime(hb)) < 15
    except:
        pass
    # 2. State file freshness — if plugin writes it, it stops when OpenCode dies
    sf = "C:/.opencode/cache/progress-state.json"
    try:
        if os.path.exists(sf):
            age = time.time() - os.path.getmtime(sf)
            return age < 60  # 60s stale = OpenCode dead
    except:
        pass
    # 3. Last resort: tasklist subprocess check
    try:
        r = subprocess.run(
            ['tasklist', '/fi', 'imagename eq OpenCode.exe', '/fo', 'csv', '/nh'],
            capture_output=True, text=True, timeout=3,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        return 'OpenCode.exe' in r.stdout or 'opencode.exe' in r.stdout.lower()
    except:
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

BR=28; CW,CH=120,120; PW,PH=320,400

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
        self.tc=0; self.active=False; self.thinking=False
        self.projects={}; self.sessions={}; self.tools=[]
        self.task_count=0; self._la=0; self.pulse=0.0
        self.panel=None; self.pc=None; self.popen=False; self.running=True

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
                    d=json.loads(r.read().decode())
                self.tc=d.get("toolCount",0)
                self.tools=d.get("activeTools",[])
                self.sessions=d.get("sessions",{})
                self.projects=d.get("projects",{})
                self.task_count=d.get("taskCount",0)
                svr_a=d.get("active",False) or self.tc>0
                if svr_a:
                    self.active=True; self.thinking=False; self._la=time.time()
                elif self.tc==0 and self._la>0:
                    e=time.time()-self._la
                    if e<8: self.thinking=True; self.active=False
                    else: self.thinking=False; self.active=False
            except Exception:
                pass
            time.sleep(0.5)

    # ── Draw ──
    def _draw(self):
        c=self.canvas; c.delete("all")
        cx,cy=CW//2,CH//2; r=BR

        # glow
        if self.active or self.thinking:
            glow_r,glow_g,glow_b=(0x34,0xd3,0x99) if self.active else (0xf5,0x9e,0x0b)
            for i in range(3):
                p=(self.pulse+i*0.33)%1.0; gr2=r+4+p*20
                alpha=int((1-p)*200+55)
                c.create_oval(cx-gr2,cy-gr2,cx+gr2,cy+gr2,outline=f"#{glow_r:02x}{glow_g:02x}{min(255,glow_b+alpha):02x}",width=3,tags="g")

        # shadow
        c.create_oval(cx-r-1,cy-r+2,cx+r-1,cy+r+2,fill="#1a1a2e",outline="",stipple="gray25")

        # body
        bc=T.GREEN if self.active else (T.AMBER if self.thinking else T.GRAY)
        hl=self._lerp(bc,"#ffffff",0.12)
        c.create_oval(cx-r,cy-r,cx+r,cy+r,fill=bc,outline=hl,width=2)

        # inner highlight
        c.create_oval(int(cx-r*0.6),int(cy-r*0.6),int(cx+r*0.1),int(cy+r*0.1),fill="#4a4a7a",outline="",stipple="gray50")

        # center icon
        if self.active:
            for i in range(4):
                a=(self.pulse*3+i*1.57)%6.283
                dx=math.cos(a)*r*.35; dy=math.sin(a)*r*.35; sz=3
                c.create_oval(cx+dx-sz,cy+dy-sz,cx+dx+sz,cy+dy+sz,fill="#e0e0ff",outline="")
        elif self.thinking:
            ps=(math.sin(self.pulse*2)+1)/2; sz=4+ps*3
            c.create_oval(cx-sz,cy-sz,cx+sz,cy+sz,fill=T.AMBER2,outline="")
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
        self.pulse+=0.05
        self._draw()
        if self.running: self.root.after(33,self._anim)

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
        self.panel.geometry(f"{PW}x{PH}+{max(0,bx-PW+CW)}+{max(0,by-PH-12)}")
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
        hy=pad+16
        if self.active: dot,dc,title="\u25cf",T.GREEN,"Active"
        elif self.thinking: dot,dc,title="\u25cf",T.AMBER,"Thinking"
        else: dot,dc,title="\u25cb",T.MUTED,"Idle"
        c.create_text(pad+22,hy,text=dot,fill=dc,font=("Segoe UI",12),anchor="w")
        nproj=len(self.projects or {})
        if nproj>1: title+=f" \u2014 {nproj} projects"
        c.create_text(pad+44,hy,text=title,fill=T.TEXT,font=("Segoe UI",13,"bold"),anchor="w")
        c.create_text(w-pad-16,hy,text=f"{self.tc} active" if self.active else str(self.task_count),fill=T.MUTED,font=("Segoe UI",10),anchor="e")
        dy=hy+16; c.create_line(pad+16,dy,w-pad-16,dy,fill=T.BORDER,width=1)

        ly=dy+12; projs=self.projects or {}
        tools=self.tools or []

        # Build groups
        groups=[]
        if len(projs)>1:
            for pn in sorted(projs):
                p=projs[pn]
                groups.append(("project",pn,p.get("active",False),p.get("toolCount",0),p.get("taskCount",0),p.get("activeTools",[]),p.get("sessions",{})))
        elif len(projs)==1:
            pn,p=next(iter(projs.items()))
            ss=p.get("sessions",{}) or self.sessions
            pt=p.get("activeTools",[]) or tools
            if ss:
                for sid,si in sorted(ss.items(),key=lambda kv:kv[1].get("runningCount",0),reverse=True):
                    a=si.get("agent","?"); st=[t for t in pt if t.get("sessionID")==sid]
                    groups.append(("agent",a,si.get("active",False),si.get("runningCount",0),si.get("taskCount",0),st,{}))
            elif pt:
                groups=self._fallback(pt)
        elif self.sessions:
            for sid,si in sorted(self.sessions.items(),key=lambda kv:kv[1].get("runningCount",0),reverse=True):
                a=si.get("agent","?"); st=[t for t in tools if t.get("sessionID")==sid]
                groups.append(("agent",a,si.get("active",False),si.get("runningCount",0),si.get("taskCount",0),st,{}))
        else:
            groups=self._fallback(tools)

        if not groups:
            c.create_text(w//2,ly+60,text="Waiting for tasks...",fill=T.MUTED,font=("Segoe UI",11))
        else:
            ch=84
            for kind,label,is_a,run,total,tasks,gt in groups:
                if ly+ch>h-pad-40: break
                lc=CAT_COLORS.get(label,T.ACCENT2 if kind=="project" else "#7c3aed")
                self._rrect(c,pad+6,ly,w-pad-6,ly+ch-4,10,fill="#1a1a30",outline="#2a2a55",width=1)
                bw=max(60,len(label)*9+20)
                self._rrect(c,pad+20,ly+6,pad+20+bw,ly+24,6,fill=lc+"44",outline=lc+"88",width=1)
                c.create_text(pad+20+bw//2,ly+15,text=label,fill=lc,font=("Segoe UI",10,"bold"))
                if kind=="project":
                    c.create_text(pad+20+bw+8,ly+15,text="project",fill=T.MUTED,font=("Segoe UI",8),anchor="w")
                dot="\u25cf" if (is_a or run>0) else "\u25cb"
                dc2=T.GREEN if (is_a or run>0) else T.MUTED
                c.create_text(pad+28,ly+38,text=dot,fill=dc2,font=("Segoe UI",9),anchor="w")
                c.create_text(pad+48,ly+38,text=f"{run}/{total} tools",fill=T.MUTED,font=("Segoe UI",9),anchor="w")
                c.create_text(w-pad-22,ly+38,text=f"{tasks} tasks",fill=T.MUTED,font=("Segoe UI",9),anchor="e")
                # dot bar
                dx=pad+24; max_d=(w-pad*2-50)//11; sh=0
                for t in gt[-max_d:]:
                    if sh>=max_d: c.create_text(dx+4,ly+60,text=f"+{len(gt)-sh}",fill=T.MUTED,font=("Segoe UI",8)); break
                    st=t.get("status",""); dc3=T.GREEN if st=="running" else T.DONE_CLR
                    tc2=CAT_COLORS.get(t.get("tool",""),T.MUTED)
                    c.create_oval(dx,ly+56,dx+8,ly+64,fill=tc2,outline=dc3,width=1)
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
            g.append(("agent",a,rn>0,rn,len(at),self.task_count,at))
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
        menu.add_command(label="Exit",command=self._close)
        menu.post(event.x_root,event.y_root)

    def _drag(self,e):
        x=self.root.winfo_x()+e.x-CW//2
        y=self.root.winfo_y()+e.y-CH//2
        self.root.geometry(f"+{x}+{y}")
        if self.popen and self.panel:
            self.panel.geometry(f"+{max(0,x-PW+CW)}+{max(0,y-PH-12)}")

    def _close(self):
        self.running=False
        self._hide_panel(); self.root.destroy()
        try: os.remove(LOCK_FILE)
        except: pass

if __name__=="__main__": App()
