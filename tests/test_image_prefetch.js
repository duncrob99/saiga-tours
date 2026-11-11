const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync('main/static/js/main.js', 'utf8');
const start = source.indexOf('let saigaImageObserver;');
const end = source.indexOf('\nminimise_images();', start);
assert(start >= 0 && end > start);
let calls = [], finish = {};
const images = [{id:'visible', top:0}, {id:'nearby', top:1100}, {id:'far', top:2100}].map(item => ({...item,isConnected:true,getBoundingClientRect(){return {width:100,height:100,top:this.top,bottom:this.top+100,left:0,right:100}}}));
const context = {document:{querySelectorAll:()=>images},innerHeight:800,innerWidth:1000,
 IntersectionObserver:class { observe(){} disconnect(){} },
 requestAnimationFrame:fn=>fn(), setTimeout:fn=>fn(),
 minimise_image:img=>{calls.push(img.id);return new Promise(resolve=>finish[img.id]=resolve)},
 Promise, Set, WeakSet};
vm.createContext(context); vm.runInContext(source.slice(start,end)+'\nminimise_images();',context);
assert.deepStrictEqual(calls,['visible']);
finish.visible();
setImmediate(()=>{assert.deepStrictEqual(calls,['visible','nearby','far']);console.log('visible images load before background images');});
