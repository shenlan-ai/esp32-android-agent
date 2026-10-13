"""Opt-in localhost input surface; never opens ADB, serial, or model connections.

Run this script, forward its port with authorized ADB reverse, and open it in
the phone browser. Browser observations supplement screenshots and human checks.
"""
from __future__ import annotations

import argparse
import json
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock

PAGE = r'''<!doctype html>
<html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Local HID input test</title>
<style>
body{margin:0;font:16px sans-serif;background:#eef2f5;color:#172636}
main{position:fixed;inset:0}h1{font-size:18px;margin:12px;text-align:center}
button,input,section{position:absolute;box-sizing:border-box;border:2px solid #172636;border-radius:6px}
button{padding:10px;color:white;background:#146fba;touch-action:none}
#target-top-left{left:5%;top:12%;width:32%;height:9%}
#target-center{left:38%;top:43%;width:30%;height:10%}
#target-low-right{right:4%;top:60%;width:32%;height:9%}
#text-field{left:8%;top:27%;width:84%;height:9%;font-size:20px;background:white;padding:8px}
#hold-zone{left:4%;top:43%;width:30%;height:10%;background:#845c13}
#drag-zone{left:4%;top:59%;width:56%;height:12%;background:#e0dff4;touch-action:none;padding:8px;user-select:none}
#drag-dot{display:block;width:24px;height:24px;border-radius:50%;background:#784dc0;position:absolute;left:10px;top:35px}
#scroll-zone{left:4%;top:75%;width:92%;height:18%;overflow:auto;background:white}
#scroll-zone div{padding:12px;border-bottom:1px solid #ccd3dc}
#status{position:absolute;left:5%;bottom:1%;margin:0;font-size:12px}
</style>
<main><h1>LOCAL TEST — NO SUBMISSION</h1>
<button id="target-top-left">Top left</button>
<input id="text-field" aria-label="Local ASCII test" placeholder="Empty local test field"
 autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false">
<button id="hold-zone">Hold here</button><button id="target-center">Center</button>
<section id="drag-zone">Drag the purple dot<span id="drag-dot"></span></section>
<button id="target-low-right">Low right</button><section id="scroll-zone"></section>
<p id="status">No input yet. This page does not control the phone.</p></main>
<script>
const queue = [], ids = ['target-top-left','target-center','target-low-right','hold-zone','drag-zone','text-field','scroll-zone'];
const scroll = document.getElementById('scroll-zone');
for(let i=0;i<30;i++){const row=document.createElement('div');row.textContent='Scroll row '+i;scroll.append(row);}
let lastMove=0, downAt=null, drag=false, busy=false;
function record(type, detail={}) {
  queue.push({type, time_ms:performance.now(), ...detail});
  if(queue.length>80) queue.shift();
  document.getElementById('status').textContent=type+' '+(detail.target||'')+' buttons='+(detail.buttons??0);
}
function geometry(){
 const targets={};for(const id of ids){const r=document.getElementById(id).getBoundingClientRect();targets[id]={x:r.x,y:r.y,width:r.width,height:r.height};}
 return {width:innerWidth,height:innerHeight,dpr:devicePixelRatio,screen_width:screen.width,screen_height:screen.height,targets};
}
document.addEventListener('pointerdown',e=>{
 downAt=performance.now();drag=e.target.closest('#drag-zone')!==null;
 if(drag)document.getElementById('drag-zone').setPointerCapture(e.pointerId);
});
for(const type of ['pointerdown','pointerup','pointercancel','pointermove','click']){
 document.addEventListener(type,e=>{
  if(type==='pointermove'&&performance.now()-lastMove<35)return;
  if(type==='pointermove')lastMove=performance.now();
  record(type,{target:e.target.id,x:e.clientX,y:e.clientY,screen_x:e.screenX,screen_y:e.screenY,buttons:e.buttons,pointer_type:e.pointerType,
   held_ms:type==='pointerup'&&downAt!==null?performance.now()-downAt:null});
  if(drag&&type==='pointermove'){
   const area=document.getElementById('drag-zone').getBoundingClientRect();
   const dot=document.getElementById('drag-dot');dot.style.left=Math.max(0,Math.min(area.width-24,e.clientX-area.x-12))+'px';
   dot.style.top=Math.max(0,Math.min(area.height-24,e.clientY-area.y-12))+'px';
  }
  if(type==='pointerup'||type==='pointercancel'){drag=false;downAt=null;}
 });
}
document.addEventListener('contextmenu',e=>e.preventDefault());
for(const type of ['keydown','keyup'])document.addEventListener(type,e=>record(type,{key:e.key,target:e.target.id}));
document.getElementById('text-field').addEventListener('input',e=>record('input',{value:e.target.value}));
scroll.addEventListener('scroll',()=>record('scroll',{top:scroll.scrollTop}));
async function send(){
 if(busy)return;busy=true;
 const events=queue.splice(0,80);
 try{await fetch('/events',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({events,geometry:geometry(),value:document.getElementById('text-field').value,scroll_top:scroll.scrollTop})});}
 catch{queue.unshift(...events);if(queue.length>80)queue.splice(80);}
 finally{busy=false;}
}
record('loaded');setInterval(send,180);send();
</script></html>'''


class InputServer(ThreadingHTTPServer):
    def __init__(self, port: int):
        super().__init__(("127.0.0.1", port), InputHandler)
        self.events = deque(maxlen=1000)
        self.latest = {}
        self.state_lock = Lock()


class InputHandler(BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(5)
        super().setup()

    def log_message(self, *_args):
        pass

    def respond(self, status: int, data: bytes, kind="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/":
            self.respond(200, PAGE.encode(), "text/html; charset=utf-8")
        elif self.path == "/state":
            with self.server.state_lock:
                snapshot = {"latest": dict(self.server.latest),
                            "events": list(self.server.events)}
            self.respond(200, json.dumps(snapshot).encode())
        else:
            self.respond(404, b'{}')

    def do_POST(self):
        if self.path != "/events":
            self.respond(404, b'{}')
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 32768:
                self.respond(413, b'{}')
                return
            payload = json.loads(self.rfile.read(size))
            events = payload.get("events") if isinstance(payload, dict) else None
            if (not isinstance(events, list) or len(events) > 80
                    or not all(isinstance(event, dict) for event in events)):
                raise ValueError
        except (ValueError, UnicodeDecodeError):
            self.respond(400, b'{}')
            return
        with self.server.state_lock:
            self.server.events.extend(events)
            self.server.latest = {key: payload.get(key) for key in ("geometry", "value", "scroll_top")}
        self.respond(200, b'{"ok":true}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8894)
    args = parser.parse_args()
    with InputServer(args.port) as server:
        print(f"Local test: http://127.0.0.1:{server.server_port}/", flush=True)
        print("Opt-in test surface; no ADB, board or model access", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
