use leptos::prelude::*;
use pulldown_cmark::{html, Options, Parser};
use serde::Deserialize;
use std::{fs, path::Path};

#[derive(Deserialize)]
struct Article { slug:String, title:String, body:String, revision:u64 }
#[derive(Deserialize)]
struct Content { articles:Vec<Article>, map:MapData, counter_label:String }
#[derive(Deserialize)]
struct MapData { title:String, points:Vec<Point> }
#[derive(Deserialize)]
struct Point { id:String, label:String, x:f64, y:f64 }

fn markdown(md:&str)->String {
 let mut out=String::new();
 html::push_html(&mut out,Parser::new_ext(md,Options::ENABLE_TABLES));
 out
}
fn page(title:&str, current:&str, body:String)->String {
 let links=[("/", "Home"),("/articles/","Articles"),("/destinations/","Destinations"),("/about/","About")];
 let nav=links.into_iter().map(|(href,label)| view!{
   <a href=href aria-current=if current==href {"page"} else {"false"}>{label}</a>
 }.to_html()).collect::<String>();
 let shell=view!{
  <header class="topbar"><a class="brand" href="/">"SAIGA Tours / architecture POC"</a></header>
 }.to_html();
 let footer=view!{<footer><button id="metrics-toggle" type="button">"Performance diagnostics"</button><small>"Static HTML · Rust WebAssembly interactions"</small></footer>}.to_html();
 format!(r#"<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} · SAIGA POC</title><link rel="stylesheet" href="/styles.css"><script type="module" src="/bootstrap.js"></script></head><body>{shell}<nav class="mainnav" aria-label="Main">{nav}</nav><main id="main" tabindex="-1" data-route="{current}">{body}</main>{footer}<dialog id="perf-dialog"><h2>Navigation timings (ms)</h2><pre id="perf-output"></pre><button id="metrics-close" type="button">Close</button><button id="metrics-export" type="button">Download JSON</button></dialog></body></html>"#)
}
fn write(out:&Path, route:&str, markup:String) {
 let path=if route=="/" {out.join("index.html")}else{out.join(route.trim_start_matches('/')).join("index.html")};
 fs::create_dir_all(path.parent().unwrap()).unwrap();
 fs::write(path,markup).unwrap();
}
fn main(){
 let input=std::env::args().nth(1).unwrap_or_else(||"content.json".into());
 let output=std::env::args().nth(2).unwrap_or_else(||"dist".into());
 let c:Content=serde_json::from_slice(&fs::read(input).expect("content input")).expect("valid content");
 let out=Path::new(&output);fs::create_dir_all(out).unwrap();
 let home=view!{<section class="hero"><h1>"Discover the world differently"</h1><p>"Static HTML generated using Leptos. Client navigation uses Rust/WASM."</p><a class="action" href="/articles/">"Read our articles"</a></section>
 <section data-island="counter" data-label=c.counter_label.clone()><h2>"Interactive island: counter"</h2><p>"Clicks: "<output data-counter-value>"0"</output></p><button data-counter-plus>"Explore"</button></section>}.to_html();
 write(out,"/",page("Home","/",home));
 let mut listing=String::from("<h1>Articles</h1><ul class=\"articles\">");
 for a in &c.articles {
  let route=format!("/article/{}/",a.slug);
  listing+=&format!("<li><a href=\"{route}\">{}</a></li>",escape(&a.title));
  let body=format!("<article><h1>{}</h1><div class=\"article-body\">{}</div><small>Revision {}</small></article>",escape(&a.title),markdown(&a.body),a.revision);
  write(out,&route,page(&a.title,&route,body));
 }
 listing+="</ul>";
 write(out,"/articles/",page("Articles","/articles/",listing));
 let points=c.map.points.iter().map(|p|format!(r#"<g data-point="{}" tabindex="0"><circle cx="{}" cy="{}" r="11"/><text x="{}" y="{}">{}</text></g>"#,escape(&p.id),p.x,p.y,p.x+15.,p.y+5.,escape(&p.label))).collect::<String>();
 let map=format!(r#"<h1>Destinations</h1><section data-island="map"><h2>{}</h2><p>Select a destination marker to view its label.</p><svg role="img" aria-label="Sample editable SVG map" viewBox="0 0 440 300"><path d="M45 55 L340 33 407 180 265 256 68 230 Z" fill="#e7e5dc" stroke="#8c897a"/>{points}</svg><output data-map-selection>Choose a marker</output></section>"#,escape(&c.map.title));
 write(out,"/destinations/",page("Destinations","/destinations/",map));
 write(out,"/about/",page("About","/about/",r#"<h1>About this prototype</h1><p>Direct links and reloads resolve to pre-rendered HTML. Navigations use fetch and swap the main document region.</p><a href="/destinations/">Try the map</a>"#.into()));
 // Bundled public assets are immutable for each Cloudflare deployment.
 fs::copy("generator/public/styles.css",out.join("styles.css")).unwrap();
 fs::copy("generator/public/bootstrap.js",out.join("bootstrap.js")).unwrap();
}
fn escape(s:&str)->String{s.replace('&',"&amp;").replace('<',"&lt;").replace('>',"&gt;").replace('"',"&quot;").replace('\'',"&#39;")}
