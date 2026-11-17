"""Explicit in-process mock; no real Credential, approval, Connector or benchmark."""
import copy, hashlib, json, sys
from datetime import datetime, timezone
from run_validation import ROOT, INPUT, read, dump, digest, metadata_check, json_errors

def content_hash(doc):
    return hashlib.sha256(json.dumps(doc,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

class MockAdmission:
    def __init__(self): self.published={}; self.available=True
    def issue(self,doc):
        if not self.available: return {'decision':'UNKNOWN','code':'VALIDATOR_UNAVAILABLE'}
        valid,errors,_,_,_=metadata_check(doc)
        return {'decision':'ALLOW' if valid else 'DENY','code':'CONTENT_OK' if valid else 'CONTENT_INVALID',
          'resource_id':doc.get('resource_id'),'product_version':doc.get('product_version'),
          'metadata_sha256':content_hash(doc),'rules':self.rules(),'errors':errors}
    def rules(self):
        return {p:digest(INPUT/p) for p in ['schemas/metadata.schema.json','shapes/resource-core-v1.ttl']}
    def publish(self,doc,report):
        if not self.available:return 'VALIDATOR_UNAVAILABLE'
        if report.get('decision')!='ALLOW':return 'CONTENT_INVALID'
        if (report.get('metadata_sha256')!=content_hash(doc) or report.get('rules')!=self.rules()
            or report.get('resource_id')!=doc.get('resource_id') or report.get('product_version')!=doc.get('product_version')):
            return 'STALE_REPORT'
        self.published[doc['resource_id']]=copy.deepcopy(doc)
        return 'PUBLISHED'

class MockAuthorization:
    """All flags below are controlled synthetic test state, NOT trusted identity evidence."""
    def __init__(self): self.grant=None; self.member=True; self.qualified=True; self.available=True
    def approve(self,actor):
        if actor!='owner-p1':return 'OWNER_REQUIRED'
        self.grant=read(INPUT/'examples/grant-active.json')
        return 'MOCK_APPROVED'
    def decide(self, user='student-01', project='tide-demo-project', resource='tide-p1-process-v1',
               action='READ_DATA', purpose='research-demo', now=None):
        now=now or datetime.now(timezone.utc)
        if not self.available:return 'AUTHORIZATION_UNAVAILABLE'
        if not self.qualified:return 'QUALIFICATION_INVALID'
        if not self.member:return 'MEMBERSHIP_INACTIVE'
        if not self.grant:return 'GRANT_REQUIRED'
        g=self.grant
        if g['status']!='ACTIVE':return 'GRANT_REVOKED'
        if not datetime.fromisoformat(g['valid_from'].replace('Z','+00:00'))<=now<datetime.fromisoformat(g['valid_until'].replace('Z','+00:00')):return 'GRANT_EXPIRED'
        if user!=g['subject_user_id'] or project!=g['project_id'] or resource not in g['resource_ids'] or action not in g['actions'] or purpose!=g['purpose']:return 'SCOPE_DENIED'
        return 'ALLOW'

def main():
    out=ROOT/'证据'/('mock-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));out.mkdir()
    rows=[]
    def check(name,expected,actual,detail=None):
        rows.append({'case':name,'expected':expected,'actual':actual,'status':'PASS' if actual==expected else 'FAIL',
                     'mode':'IN_PROCESS_MOCK','detail':detail})
    a=MockAdmission(); doc=read(INPUT/'metadata/p1-valid.jsonld'); report=a.issue(doc)
    check('TC01 合格P1模拟发布','PUBLISHED',a.publish(doc,report))
    saved=content_hash(a.published)
    for name in ['p1-missing-rights','p1-missing-source','p1-invalid-access']:
        bad=read(INPUT/'metadata'/(name+'.jsonld'))
        check('TC01 '+name,'CONTENT_INVALID',a.publish(bad,a.issue(bad)))
        check('TC01 错误发布不更新 '+name,saved,content_hash(a.published))
    changed=copy.deepcopy(doc);changed['title']+=' [MOCK mutation]'
    check('D2 更换metadata后旧报告失效','STALE_REPORT',a.publish(changed,report))
    stale=copy.deepcopy(report);stale['rules']['shapes/resource-core-v1.ttl']='0'*64
    check('D2 不同规则hash报告失效','STALE_REPORT',a.publish(doc,stale))
    a.available=False
    check('D2 Validator不可用不发布','VALIDATOR_UNAVAILABLE',a.publish(doc,report))
    check('D2 故障后内容未改变',saved,content_hash(a.published))
    b=MockAuthorization()
    check('TC02 有模拟资格但无Grant','GRANT_REQUIRED',b.decide())
    check('TC02 申请人自批','OWNER_REQUIRED',b.approve('student-01'))
    check('TC02 模拟owner批准','MOCK_APPROVED',b.approve('owner-p1'))
    check('TC02 模拟批准后允许','ALLOW',b.decide())
    for name,args in [('资源',{'resource':'tide-p2-benchmark-v1'}),('动作',{'action':'EXECUTE'}),
                      ('用途',{'purpose':'commercial'}),('个人',{'user':'student-02'}),('项目',{'project':'other-project'})]:
        check('TC02/03 错误'+name,'SCOPE_DENIED',b.decide(**args))
    b.member=False;check('TC03 退出个人','MEMBERSHIP_INACTIVE',b.decide());b.member=True
    b.qualified=False;check('TC02 无模拟资格','QUALIFICATION_INVALID',b.decide());b.qualified=True
    check('TC07 到期边界','GRANT_EXPIRED',b.decide(now=datetime(2027,11,1,tzinfo=timezone.utc)))
    b.grant=read(INPUT/'examples/grant-revoked.json');check('TC07 模拟收回','GRANT_REVOKED',b.decide())
    b.available=False;check('TC09 判定故障','AUTHORIZATION_UNAVAILABLE',b.decide())
    recipe=read(INPUT/'examples/recipe-valid.json');recipe['feature_fields'][0]='target_temp'
    errors=json_errors(recipe,read(INPUT/'schemas/recipe.schema.json'))
    check('TC06 派生负例标签作输入',True,any(e['keyword']=='enum' and 'feature_fields' in e['path'] for e in errors),errors)
    dump(out/'mock-results.json',rows)
    dump(out/'derived-recipe-negative.json',{'origin':'examples/recipe-valid.json','change':'feature_fields[0]=target_temp',
          'classification':'explicit synthetic negative fixture','data':recipe})
    dump(out/'admission-report.example.json',report)
    dump(ROOT/'证据/latest-mock.json',{'directory':out.name})
    print(json.dumps({'checks':len(rows),'pass':sum(r['status']=='PASS' for r in rows),'directory':out.name}))
    return 0 if all(r['status']=='PASS' for r in rows) else 1
if __name__=='__main__':sys.exit(main())
