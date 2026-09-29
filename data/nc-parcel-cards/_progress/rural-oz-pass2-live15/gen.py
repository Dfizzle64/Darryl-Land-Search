import json,yaml,sys,urllib.parse,re
sys.path.insert(0,'/workspace/pass2')
from cfg import CFG, ENTITY_TOKENS_SQL
from meta import M, AADT22
D='/workspace/gis-research/cards/NC/'
A=json.load(open('/workspace/pass2/aadt.json'))
AURL="https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0"
BURL="https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1"
SEG="https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/0"
Y24="https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT__2024_AADT_Stations_published_September_2025/FeatureServer/0"
REGEX=r"(?i)(\bL\.?\s?L\.?\s?C\b|\bINC\b|\bCORP|\bL\.?\s?P\b|\bLLP\b|\bLLLP\b|\bLTD\b|TRUST|CHURCH|MINISTR|\bCOMPANY\b|PARTNERSHIP|PRTNRSHP|HOLDINGS|PROPERTIES|INVESTMENT|ASSOCIATION|\bHOA\b|FOUNDATION|AUTHORITY|\bDEVELOPMENT|BOARD OF EDUCATION|^(CITY|COUNTY|STATE|TOWN|VILLAGE) OF\b|^UNITED STATES|^NORTH CAROLINA\b|\bCOUNTY$)"
def q(url,params): return url+'/query?'+urllib.parse.urlencode(params)
def build(slug):
    fips=slug[:5]; c=CFG[slug]; m=M[slug]; name=m['name']; U=name.upper()
    r=json.load(open(f'/workspace/pass2/res_{slug}.json'))
    y=yaml.safe_load(open(D+slug+'.yaml'))
    fm={}
    for l in y['layers']:
        if (l.get('restUrl') or '').replace('https://','http://')==c['url'].replace('https://','http://'): fm=l.get('fieldMap') or {}
    a=A[name]; tot22,nb22=AADT22[fips]
    url=c['url'].replace('http://maps.wakegov.com','https://maps.wakegov.com')
    gaps=[]
    if m['pa']['template'] is None: gaps.append('PA deep link: no GET URL with parcel id (search page only) — '+m['pa']['note'].split(':',1)[1].strip()[:160])
    if slug in('37025-cabarrus','37057-davidson'): gaps.append('Sale date is year+month only on parcel layer (no day)')
    if slug=='37183-wake': gaps.append('Box HTTPS to *.wakegov.com resets at TLS; REST verified over http://maps.wakegov.com; Account.asp verified via external fetch')
    if slug=='37141-pender': gaps.append('Box HTTPS to *.pendercountync.gov resets at TLS; all pass2 REST counts + PA test run via external fetch')
    if slug=='37169-stokes': gaps.append('PACKAGE_SALE_DATE sparse (12,722 of 32,131) — use DEED_DATE fallback')
    gaps.append(f"AADT_2022 blank at {tot22-nb22} of {tot22} stations on the 2022 layer (NCDOT counts on a cycle) — prefer 2025 layer / latest non-blank year")
    gaps.append('No multi-transfer sale history on primary layer (last sale only)' if slug not in('37109-lincoln','37057-davidson') else 'Last sale on primary layer; separate sales layer documented in saleHistory.notes')
    p={
     'label':'PASS2 full-suite upgrade — rural OZ counties (tax / sale / owner-entity / PA link / GIS link / AADT)',
     'verifiedAt':'2026-09-28','verifiedBy':'North Carolina Public Info Researcher',
     'aadtScreening':{
        'source':'NCDOT Traffic Survey Group (public AGOL)',
        'layer':'NCDOT_AADT_Stations FeatureServer/0 (documented in enrichment/NC/ncdot-aadt-statewide-dig-2026-09-24.yaml)',
        'restUrl':AURL,'countyField':'COUNTY','countyValue':U,'valueField':'AADT_2022','valueType':'string (trim; blank = no count that year)',
        'countQuery':q(AURL,{'where':f"COUNTY='{U}'",'returnCountOnly':'true','f':'json'}),
        'featureQuery':q(AURL,{'where':f"COUNTY='{U}'",'outFields':'LocationID,ROUTE,LOCATION,AADT_2021,AADT_2022','outSR':'4326','f':'geojson','resultOffset':0,'resultRecordCount':1000}),
        'liveStationCount':tot22,
        'stationsWithAADT2022':nb22,
        'newerYearAvailable':{
           'available':True,
           'layer':'NCDOT_2025_AADTandTrafficSegments_gdb FeatureServer/1 (NCDOT_2025_AADT_Stations; dataLastEdit 2026-09-23)',
           'restUrl':BURL,'countyField':'County','countyValue':name,'valueField':'AADT_2025','valueType':'integer (null = no count)',
           'countQuery':q(BURL,{'where':f"County='{name}'",'returnCountOnly':'true','f':'json'}),
           'featureQuery':q(BURL,{'where':f"County='{name}'",'outFields':'LocationID,RouteID,Located_On,Crossroad,AADT_2023,AADT_2024,AADT_2025','outSR':'4326','f':'geojson','resultOffset':0,'resultRecordCount':1000}),
           'liveStationCount':a['s2025_total'],'stationsWithAADT2025':a['s2025_nonnull'],'stationsWithAADT2024':a['s2024_nonnull'],
           'segmentsLayer':SEG+' (AADT, AADT_Year=2025, AADTT truck volumes; polyline, statewide — spatial filter by county envelope)',
           'also':Y24+' (2024 stations, published Sep 2025; County title-case; AADT_2023/AADT_2024 strings)',
        },
        'recommendation':'Keep AADT_2022 wiring (#59) as-is; optionally switch to 2025 stations layer and take latest non-null of AADT_2025→AADT_2024→AADT_2023 per station. Note County value case differs (2022 layer UPPER, 2025 layer Title).',
     },
     'primaryParcelLayer':{'restUrl':url,'acreageField':c['acre'],'range5to150Where':r['rangeWhere'],'liveTotalParcels':r['total'],'liveParcels5to150':r['inRange']},
     'taxValues':{'status':'ok','fields':{f:fm.get(f,'tax') for f in c['tax']},'liveNonZeroCounty':r['tax'],'liveNonZero5to150':r['taxInRange'],'notes':m['taxNote'],
        'publicFallback':m['pa']['template'] or m['pa']['tested']},
     'saleHistory':{'status':'ok','priceFields':c['sp'],'dateFields':c['sd'],'livePriceGt0County':r['salePrice'],'livePriceGt0_5to150':r['salePriceInRange'],'liveDateNonNullCounty':r['saleDate'],'notes':m['saleNote']},
     'ownerEntity':{
        'ownerFields':c['owner'],'primaryOwnerField':c['owner'][0],
        'rule':{'apply':f"Uppercase + trim {c['owner'][0]} (optionally also {c['owner'][1]})" if len(c['owner'])>1 else f"Uppercase + trim {c['owner'][0]}",
                'regex':REGEX,
                'sqlLikeTokens':ENTITY_TOKENS_SQL,
                'caveats':'TRUST/TRUSTEE also flags family/revocable living trusts (still non-individual title holders); "% COUNTY" suffix catches e.g. "PERSON COUNTY"; bare "CO" and "ESTATE" intentionally excluded (too many false positives). Some owner strings carry trailing spaces (Wake) or mixed case (Yadkin) — normalize first.'},
        'liveEntityCount5to150':r['entityInRange'],
        'liveOwnerNonNull5to150':r.get('ownerNonNullInRange'),
        'entityQuery':'where='+r.get('entityWhere', r['rangeWhere']+' AND (<owner> LIKE any sqlLikeTokens)'),
     },
     'paDeepLink':{'template':m['pa']['template'],'testedUrl':m['pa']['tested'],'httpStatus':m['pa']['status'],'notes':m['pa']['note']},
     'jurisdictionGisViewer':{'url':m['gis']['url'],'httpStatus':m['gis']['status'],'notes':m['gis']['note']},
     'gaps':gaps,
    }
    if slug=='37141-pender': p['ownerEntity']['entityQuery']='where='+r['rangeWhere']+" AND (NAME LIKE any sqlLikeTokens) [run via external fetch]"
    return p
