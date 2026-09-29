s=open('check2.py').read()
import re
lines=s.split("\n")
lines[6]='TOK=["LLC","INC","CORP","LP","LLP","LTD","TRUST","CHURCH","COMPANY","PARTNERSHIP","HOLDINGS","PROPERTIES"]'
lines[7]='PHR=["CITY OF","COUNTY OF","STATE OF","TOWN OF"]'
lines[8]='ENTITY_REGEX=r"\\b(" + "|".join(TOK) + r")\\b|^(" + "|".join(PHR) + r")\\b"'
s="\n".join(lines)
s=s.replace("""    for p in PHR: parts.append(f"{u} LIKE '%{p}%'")""","""    for p in PHR: parts.append(f"{u} LIKE '{p} %'")""")
s=s.replace('def post(url,data,t=90):','def post(url,data,t=60):')
s=s.replace("""res={}
try: res=json.load(open('results.json'))
except Exception: pass""","res={}")
s=s.replace("json.dump(res,open('results.json','w'),indent=1,default=str)","json.dump(R,open(f'res/{fips}.json','w'),indent=1,default=str)")
open('check2.py','w').write(s)
