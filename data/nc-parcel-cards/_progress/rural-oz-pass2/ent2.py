import json,sys,subprocess,time
from cfg import C
TOK=["LLC","INC","LP","LLP","LTD","TRUST","CHURCH","COMPANY","PARTNERSHIP","HOLDINGS","PROPERTIES","CORP"]
def sqlw(o):
    u=f"UPPER({o})"
    p=[f"{u} LIKE '% {t}%'" for t in TOK]+[f"{u} LIKE '%,LLC%'",f"{u} LIKE '%,INC%'"]+[f"{u} LIKE '{x} OF %'" for x in ["CITY","COUNTY","STATE","TOWN"]]
    return "("+" OR ".join(p)+")"
def cnt(url,where,t=90):
    for i in range(2):
        r=subprocess.run(["curl","-s","-m",str(t),"-A","Mozilla/5.0","-X","POST",url+"/query","--data-urlencode","where="+where,"--data-urlencode","returnCountOnly=true","--data-urlencode","f=json"],capture_output=True,text=True)
        try:
            d=json.loads(r.stdout)
            if "count" in d: return d["count"]
        except Exception: pass
        time.sleep(2)
    return "ERR"
A25="https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1"
for f in sys.argv[1:]:
    c=C[f]; out={}
    out["aadt25_with2024"]=cnt(A25,f"County='{c['name'].title()}' AND AADT_2024 > 0")
    if c["owner"]:
        o=c["owner"][0]; w=sqlw(o)
        out["sqlw"]=w
        out["entity_all"]=cnt(c["url"],w)
        out["entity_band"]=cnt(c["url"],f"{c['acre']} >= 5 AND {c['acre']} <= 150 AND "+w)
    json.dump(out,open(f"res/{f}.ent.json","w"),indent=1)
    print(f,out.get("entity_all"),out.get("entity_band"),out["aadt25_with2024"],flush=True)
