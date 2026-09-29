import json,subprocess,sys,urllib.parse
from cfg import C
def get(u,params=None,t=60):
    if params: u=u+"?"+urllib.parse.urlencode(params)
    r=subprocess.run(["curl","-s","-m",str(t),"-A","Mozilla/5.0",u],capture_output=True,text=True)
    try: return json.loads(r.stdout)
    except Exception: return {"_raw":r.stdout[:300]}
out={}
for f,c in C.items():
    d=get(c["url"],{"f":"json"})
    flds={x["name"]:x["type"].replace("esriFieldType","") for x in d.get("fields",[])}
    want=[c["acre"],c["id"],c["pakey"]]+c["owner"]+c["tax"]+c["price"]+c["date"]
    miss=[w for w in want if w not in flds]
    out[f]=flds
    print(f,c["slug"],"nf",len(flds),"MISSING:",miss, {w:flds.get(w) for w in c["price"]+c["date"]})
    if miss or not c["owner"]:
        print("   ALL:", list(flds.items()))
json.dump(out,open("fields.json","w"))
