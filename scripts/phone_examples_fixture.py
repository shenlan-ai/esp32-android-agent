"""Opt-in offline phone examples; no model, ADB, or board access.

Forward the chosen port with authorized ADB reverse and open it on the phone.
Only actual pointer events draw strokes. There is no scripted task completion.
"""
from __future__ import annotations

import argparse

from phone_input_fixture import InputHandler, InputServer

STYLE = '''<style>
*{box-sizing:border-box}body{margin:0;background:#f1f3f5;color:#172636;font:18px sans-serif}
header{padding:18px;background:#172636;color:white}h1{font-size:22px;margin:0 0 8px}
header a{color:white}main{padding:18px}p{line-height:1.5}
.entry{display:block;margin:24px 0;padding:30px;border:2px solid #172636;border-radius:10px;
background:white;color:#172636;text-decoration:none;font-size:24px}
textarea{width:100%;height:55vh;font:26px sans-serif;padding:20px;border:2px solid #172636;
border-radius:8px;background:white}canvas{display:block;width:100%;height:62vh;
border:2px solid #172636;background:white;touch-action:none}
#status{font-size:14px}button{padding:12px;font:18px sans-serif}
</style>'''
HEAD = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Local phone examples</title>'''+STYLE
HEADER = '''<header><h1>LOCAL PHONE EXAMPLES</h1><a href="/">Home</a></header>'''
MENU = HEAD+HEADER+'''<main><p>Offline test content. Real phone input only.</p>
<a class="entry" href="/whiteboard">Whiteboard — blank canvas</a>
<a class="entry" href="/notes">Notes — new blank note</a>
<p>No account. No external resources. No automatic task completion.</p></main></html>'''
REPORT = r'''
const queue=[];let busy=false;
function record(type,detail={}){
 queue.push({type,time_ms:performance.now(),...detail});if(queue.length>80)queue.shift();
}
async function send(){
 if(busy)return;busy=true;const events=queue.splice(0,80);
 try{await fetch('/events',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({events,geometry:geometry(),value:document.querySelector('textarea')?.value??'',scroll_top:0})});}
 catch{queue.unshift(...events);if(queue.length>80)queue.splice(80);}
 finally{busy=false;}
}
record('loaded');setInterval(send,200);
'''
NOTES = HEAD+HEADER+'''<main><h2>New blank note</h2>
<textarea aria-label="Note body" placeholder="Write here" autocomplete="off"
 autocorrect="off" autocapitalize="off" spellcheck="false"></textarea>
<p>Local test note. No send or submit action.</p></main><script>'''+REPORT+r'''
const note=document.querySelector('textarea');
function geometry(){const r=note.getBoundingClientRect();return {page:'notes',width:innerWidth,
 height:innerHeight,dpr:devicePixelRatio,field:{x:r.x,y:r.y,width:r.width,height:r.height}};}
note.addEventListener('input',()=>record('input',{value:note.value}));
for(const type of ['keydown','keyup'])note.addEventListener(type,e=>record(type,{key:e.key}));
send();</script></html>'''
BOARD = HEAD+HEADER+'''<main><h2>Whiteboard</h2><canvas aria-label="Blank whiteboard"></canvas>
<p id="status">Blank canvas — draw with pointer input.</p>
<button id="clear">Clear canvas</button></main><script>'''+REPORT+r'''
const canvas=document.querySelector('canvas'),ctx=canvas.getContext('2d');
let active=null;const strokes=[];
function size(){const r=canvas.getBoundingClientRect();canvas.width=Math.round(r.width*devicePixelRatio);
 canvas.height=Math.round(r.height*devicePixelRatio);ctx.scale(devicePixelRatio,devicePixelRatio);
 ctx.lineWidth=5;ctx.lineCap='round';ctx.lineJoin='round';ctx.strokeStyle='#172636';}
size();
function point(e){const r=canvas.getBoundingClientRect();return {x:e.clientX-r.x,y:e.clientY-r.y};}
function status(){document.getElementById('status').textContent='Actual pointer strokes: '+strokes.length;}
function geometry(){const r=canvas.getBoundingClientRect();return {page:'whiteboard',width:innerWidth,
 height:innerHeight,dpr:devicePixelRatio,canvas:{x:r.x,y:r.y,width:r.width,height:r.height},
 stroke_count:strokes.length,stroke_points:strokes.map(s=>s.length)};}
canvas.addEventListener('pointerdown',e=>{
 if(e.button!==0||active!==null)return;e.preventDefault();canvas.setPointerCapture(e.pointerId);
 active=[point(e)];strokes.push(active);if(strokes.length>200)strokes.shift();
 const p=active[0];ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(p.x+.1,p.y);ctx.stroke();
 record('pointerdown',{...p,buttons:e.buttons,pointer_type:e.pointerType});status();
});
canvas.addEventListener('pointermove',e=>{
 if(!active||!(e.buttons&1))return;e.preventDefault();const p=point(e),last=active.at(-1);
 ctx.beginPath();ctx.moveTo(last.x,last.y);ctx.lineTo(p.x,p.y);ctx.stroke();
 active.push(p);if(active.length>1000)active.splice(0,1);
 record('pointermove',{...p,buttons:e.buttons,pointer_type:e.pointerType});
});
for(const type of ['pointerup','pointercancel','lostpointercapture'])canvas.addEventListener(type,e=>{
 if(!active)return;record(type,{...point(e),buttons:e.buttons,pointer_type:e.pointerType});active=null;status();
});
canvas.addEventListener('contextmenu',e=>e.preventDefault());
document.getElementById('clear').addEventListener('click',()=>{
 ctx.clearRect(0,0,canvas.width,canvas.height);strokes.length=0;active=null;record('clear');status();
});
send();</script></html>'''


class ExamplesHandler(InputHandler):
    def do_GET(self):
        page = {"/": MENU, "/notes": NOTES, "/whiteboard": BOARD}.get(self.path)
        if page is not None:
            self.respond(200, page.encode(), "text/html; charset=utf-8")
        else:
            super().do_GET()


class ExamplesServer(InputServer):
    def __init__(self, port):
        super().__init__(port)
        # Reuse the bounded, size-checked event collector; no device connections.
        self.RequestHandlerClass = ExamplesHandler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8895)
    args = parser.parse_args()
    with ExamplesServer(args.port) as server:
        print(f"Offline phone examples: http://127.0.0.1:{server.server_port}/", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
