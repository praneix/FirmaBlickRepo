"""Read-only FirmaBlick n8n diagnostic. Never logs raw workflow nodes, prompts, secrets or execution data."""
import os, json, urllib.request, urllib.error, datetime, pathlib, sys
ids={"FB00":"48njroUcejm6gTLV","FB01":"4n5ITvZUOahJo43n","FB02":"Dy6ImadwlwQevKRd","FB99":"L7DAAEFUWKA7NMmS"}
url=os.environ["N8N_BASE_URL"].rstrip("/")
if not url.startswith("https://") or "?" in url or "#" in url:raise ValueError("N8N_BASE_URL must be https origin")
url=url.removesuffix("/api/v1")
key=os.environ["N8N_API_KEY"]
def req(route):
    request=urllib.request.Request(url+"/api/v1"+route,headers={"X-N8N-API-KEY":key,"Accept":"application/json"},method="GET")
    try:
        with urllib.request.urlopen(request,timeout=30) as res:return json.load(res)
    except urllib.error.HTTPError as e:return {"api_http_error":e.code}
def classify_message(s):
    s=str(s).lower()
    if "received no input" in s or "must be called" in s:return "MISSING_SUBWORKFLOW_INPUT"
    if "incomplete" in s or "max_output_tokens" in s:return "MODEL_OUTPUT_INCOMPLETE"
    if "timed out" in s or "timeout" in s:return "TIMEOUT"
    if "invalid json" in s or "json parse" in s:return "INVALID_MODEL_JSON"
    if "credential" in s or "401" in s:return "AUTHENTICATION"
    return "OTHER_ERROR" if s else "NONE"
result={"generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"mode":"read_only_metadata","workflows":[]}
for name,wid in ids.items():
    w=req("/workflows/"+wid)
    if "api_http_error" in w:
        result["workflows"].append({"name":name,"id":wid,"http_error":w["api_http_error"]});continue
    nodes=w.get("nodes",[])
    x=req("/executions?workflowId="+wid+"&limit=8")
    executions=[]
    for e in x.get("data",[]):
        # Deliberately avoid includeData=true; protect client content
        executions.append({"id":e.get("id"),"status":e.get("status"),"startedAt":e.get("startedAt"),"stoppedAt":e.get("stoppedAt"),"finished":e.get("finished")})
    result["workflows"].append({"name":name,"id":wid,"isActive":w.get("active"),"node_count":len(nodes),"node_types":[n.get("type","?") for n in nodes],"execute_workflow_nodes":[{"name":n.get("name"),"workflowId_expression":str(n.get("parameters",{}).get("workflowId",""))[:110],"waitForSubWorkflow":n.get("parameters",{}).get("options",{}).get("waitForSubWorkflow")} for n in nodes if n.get("type","").endswith(".executeWorkflow")],"recent_execution_metadata":executions,"execution_query_error":x.get("api_http_error")})
out=pathlib.Path("/tmp/n8n-safe-diagnostic.json");out.write_text(json.dumps(result,indent=2))
print(json.dumps({"status":"READ_ONLY_COMPLETE","workflows":len(result["workflows"]),"summary": [{"name":w["name"],"nodes":w.get("node_count"),"http_error":w.get("http_error"),"runs":len(w.get("recent_execution_metadata",[]))} for w in result["workflows"]]}))
with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:
    f.write("## FirmaBlick n8n read-only diagnostic\n\nNo prompt, credentials, workflow node parameters or execution data were exported.\n\n")
    for w in result["workflows"]:
        f.write(f"- **{w['name']}**: {w.get('node_count','?')} nodes; {len(w.get('recent_execution_metadata',[]))} recent execution metadata records; HTTP issue {w.get('http_error','none')}\n")
print("Detailed sanitized metadata saved locally only; not uploaded as a public artifact.")
