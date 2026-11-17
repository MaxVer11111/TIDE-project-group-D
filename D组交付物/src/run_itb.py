"""Create an isolated native ITB fixture run via documented REST API.
Master key is read from environment or getpass and never saved in deliverables.
Each invocation creates its own test configuration; existing histories are preserved.
"""
import base64, getpass, os, re, sys, time, shutil
from datetime import datetime, timezone
import requests
from run_validation import ROOT, dump, digest

def main():
    key=os.environ.get('TIDE_ITB_MASTER_KEY') or getpass.getpass('Local ITB master API key: ')
    base='http://127.0.0.1:19000/api/rest'
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out=ROOT/'证据'/('itb-'+stamp);out.mkdir()
    secrets=[key]; calls=[]
    def safe(x):
        if isinstance(x,dict):return {k:('[REDACTED]' if k.lower()=='apikey' else safe(v)) for k,v in x.items()}
        if isinstance(x,list):return [safe(v) for v in x]
        if isinstance(x,str):
            for s in secrets: x=x.replace(s,'[REDACTED]')
        return x
    def api(method,path,auth,body=None):
        response=requests.request(method,base+path,headers={'ITB-API-KEY':auth},json=body,timeout=60)
        try:result=response.json()
        except ValueError:result={'text':response.text} if response.text else {}
        if isinstance(result,dict) and 'apiKey' in result:secrets.append(result['apiKey'])
        calls.append({'method':method,'path':safe(path),'status':response.status_code,'response':safe(result)})
        dump(out/'api-records.redacted.json',calls)
        if not response.ok:raise RuntimeError(f'{method} {safe(path)} HTTP {response.status_code}: {safe(result)}')
        return result
    suffix='TIDE D '+stamp
    domain=api('PUT','/domain',key,{'shortName':suffix,'fullName':suffix+' fixture validation'})['apiKey']
    community=api('PUT','/community',key,{'shortName':suffix,'fullName':suffix+' mock community','domain':domain})['apiKey']
    spec=api('PUT','/specification',community,{'shortName':'W1-W4','fullName':'TIDE supplied fixtures 1.0.0'})['apiKey']
    org=api('PUT','/organisation',community,{'shortName':'D-MOCK','fullName':'D group synthetic fixture test organisation'})['apiKey']
    system=api('PUT','/system',community,{'shortName':'Fixtures','fullName':'Supplied teaching fixtures','organisation':org,'version':'1.0.0'})['apiKey']
    archive=ROOT/'ITB/TIDE_D_W1W4.zip'
    shutil.copy2(archive,out/'executed-suite.zip')
    deployed=api('POST','/testsuite/deploy',community,{'specification':spec,'testSuite':base64.b64encode(archive.read_bytes()).decode(),'replaceTestHistory':False})
    dump(out/'deployment.json',safe(deployed))
    if not deployed.get('completed'):raise RuntimeError('ITB rejected suite; inspect deployment.json')
    actor=deployed['identifiers']['specifications'][0]['actors'][0]['identifier'];secrets.append(actor)
    api('PUT',f'/conformance/{system}/{actor}',org)
    start=api('POST','/tests/start',org,{'system':system,'actor':actor,'testSuite':['TIDE_D_W1W4'],'waitForCompletion':True,'maximumWaitTime':30})
    dump(out/'sessions-start.json',safe(start))
    sessions=[s['session'] for s in start['createdSessions']]
    if len(sessions)!=8:raise RuntimeError(f'Expected 8 native sessions, got {len(sessions)}')
    status={}
    for _ in range(24):
        status=api('POST','/tests/status',org,{'session':sessions,'withLogs':True,'withReports':True})
        if len(status.get('sessions',[]))==8 and all(s.get('endTime') for s in status['sessions']):break
        time.sleep(2)
    dump(out/'sessions-status.json',safe(status))
    for s in status.get('sessions',[]):
        if s.get('report'):(out/(s['session']+'.xml')).write_text(safe(s['report']),encoding='utf-8')
    summary={'native_itb_version':'1.30.3','fixture_scope_only':True,'suite_sha256':digest(archive),
             'sessions':[{k:v for k,v in s.items() if k not in ['report','logs']} for s in status.get('sessions',[])]}
    dump(out/'summary.json',safe(summary));dump(ROOT/'证据/latest-itb.json',{'directory':out.name})
    print(safe(summary))
    return 0 if len(summary['sessions'])==8 and all(s.get('endTime') and s['result']=='SUCCESS' for s in summary['sessions']) else 1
if __name__=='__main__':sys.exit(main())
