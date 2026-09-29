import json,urllib.request,urllib.parse,ssl,sys,concurrent.futures as cf
sys.path.insert(0,'/workspace/pass2'); from cfg import CFG, ENTITY_TOKENS_SQL
ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
UA={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) Chrome/124 Safari/537.36'}
def g(u,p,post=True):
    data=urllib.parse.urlencode(p).encode()
    req=urllib.request.Request(u,data=data,headers=UA) if post else urllib.request.Request(u+'?'+data.decode(),headers=UA)
    return json.loads(urllib.request.urlopen(req,timeout=90,context=ctx).read())
def cnt(u,w):
    r=g(u+'/query',{'where':w,'returnCountOnly':'true','f':'json'})
    if 'error' in r: return 'ERR:'+json.dumps(r['error'])[:150]
    return r.get('count')
def nz(f,t):
    if t=='String': return f"({f} IS NOT NULL AND {f}<>'' AND {f}<>'0' AND {f}<>' ')"
    return f"({f} IS NOT NULL AND {f}>0)"
def ent(f): return '('+' OR '.join(f"{f} LIKE '{p}'" for p in ENTITY_TOKENS_SQL)+')'
def run(k,c,types):
    u=c['url']; a=c['acre']
    rng=f"{a}>=5 AND {a}<=150"
    if c.get('acreRng'): rng=c['acreRng']
    o={'county':k,'rangeWhere':rng}
    o['total']=cnt(u,'1=1'); o['inRange']=cnt(u,rng)
    o['tax']={f:cnt(u,nz(f,types[f])) for f in c['tax']}
    o['taxInRange']={f:cnt(u,rng+' AND '+nz(f,types[f])) for f in c['tax'][-1:]}
    o['salePrice']={f:cnt(u,nz(f,types[f])) for f in c['sp']}
    o['salePriceInRange']={f:cnt(u,rng+' AND '+nz(f,types[f])) for f in c['sp'][:1]}
    o['saleDate']={f:cnt(u,f"{f} IS NOT NULL"+(f" AND {f}<>'' AND {f}<>' '" if types[f]=='String' else (f" AND {f}>0" if types[f] in('Integer','Double','SmallInteger') else ''))) for f in c['sd']}
    o['entityWhere']=rng+' AND '+ent(c['owner'][0])
    o['entityInRange']=cnt(u,o['entityWhere'])
    o['ownerNonNullInRange']=cnt(u,rng+f" AND {c['owner'][0]} IS NOT NULL")
    s=g(u+'/query',{'where':rng+' AND '+nz(c['sp'][0],types[c['sp'][0]]),'outFields':','.join(c['ids']+c['owner'][:1]+c['sp'][:1]+c['sd'][:1]+[a]),'returnGeometry':'false','resultRecordCount':'3','f':'json'})
    o['sample']=[x['attributes'] for x in s.get('features',[])][:3] if 'error' not in s else s['error']
    se=g(u+'/query',{'where':o['entityWhere'],'outFields':c['owner'][0],'returnGeometry':'false','resultRecordCount':'8','f':'json'})
    o['entitySample']=[x['attributes'][c['owner'][0]] for x in se.get('features',[])] if 'error' not in se else se['error']
    return o
if __name__=='__main__':
    keys=sys.argv[1:] or list(CFG)
    types=json.load(open('/workspace/pass2/types.json'))
    def w(k):
        try: return run(k,CFG[k],types[k])
        except Exception as e: return {'county':k,'err':f'{type(e).__name__}: {e}'}
    with cf.ThreadPoolExecutor(8) as ex:
        res=list(ex.map(w,keys))
    for r in res:
        json.dump(r,open(f"/workspace/pass2/res_{r['county']}.json",'w'),indent=1,default=str)
        print(json.dumps(r,default=str)[:1500]); print()
