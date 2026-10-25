use std::{env,io::{Read,Write},net::TcpListener,time::{SystemTime,UNIX_EPOCH}};
fn main()->std::io::Result<()>{
 let port=env::var("SAIGA_POC_DEV_PORT").unwrap_or_else(|_|"4194".into());
 let listener=TcpListener::bind(format!("127.0.0.1:{port}"))?;
 for stream in listener.incoming(){
  let Ok(mut stream)=stream else{continue};
  let mut buf=[0u8;4096];let n=stream.read(&mut buf).unwrap_or(0);
  let req=String::from_utf8_lossy(&buf[..n]);
  let path=req.split_whitespace().nth(1).unwrap_or("/");
  let body=match path{
   "/health"=>serde_json::json!({"status":"ok","service":"saiga-poc-dev-status"}).to_string(),
   "/diagnostics/build"=>serde_json::json!({"service":"saiga-poc-dev","build_validation":"executed by Personal Ops buildCommands before release promotion","persistent_cache":"~/.cache/saiga-poc/cargo-target","at_unix":SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_secs()}).to_string(),
   _=>serde_json::json!({"error":"not_found"}).to_string()
  };
  let status=if path=="/health"||path=="/diagnostics/build"{"200 OK"}else{"404 Not Found"};
  let response=format!("HTTP/1.1 {status}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",body.len());
  let _=stream.write_all(response.as_bytes());
 }
 Ok(())
}
