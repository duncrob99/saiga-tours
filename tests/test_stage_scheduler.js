const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const handlers = new Map();
const stages = [7, 5, 2, 1, 6].map(priority => ({dataset:{priority},isConnected:true,attrs:new Set(),hasAttribute(name){return this.attrs.has(name)},setAttribute(name){this.attrs.add(name)},removeAttribute(name){this.attrs.delete(name)}}));
const launched = [];
const document = {
  currentScript:{src:'https://example.test/static/js/saiga-stages.js'},readyState:'complete',head:{appendChild(){}},
  querySelectorAll(){return stages.filter(s=>s.isConnected&&!s.attrs.has('data-saiga-started'))},
  addEventListener(type,handler){handlers.set(type,handler)}
};
const htmx={trigger(element){launched.push(element.dataset.priority)}};
const context={document,window:{htmx},location:{href:'https://example.test/'},URL,htmx,minimise_images(){}};
vm.runInNewContext(fs.readFileSync('main/static/js/saiga-stages.js','utf8'),context);
assert.deepEqual(launched,[1]);
for(let i=0;i<stages.length;i++){
  const current=stages.find(s=>s.isConnected && s.dataset.priority==launched.at(-1));
  current.isConnected=false;
  handlers.get('htmx:afterSwap')({detail:{target:current}});
}
assert.deepEqual(launched,[1,2,5,6,7]);
console.log('stages request one at a time in priority order');
