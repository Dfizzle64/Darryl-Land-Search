import json,glob,csv,sys,urllib.request,urllib.parse,ssl,concurrent.futures as cf,re
ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
UA={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) Chrome/124 Safari/537.36'}
def get(url,params,timeout=45):
    u=url+'?'+urllib.parse.urlencode(params)
    req=urllib.request.Request(u,headers=UA)
    with urllib.request.urlopen(req,timeout=timeout,context=ctx) as r: return json.loads(r.read().decode('utf-8','replace'))
IDPREF=['PIN','PIN14','PIN_NUM','PARNO','PARID','PARCEL_ID','PARCELID','PARCELNUMBER','PARCEL','NCPIN','GPIN','REID','PID','TAG','NEWPIN','GISPIN','PIN15','GEOPIN','ALPHA','TMS','LINKPIN']
def pick_id(fields,hint):
    names=[f['name'] for f in fields]; up={n.upper():n for n in names}
    for h in hint:
        if h in names: return h
        if h.upper() in up: return up[h.upper()]
    for p in IDPREF:
        if p in up: return up[p]
    for n in names:
        if re.search(r'pin|parcel|parno|reid',n,re.I) and 'shape' not in n.lower(): return n
    return None
def nn(f,typ):
    return f"{f} IS NOT NULL AND {f} <> ''" if typ=='esriFieldTypeString' else f"{f} IS NOT NULL"
def cnt(url,where):
    c=get(url+'/query',{'where':where,'returnCountOnly':'true','f':'json'})
    if 'error' in c: raise RuntimeError('count: '+json.dumps(c['error'])[:200])
    return c.get('count')
def check(url,hint=(),where='1=1',acrehint=()):
    res=dict(url=url,where=where,ok=False)
    try:
        L=get(url,{'f':'json'})
        if 'error' in L: res['err']='layer: '+json.dumps(L['error'])[:200]; return res
        res['geom']=L.get('geometryType'); fields=L.get('fields') or []
        ftype={f['name']:f['type'] for f in fields}; up={n.upper():n for n in ftype}
        if res['geom']!='esriGeometryPolygon': res['err']=f"not polygon ({res['geom']})"; return res
        res['count']=total=cnt(url,where)
        if not total: res['err']='count 0'; return res
        cands=[]
        for h in list(hint)+IDPREF:
            n=h if h in ftype else up.get(h.upper())
            if n and n not in cands: cands.append(n)
        cands+= [n for n in ftype if re.search(r'pin|parcel|parno|reid',n,re.I) and 'shape' not in n.lower() and n not in cands]
        idf=None
        for n in cands[:8]:
            try: k=cnt(url,f"({where}) AND {nn(n,ftype[n])}")
            except Exception: continue
            if k and k>=0.8*total: idf=n; res['idNonEmpty']=k; break
        res['idField']=idf
        if not idf: res['err']='no populated parcel id field'; return res
        s=get(url+'/query',{'where':f"({where}) AND {nn(idf,ftype[idf])}",'outFields':idf,'returnGeometry':'true','outSR':'4326','resultRecordCount':'5','orderByFields':idf,'f':'json'},timeout=90)
        if 'error' in s: res['err']='sample: '+json.dumps(s['error'])[:200]; return res
        ft=next((f for f in s.get('features',[]) if (f.get('geometry') or {}).get('rings')),None)
        if not ft: res['err']='no sample feature with rings'; return res
        pts=ft['geometry']['rings'][0]; x=sum(p[0] for p in pts)/len(pts); y=sum(p[1] for p in pts)/len(pts)
        res['sampleId']=ft['attributes'].get(idf); res['sampleXY']=[round(x,4),round(y,4)]
        if not (-84.4<x<-75.3 and 33.7<y<36.7): res['err']=f'sample outside NC {x},{y}'; return res
        num=('esriFieldTypeDouble','esriFieldTypeSingle','esriFieldTypeInteger','esriFieldTypeSmallInteger')
        acands=[]
        for h in list(acrehint): 
            n=h if h in ftype else up.get(h.upper())
            if n and n not in acands: acands.append(n)
        acands+=[n for n in ftype if re.search(r'acre|acres|acr',n,re.I) and n not in acands]
        acands=[n for n in acands if ftype[n] in num]
        res['acreField']=None
        for n in acands:
            try: k=cnt(url,f"({where}) AND {n} >= 5 AND {n} <= 150")
            except Exception: continue
            if k and k>0.03*total: res['acreField']=n; res['acres5to150']=k; break
        if not res['acreField']: res['err']='no usable numeric acreage field (5-150)'; return res
        res['ok']=True
    except Exception as e: res['err']=f'{type(e).__name__}: {str(e)[:200]}'
    return res
if __name__=='__main__':
    todo=json.load(open(sys.argv[1]))
    with cf.ThreadPoolExecutor(12) as ex:
        out=list(ex.map(lambda t: {**t, **check(t['url'],t.get('hint',[]),t.get('where','1=1'),t.get('acrehint',[]))}, todo))
    json.dump(out,open(sys.argv[2],'w'),indent=1)
