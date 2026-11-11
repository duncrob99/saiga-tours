const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const handlers = new Map();
const stages = [7, 5, 2, 1, 6].map(priority => ({dataset:{priority},isConnected:true,attrs:new Set(),hasAttribute(name){return this.attrs.has(name)},setAttribute(name){this.attrs.add(name)},removeAttribute(name){this.attrs.delete(name)}}));
const launched = [];
const document = {
  currentScript:{src:'https://example.test/static/js/saiga-stages.js'},readyState:'interactive',head:{appendChild(){}},
  querySelectorAll(){return stages.filter(s=>s.isConnected&&!s.attrs.has('data-saiga-started'))},
  addEventListener(type,handler){handlers.set(type,handler)},
  dispatchEvent(event){handlers.get(event.type)?.(event)}
};
const processed=[];
const htmx={process(element){processed.push(element.dataset.priority)},trigger(element){assert(processed.includes(element.dataset.priority));launched.push(element.dataset.priority)}};
const context={document,window:{htmx},location:{href:'https://example.test/'},URL,Event:class Event {constructor(type){this.type=type}},htmx,setTimeout:callback=>callback(),minimise_images(){}};
vm.runInNewContext(fs.readFileSync('main/static/js/saiga-stages.js','utf8'),context);
assert.deepEqual(processed,[7,5,2,1,6],'process stage triggers before DOMContentLoaded');
assert.deepEqual(launched,[1]);
for(let i=0;i<stages.length;i++){
  const current=stages.find(s=>s.isConnected && s.dataset.priority==launched.at(-1));
  current.isConnected=false;
  handlers.get('htmx:afterSwap')({detail:{target:current}});
}
assert.deepEqual(launched,[1,2,5,6,7]);
const newStage={dataset:{priority:0},isConnected:true,attrs:new Set(),hasAttribute(name){return this.attrs.has(name)},setAttribute(name){this.attrs.add(name)},removeAttribute(name){this.attrs.delete(name)}};
stages.push(newStage);
handlers.get('htmx:afterSwap')({detail:{target:{id:'site-page'}}});
assert(processed.at(-1)===0,'process the destination page stage after navigation');
assert(launched.at(-1)===0,'start the destination page stage after navigation');
console.log('stages request one at a time in priority order');
