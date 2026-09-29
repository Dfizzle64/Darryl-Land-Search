import urllib.request,ssl,sys,json,concurrent.futures as cf
ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
UA={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36','Accept':'text/html,application/xhtml+xml,*/*'}
def t(u,needle=None):
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=40,context=ctx)
        b=r.read(); s=b.decode('utf-8','replace')
        import re; title=(re.search(r'<title[^>]*>(.*?)</title>',s,re.S|re.I) or [None,''])[1].strip()[:80]
        return dict(url=u,status=r.status,final=r.geturl(),bytes=len(b),title=title,idInBody=(needle in s) if needle else None)
    except urllib.error.HTTPError as e: return dict(url=u,status=e.code,err=str(e)[:100])
    except Exception as e: return dict(url=u,status=None,err=f'{type(e).__name__}: {str(e)[:120]}')
if __name__=='__main__':
    L=json.load(open(sys.argv[1]))
    with cf.ThreadPoolExecutor(10) as ex:
        for k,r in zip(L,ex.map(lambda x:t(x[1],x[2] if len(x)>2 else None),L)): print(k[0],json.dumps(r))