def md(slug,p):
    a=p['aadtScreening']; n=a['newerYearAvailable']; t=p['taxValues']; s=p['saleHistory']; o=p['ownerEntity']; pa=p['paDeepLink']; g=p['jurisdictionGisViewer']
    L=[ '', '## PASS2 — full-suite upgrade (rural OZ) · verifiedAt 2026-09-28', '',
      '_Added by North Carolina Public Info Researcher. Existing sections above (incl. cities-first municipality routing) unchanged._','',
      '### 1. AADT / screening',
      f"- NCDOT_AADT_Stations FS/0, `COUNTY='{a['countyValue']}'`, field `AADT_2022` (string) — **{a['liveStationCount']} stations live**, {a['stationsWithAADT2022']} with a non-blank 2022 count.",
      f"- Count: `{a['countQuery']}`",
      f"- Features: `{a['featureQuery']}`",
      f"- **Newer year:** NCDOT_2025_AADTandTrafficSegments_gdb FS/1, `County='{n['countyValue']}'`, `AADT_2025` (int) — {n['liveStationCount']} stations; {n['stationsWithAADT2025']} with 2025, {n['stationsWithAADT2024']} with 2024. Segments FS/0 has 2025 AADT + AADTT. 2024 stations svc also public.",
      '', '### 2. Tax values',
      f"- Layer `{p['primaryParcelLayer']['restUrl']}` — total {p['primaryParcelLayer']['liveTotalParcels']}, 5–150 ac {p['primaryParcelLayer']['liveParcels5to150']} (`{p['primaryParcelLayer']['range5to150Where']}`).",
      f"- Non-zero county: {', '.join(f'`{k}` {v}' for k,v in t['liveNonZeroCounty'].items())}; in 5–150: {', '.join(f'`{k}` {v}' for k,v in t['liveNonZero5to150'].items())}. **Status: ok.**",
      f"- {t['notes']}",
      '', '### 3. Sale history',
      f"- Price {', '.join(f'`{k}`>0 {v}' for k,v in s['livePriceGt0County'].items())} (5–150: {', '.join(str(v) for v in s['livePriceGt0_5to150'].values())}); date non-null {', '.join(f'`{k}` {v}' for k,v in s['liveDateNonNullCounty'].items())}. **Status: ok.**",
      f"- {s['notes']}",
      '', '### 4. Owner entity',
      f"- Owner fields: {', '.join('`'+x+'`' for x in o['ownerFields'])}. Rule: uppercase/trim, flag if matches regex `{o['rule']['regex']}`.",
      f"- **Live entity-pattern parcels 5–150 ac: {o['liveEntityCount5to150']}** (of {o['liveOwnerNonNull5to150'] or p['primaryParcelLayer']['liveParcels5to150']} with owner). Server-side SQL = range AND OR-list of LIKE tokens (see YAML `pass2.ownerEntity.sqlLikeTokens`).",
      f"- Caveats: {o['rule']['caveats']}",
      '', '### 5. PA deep link',
      f"- Template: `{pa['template']}`" if pa['template'] else "- Template: **none (gap)**",
      f"- Tested `{pa['testedUrl']}` → **{pa['httpStatus']}**. {pa['notes']}",
      '', '### 6. Jurisdiction GIS viewer',
      f"- `{g['url']}` → **{g['httpStatus']}**. {g['notes']}",
      '', '### Pass2 gaps', *[f"- {x}" for x in p['gaps']], '' ]
    return '\n'.join(L)
if __name__=='__main__':
    for slug in CFG:
        p=build(slug)
        # YAML: append block (text) preserving existing formatting
        yt=open(D+slug+'.yaml').read()
        assert '\npass2:' not in yt, slug
        blk=yaml.safe_dump({'pass2':p},sort_keys=False,allow_unicode=True,width=10000,default_flow_style=False)
        open(D+slug+'.yaml','w').write(yt.rstrip('\n')+'\n\n# ---- PASS2 full-suite upgrade (rural OZ) — verifiedAt 2026-09-28 ----\n'+blk)
        j=json.load(open(D+slug+'.json')); j['pass2']=p
        open(D+slug+'.json','w').write(json.dumps(j,indent=2)+'\n')
        mt=open(D+slug+'.md').read(); assert '## PASS2' not in mt
        open(D+slug+'.md','w').write(mt.rstrip('\n')+'\n'+md(slug,p))
        # verify
        y2=yaml.safe_load(open(D+slug+'.yaml')); j2=json.load(open(D+slug+'.json'))
        assert y2['pass2']==j2['pass2'], slug
        print('ok',slug)
