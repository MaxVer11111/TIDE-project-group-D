"""Offline review of native results and session-linked validator responses."""
import json, xml.etree.ElementTree as ET
from run_validation import ROOT, INPUT, read, dump, digest

def main():
    folder=ROOT/'证据'/read(ROOT/'证据/latest-itb.json')['directory']
    starts=read(folder/'sessions-start.json')['createdSessions']
    audit=[json.loads(x) for x in (ROOT/'证据/validator-bridge/adapter-calls.jsonl').read_text(encoding='utf-8').splitlines()]
    statuses={s['session']:s for s in read(folder/'sessions-status.json')['sessions']}
    markers={'P1_MISSING_RIGHTS':'rights_holder','P1_MISSING_SOURCE':'source','P1_BAD_ACCESS':'access_level','P4_LEAK':'records'}
    reviewed=[];ns={'t':'http://www.gitb.com/tr/v1/'}
    for s in starts:
        case=s['testCase'];sid=s['session'];report=ET.parse(folder/(sid+'.xml'))
        descriptions=[e.text or '' for e in report.findall('.//t:error/t:description',ns)]
        ok=statuses[sid]['result']=='SUCCESS' and bool(statuses[sid].get('endTime'))
        if case in markers:ok=ok and markers[case] in ' '.join(descriptions)
        detail={'native_error_descriptions':descriptions}
        if case.startswith('P3_'):
            matches=[a for a in audit if a['native_itb_session']==sid]
            ok=ok and len(matches)==1
            if matches:
                item=matches[0];response=item['response'];valid=case=='P3_VALID'
                fixture=INPUT/'examples'/('recipe-valid.json' if valid else 'recipe-invalid.json')
                ok=ok and response['conforms']==valid and response['input_sha256']==digest(fixture) and response['rule_sha256']==digest(INPUT/'schemas/recipe.schema.json')
                if not valid:
                    errs=response['errors']
                    ok=ok and any(e['keyword']=='enum' and e['path']=='$.smoothing_window' for e in errs)
                    ok=ok and any(e['keyword']=='additionalProperties' and 'script' in e['message'] for e in errs)
                detail['adapter_response']=response
        reviewed.append({'test_case':case,'native_session':sid,'review':'PASS' if ok else 'FAIL',**detail})
    dump(folder/'reason-review.json',reviewed)
    dump(ROOT/'证据/ITB最终结果索引.json',{'directory':folder.name,'reviewed_cases':reviewed})
    assert len(reviewed)==8 and all(r['review']=='PASS' for r in reviewed), 'Native evidence reason review failed'
    print('Native evidence reason review: 8/8 PASS')
if __name__=='__main__':main()
