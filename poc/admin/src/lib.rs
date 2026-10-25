use worker::*;
use serde::{Deserialize,Serialize};
const SEED:&str=include_str!("../../content.json");
#[derive(Clone,Serialize,Deserialize)]
struct Content{articles:Vec<Article>,map:MapData,counter_label:String}
#[derive(Clone,Serialize,Deserialize)]
struct Article{slug:String,title:String,body:String,revision:u64}
#[derive(Clone,Serialize,Deserialize)]
struct MapData{title:String,points:Vec<Point>}
#[derive(Clone,Serialize,Deserialize)]
struct Point{id:String,label:String,x:f64,y:f64}
fn esc(s:&str)->String{s.replace('&',"&amp;").replace('<',"&lt;").replace('>',"&gt;").replace('"',"&quot;").replace('\'',"&#39;")}
async fn load(bucket:&Bucket,key:&str)->Result<Content>{
 let Some(object)=bucket.get(key).execute().await? else{return Ok(serde_json::from_str(SEED)?)};
 let Some(body)=object.body() else{return Err(Error::RustError("Empty R2 object".into()))};
 Ok(serde_json::from_str(&body.text().await?)?)
}
async fn save(bucket:&Bucket,key:&str,c:&Content)->Result<()>{
 bucket.put(key,serde_json::to_string_pretty(c)?).execute().await?;Ok(())
}
fn field(f:&FormData,key:&str)->String{match f.get(key){Some(FormEntry::Field(v))=>v,_=>String::new()}}
fn html(s:String)->Result<Response>{
 Response::from_html(format!(r#"<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SAIGA POC admin</title><style>body{{max-width:900px;margin:2rem auto;padding:0 1rem;font:16px system-ui}}section{{padding:1rem;border:1px solid #bbb;margin:1rem 0}}input,textarea{{display:block;width:100%;padding:.5rem;margin:.5rem 0 1rem}}button{{padding:.7rem}}</style></head><body><h1>SAIGA admin POC</h1>{s}</body></html>"#))
}
#[event(fetch)]
pub async fn main(mut req:Request,env:Env,_ctx:worker::Context)->Result<Response>{
 let path=req.path();let bucket=env.bucket("CONTENT")?;
 let host=req.url()?.host_str().unwrap_or_default().to_owned();
 if req.method()==Method::Post && req.headers().get("Origin")?.as_deref()!=Some(format!("https://{host}").as_str()){
  return Response::error("Invalid origin",403)
 }
 if path=="/api/published"{
  let token=env.secret("PUBLISH_TOKEN")?.to_string();
  if req.headers().get("Authorization")?.as_deref()!=Some(format!("Bearer {token}").as_str()){return Response::error("Forbidden",403)}
  let mut response=Response::from_json(&load(&bucket,"published.json").await?)?;
  response.headers_mut().set("Cache-Control","no-store")?;return Ok(response)
 }
 // Mandatory Cloudflare Access application policy on the route.
 if req.headers().get("Cf-Access-Jwt-Assertion")?.is_none(){return Response::error("Cloudflare Access required",403)}
 let mut c=load(&bucket,"draft.json").await?;
 if req.method()==Method::Post{
  let f=req.form_data().await?;
  match path.as_str(){
   "/save/article"=>{
    let slug=field(&f,"slug");
    let Some(a)=c.articles.iter_mut().find(|a|a.slug==slug) else{return Response::error("Not found",404)};
    a.title=field(&f,"title");a.body=field(&f,"body");a.revision+=1;
    save(&bucket,"draft.json",&c).await?;
    return Response::redirect(req.url()?.join("/")?)
   }
   "/save/map"=>{
    c.map.title=field(&f,"title");
    for p in &mut c.map.points {
     let label=field(&f,&format!("label_{}",p.id));if !label.is_empty(){p.label=label}
     if let Ok(x)=field(&f,&format!("x_{}",p.id)).parse::<f64>(){if x.is_finite()&&(0.0..=440.0).contains(&x){p.x=x}}
     if let Ok(y)=field(&f,&format!("y_{}",p.id)).parse::<f64>(){if y.is_finite()&&(0.0..=300.0).contains(&y){p.y=y}}
    }
    save(&bucket,"draft.json",&c).await?;
    return Response::redirect(req.url()?.join("/")?)
   }
   "/publish"=>{
    save(&bucket,"published.json",&c).await?;
    return html("<p>Publication requested. The self-hosted publisher will deploy the new static snapshot on its next scheduled run. The public site is unchanged until deployment succeeds.</p><a href=\"/\">Back</a>".into())
   }
   _=>return Response::error("Unknown operation",404)
  }
 }
 if req.method()!=Method::Get{return Response::error("Method not allowed",405)}
 let mut body=String::from("<p>Changes save to a private draft. Publish updates the static site.</p>");
 for a in &c.articles {
  body+=&format!(r#"<section><h2>{}</h2><form method="post" action="/save/article"><input type="hidden" name="slug" value="{}"><label>Title<input name="title" value="{}"></label><label>Article body<textarea name="body" rows="8">{}</textarea></label><button>Save draft article</button></form></section>"#,esc(&a.slug),esc(&a.slug),esc(&a.title),esc(&a.body));
 }
 body+=&format!(r#"<section><h2>Editable map coordinates</h2><form method="post" action="/save/map"><label>Title<input name="title" value="{}"></label>"#,esc(&c.map.title));
 for p in &c.map.points{
  body+=&format!(r#"<h3>{}</h3><label>Label<input name="label_{}" value="{}"></label><label>X<input type="number" name="x_{}" value="{}"></label><label>Y<input type="number" name="y_{}" value="{}"></label>"#,esc(&p.id),esc(&p.id),esc(&p.label),esc(&p.id),p.x,esc(&p.id),p.y);
 }
 body+="<button>Save draft map</button></form></section><form method=\"post\" action=\"/publish\"><button>Publish static site</button></form>";
 html(body)
}
