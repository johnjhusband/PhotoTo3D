#!/usr/bin/env python3
"""make_3mf_viewer.py — generate a self-contained HTML viewer for a color 3MF (or STL/GLB-as-3mf).
Embeds the 3MF as base64 and renders it with three.js's native ThreeMFLoader (colors included), so a
double-click opens an orbitable, zoomable view of the ACTUAL print file in any browser.
Usage: make_3mf_viewer.py <file.3mf> <out.html> [title]
"""
import base64, os, sys
TPL = '''<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>__TITLE__</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{margin:0;background:#23262d;font-family:system-ui,sans-serif;color:#ddd;overflow:hidden}
#hud{position:fixed;top:10px;left:12px;z-index:10;font-size:13px;background:#0006;padding:8px 12px;border-radius:8px}#hud b{color:#fff}</style>
<script type="importmap">{ "imports": {
 "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
 "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/" }}</script></head><body>
<div id="hud"><b>__TITLE__</b> — drag to rotate, scroll to zoom</div>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { ThreeMFLoader } from 'three/addons/loaders/3MFLoader.js';
const B64="__B64__";
function buf(b){const s=atob(b),n=s.length,a=new Uint8Array(n);for(let i=0;i<n;i++)a[i]=s.charCodeAt(i);return a.buffer;}
const scene=new THREE.Scene();scene.background=new THREE.Color(0x23262d);
const camera=new THREE.PerspectiveCamera(45,innerWidth/innerHeight,0.01,5000);
const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setSize(innerWidth,innerHeight);
renderer.setPixelRatio(devicePixelRatio);document.body.appendChild(renderer.domElement);
scene.add(new THREE.AmbientLight(0xffffff,0.9));
let L=new THREE.DirectionalLight(0xffffff,0.9);L.position.set(1,1.5,1);scene.add(L);
let L2=new THREE.DirectionalLight(0xffffff,0.5);L2.position.set(-1,0.5,-1.5);scene.add(L2);
const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;
const pivot=new THREE.Group();scene.add(pivot);
try{const obj=new ThreeMFLoader().parse(buf(B64));obj.rotation.x=-Math.PI/2;pivot.add(obj);
 const box=new THREE.Box3().setFromObject(pivot),c=box.getCenter(new THREE.Vector3()),sz=box.getSize(new THREE.Vector3());
 pivot.position.sub(c);const r=Math.max(sz.x,sz.y,sz.z);camera.position.set(0,0,r*2.0);controls.target.set(0,0,0);controls.update();
}catch(e){document.getElementById('hud').innerHTML='3MF parse error: '+e;}
addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);});
(function a(){requestAnimationFrame(a);controls.update();renderer.render(scene,camera);})();
</script></body></html>'''
def main():
    if len(sys.argv)<3: sys.exit("usage: make_3mf_viewer.py <file.3mf> <out.html> [title]")
    src,out=sys.argv[1],sys.argv[2]; title=sys.argv[3] if len(sys.argv)>3 else os.path.basename(src)
    b64=base64.b64encode(open(src,"rb").read()).decode()
    open(out,"w").write(TPL.replace("__B64__",b64).replace("__TITLE__",title))
    print("wrote",out,round(os.path.getsize(out)/1e6,1),"MB")
if __name__=="__main__": main()
