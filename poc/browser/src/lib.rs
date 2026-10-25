use wasm_bindgen::prelude::*;
use wasm_bindgen::JsCast;
use wasm_bindgen_futures::{spawn_local,JsFuture};
use web_sys::{window,Event,MouseEvent,Element,DomParser,SupportedType};
use std::cell::RefCell;
thread_local! {static SAMPLES: RefCell<Vec<serde_json::Value>>=const {RefCell::new(Vec::new())};}
fn doc()->web_sys::Document{window().unwrap().document().unwrap()}
fn now()->f64{window().unwrap().performance().unwrap().now()}
fn log(v:serde_json::Value){SAMPLES.with(|s|s.borrow_mut().push(v));}
fn href()->String{let l=window().unwrap().location();format!("{}{}",l.pathname().unwrap_or_default(),l.search().unwrap_or_default())}
fn html_escape(s:&str)->String{s.replace('&',"&amp;").replace('<',"&lt;").replace('>',"&gt;")}
fn show_metrics(){
 let d=doc();
 let text=SAMPLES.with(|s|serde_json::to_string_pretty(&*s.borrow()).unwrap_or_default());
 if let Some(el)=d.get_element_by_id("perf-output"){el.set_text_content(Some(&text));}
 if let Some(el)=d.get_element_by_id("perf-dialog"){if let Ok(dlg)=el.dyn_into::<web_sys::HtmlDialogElement>(){let _=dlg.show_modal();}}
}
fn island_ready(route:&str, navigation_started:f64,swap_time:f64){
 let d=doc();
 let mut count=0;
 if let Ok(nodes)=d.query_selector_all("[data-island]"){
  for i in 0..nodes.length(){if let Some(el)=nodes.item(i){el.set_attribute("data-ready","true").ok();count+=1;}}
 }
 log(serde_json::json!({"type":"navigation","route":route,"fetch_and_swap_ms":swap_time-navigation_started,"island_ready_ms":now()-navigation_started,"islands":count,"at_ms":now()}));
}
async fn navigate(url:String,push:bool){
 let start=now();
 let w=window().unwrap();
 let fetch=JsFuture::from(w.fetch_with_str(&url)).await;
 let Ok(resp)=fetch else {let _=w.location().set_href(&url);return};
 let Ok(response)=resp.dyn_into::<web_sys::Response>() else{return};
 if !response.ok(){let _=w.location().set_href(&url);return}
 let Ok(text)=JsFuture::from(response.text().unwrap()).await else{return};
 let Some(body)=text.as_string() else{return};
 let Ok(parsed)=DomParser::new().unwrap().parse_from_string(&body,SupportedType::TextHtml) else{return};
 let Some(next)=parsed.get_element_by_id("main") else{let _=w.location().set_href(&url);return};
 let Some(old)=doc().get_element_by_id("main") else{return};
 let _=old.replace_with_with_node_1(&next);
 if let Ok(title)=parsed.title().parse::<String>(){doc().set_title(&title);}
 if push{let _=w.history().unwrap().push_state_with_url(&JsValue::NULL,"",Some(&url));}
 let links=doc().query_selector_all("nav a").unwrap();
 for i in 0..links.length(){if let Some(el)=links.item(i){let path=el.get_attribute("href").unwrap_or_default();let state=if path==url{"page"}else{"false"};let _=el.set_attribute("aria-current",state);}}
 let swapped=now();
 if let Some(m)=doc().get_element_by_id("main"){let _=m.dyn_ref::<web_sys::HtmlElement>().map(|h|h.focus());}
 island_ready(&url,start,swapped);
 // Document navigation timing covers click → fetched HTML → DOM swap → islands interactive.
}
#[wasm_bindgen]
pub fn start(){
 let load=now();log(serde_json::json!({"type":"initial-wasm-start","route":href(),"ms_since_time_origin":load}));
 island_ready(&href(),load,now());
 let cb=Closure::<dyn FnMut(Event)>::new(move |ev:Event|{
  let target=ev.target().and_then(|x|x.dyn_into::<Element>().ok());
  let Some(t)=target else{return};
  if t.closest("#metrics-toggle").ok().flatten().is_some(){show_metrics();return}
  if t.closest("#metrics-close").ok().flatten().is_some(){if let Some(el)=doc().get_element_by_id("perf-dialog"){let _=el.dyn_into::<web_sys::HtmlDialogElement>().unwrap().close();}return}
  if t.closest("#metrics-export").ok().flatten().is_some(){
   // Diagnostics remain in browser memory; copying them is possible in devtools.
   show_metrics();return
  }
  if t.closest("[data-counter-plus]").ok().flatten().is_some(){
   if let Ok(Some(el))=doc().query_selector("[data-counter-value]"){let n=el.text_content().unwrap_or_default().parse::<u32>().unwrap_or(0);el.set_text_content(Some(&(n+1).to_string()));}
   return
  }
  if let Ok(Some(point))=t.closest("[data-point]"){
   if let Ok(Some(out))=doc().query_selector("[data-map-selection]"){out.set_text_content(Some(&format!("Selected: {}",point.get_attribute("data-point").unwrap_or_default())));}
   return
  }
  let Some(mouse)=ev.dyn_ref::<MouseEvent>() else{return};
  if mouse.button()!=0||mouse.ctrl_key()||mouse.meta_key()||mouse.shift_key()||mouse.alt_key(){return}
  let Ok(Some(link))=t.closest("a[href]") else{return};
  if link.has_attribute("download")||link.get_attribute("target").is_some(){return}
  let Some(raw)=link.get_attribute("href") else{return};
  if !raw.starts_with('/')||raw.starts_with("//")||raw.starts_with("/admin"){return}
  ev.prevent_default();
  spawn_local(navigate(raw,true));
 });
 doc().add_event_listener_with_callback("click",cb.as_ref().unchecked_ref()).unwrap();cb.forget();
 let back=Closure::<dyn FnMut(Event)>::new(move |_ev:Event|{spawn_local(navigate(href(),false));});
 window().unwrap().add_event_listener_with_callback("popstate",back.as_ref().unchecked_ref()).unwrap();back.forget();
 let _=html_escape("");
}
