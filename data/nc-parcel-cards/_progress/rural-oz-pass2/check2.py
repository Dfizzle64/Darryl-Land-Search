import json,subprocess,sys,urllib.parse,re,time
from cfg import C,PA,GIS
F=json.load(open('fields.json'))
AADT22="https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0"
AADT24="https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT__2024_AADT_Stations_published_September_2025/FeatureServer/0"
AADT25="https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1"
TOK=["LLC","INC","CORP","LP","LLP","LTD","TRUST","CHURCH","COMPANY","PARTNERSHIP","HOLDINGS","PROPERTIES"]
PHR=["CITY OF","COUNTY OF","STATE OF","TOWN OF"]
ENTITY_REGEX=r"\b(" + "|".join(TOK) + r")\b|^(" + "|".join(PHR) + r")\b"
def ent_where(f):
    u=f"UPPER({f})"
    parts=[]
    for t in TOK:
        parts += [f"{u} LIKE '% {t}'", f"{u} LIKE '% {t} %'", f"{u} LIKE '% {t},%'", f"{u} LIKE '% {t}.%'", f"{u} LIKE '{t} %'"]
    for p in PHR: parts.append(f"{u} LIKE '{p} %'")
    return "(" + " OR ".join(parts) + ")"
def post(url,data,t=60):
    args=["curl","-s","-m",str(t),"-A","Mozilla/5.0","-X","POST",url+"/query"]
    for k,v in data.items(): args += ["--data-urlencode",f"{k}={v}"]
    r=subprocess.run(args,capture_output=True,text=True)
    try: return json.loads(r.stdout)
    except Exception: return {"_raw":r.stdout[:200]}
def cnt(url,where):
    for i in range(2):
        d=post(url,{"where":where,"returnCountOnly":"true","f":"json"})
        if "count" in d: return d["count"]
        time.sleep(2)
    return "ERR:"+json.dumps(d)[:150]
def nonempty(f,typ,positive=False):
    if typ in("String",):
        return f"({f} IS NOT NULL AND {f} <> '' AND {f} <> '0')" if positive else f"({f} IS NOT NULL AND {f} <> '')"
    if typ in("Date","DateOnly"): return f"{f} IS NOT NULL"
    return f"{f} > 0"
def http(u):
    r=subprocess.run(["curl","-s","-L","-o","/tmp/pa.out","-w","%{http_code}|%{content_type}|%{size_download}|%{url_effective}","-m","45","-A","Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36",u],capture_output=True,text=True)
    body=open('/tmp/pa.out','rb').read(200000).decode('latin1',errors='ignore') if r.stdout else ''
    return r.stdout, body
only=sys.argv[1:] 
res={}
for fips,c in C.items():
    if only and fips not in only: continue
    R={"fips":fips,"slug":c["slug"],"url":c["url"]}
    nm=c["name"]
    R["aadt22_where"]=f"COUNTY='{nm}'"
    R["aadt22_count"]=cnt(AADT22,f"COUNTY='{nm}'")
    R["aadt22_nonblank"]=cnt(AADT22,f"COUNTY='{nm}' AND AADT_2022 IS NOT NULL AND AADT_2022 <> '' AND AADT_2022 <> ' '")
    tn=nm.title()
    R["aadt24_count"]=cnt(AADT24,f"County='{tn}'")
    R["aadt24_nonblank"]=cnt(AADT24,f"County='{tn}' AND AADT_2024 IS NOT NULL AND AADT_2024 <> ''")
    R["aadt25_count"]=cnt(AADT25,f"County='{tn}'")
    R["aadt25_nonnull"]=cnt(AADT25,f"County='{tn}' AND AADT_2025 > 0")
    fl=F[fips]; url=c["url"]
    R["total"]=cnt(url,"1=1")
    band=f"{c['acre']} >= 5 AND {c['acre']} <= 150"
    R["band"]=cnt(url,band)
    R["tax"]={f:cnt(url,nonempty(f,fl[f],True)) for f in c["tax"]}
    R["price"]={f:cnt(url,nonempty(f,fl[f],True)) for f in c["price"]}
    R["date"]={f:cnt(url,nonempty(f,fl[f])) for f in c["date"]}
    R["price_band"]={f:cnt(url,band+" AND "+nonempty(f,fl[f],True)) for f in c["price"]}
    if c["owner"]:
        o=c["owner"][0]
        R["owner_nonnull"]=cnt(url,nonempty(o,fl[o]))
        R["entity_where"]=ent_where(o)
        R["entity_all"]=cnt(url,ent_where(o))
        R["entity_band"]=cnt(url,band+" AND "+ent_where(o))
    # sample
    need=set([c["id"],c["pakey"]]+c["owner"]+c["tax"][:1]+c["price"][:1]+c["date"][:1])
    if fips=="37017": need|={"OwnerId","ParcelId"}
    if fips=="37089": need|={"PARCEL_PK"}
    if fips=="37161": need|={"Parcel_Number"}
    w=band+(" AND "+nonempty(c["price"][0],fl[c["price"][0]],True) if c["price"] else "")
    s=post(url,{"where":w,"outFields":",".join(sorted(need)),"returnGeometry":"false","resultRecordCount":"1","f":"json"})
    if not s.get("features"):
        s=post(url,{"where":w,"outFields":",".join(sorted(need)),"returnGeometry":"false","resultRecordCount":"1","orderByFields":c["id"],"f":"json"})
    if not s.get("features"):
        s=post(url,{"where":band,"outFields":",".join(sorted(need)),"returnGeometry":"false","f":"json"})
    feat=(s.get("features") or [{}])[0].get("attributes",{})
    R["sample"]=feat
    try:
        a=dict(feat)
        for k in("OwnerId","ParcelId"):
            if k in a and a[k] is not None: a[k]=int(a[k])
        pv=str(a.get(c["pakey"]) or "")
        tmpl=PA[fips]
        if fips=="37165": a["PIN"]=urllib.parse.quote(pv)
        elif fips=="37027": a["PID"]=pv.replace(" ","+")
        elif fips=="37049": a["PID"]=urllib.parse.quote(pv)
        else:
            for k in a:
                if isinstance(a[k],str): a[k]=urllib.parse.quote(a[k].strip(),safe="-")
        pa=tmpl.format(**a)
    except Exception as e:
        pa="ERR "+repr(e)
    R["pa_url"]=pa
    if not pa.startswith("ERR"):
        st,body=http(pa)
        R["pa_http"]=st
        m=re.search(r"<title>(.*?)</title>",body,re.S|re.I)
        R["pa_title"]=(m.group(1).strip()[:80] if m else "")
        R["pa_has_id"]= (pv.replace(" ","") in body.replace(" ","")) if pv else None
    st,body=http(GIS[fips])
    m=re.search(r"<title>(.*?)</title>",body,re.S|re.I)
    R["gis_url"]=GIS[fips]; R["gis_http"]=st; R["gis_title"]=(m.group(1).strip()[:80] if m else "")
    res[fips]=R
    print(json.dumps({k:v for k,v in R.items() if k not in("entity_where",)},default=str)[:1500],flush=True)
    json.dump(R,open(f'res/{fips}.json','w'),indent=1,default=str)
json.dump({"ENTITY_REGEX":ENTITY_REGEX},open('entity_rule.json','w'))
