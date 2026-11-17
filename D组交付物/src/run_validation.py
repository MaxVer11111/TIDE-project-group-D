"""Run real validators on supplied teaching fixtures; never claims ITB sessions."""
from pathlib import Path
import csv, hashlib, json, sys, platform, shutil, inspect
from datetime import datetime, timezone
from importlib.metadata import version
from jsonschema import Draft202012Validator, FormatChecker
from rdflib import Graph, Namespace, RDF
from pyshacl import validate

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'TIDE_Minimal_Research_Scenario'
INPUT = ROOT / 'inputs'
SH = Namespace('http://www.w3.org/ns/shacl#')
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2), encoding='utf-8')
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def json_errors(doc, schema):
    Draft202012Validator.check_schema(schema)
    return [{'path': e.json_path, 'keyword': e.validator, 'message': e.message,
             'schema_path': list(e.absolute_schema_path)}
            for e in Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(doc)]
def metadata_check(doc):
    errors = json_errors(doc, read(INPUT/'schemas/metadata.schema.json'))
    graph = Graph().parse(data=json.dumps(doc), format='json-ld')
    targets = list(graph.subjects(RDF.type, Namespace('https://example.invalid/tide/vocab#').ResearchResource))
    conforms, report, raw = validate(graph, shacl_graph=str(INPUT/'shapes/resource-core-v1.ttl'),
                                    inference='none', meta_shacl=True)
    return not errors and bool(conforms) and bool(targets), errors, report, raw, targets

def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = ROOT/'证据'/stamp
    out.mkdir(parents=True)
    # Snapshot only public teaching fixtures, never copy restricted CSV into reports.
    for folder in ['metadata','schemas','shapes','examples','identity','api']:
        shutil.copytree(SOURCE/folder, INPUT/folder, dirs_exist_ok=True)
    for name in ['data-manifest.json','dictionary.csv','TERMS.md']:
        (INPUT/'data').mkdir(parents=True,exist_ok=True)
        shutil.copy2(SOURCE/'data'/name, INPUT/'data'/name)
    dump(out/'input-hashes.json', {str(p.relative_to(SOURCE)).replace('\\','/'):digest(p)
                                  for p in SOURCE.rglob('*') if p.is_file()})
    shutil.copytree(INPUT, out/'input-snapshot')
    dump(out/'environment.json', {'time_utc':stamp,'python':platform.python_version(),
        'packages':{p:version(p) for p in ['pyshacl','rdflib','jsonschema']},
        'scope':'real local content validation on supplied synthetic fixtures; NOT ITB or EDC'})
    rows=[]
    for p in sorted((INPUT/'metadata').glob('p*.jsonld')):
        expected = '-valid' in p.name
        doc=read(p)
        for engine in ['JSONSchema','SHACL']:
            record={'input':str(p.relative_to(INPUT)), 'engine':engine, 'expected_conforms':expected,
                    'input_sha256':digest(p)}
            try:
                if engine=='JSONSchema':
                    errors=json_errors(doc,read(INPUT/'schemas/metadata.schema.json'))
                    actual=not errors
                    record['errors']=errors
                    record['rule_sha256']=digest(INPUT/'schemas/metadata.schema.json')
                else:
                    _,_,report,raw,targets=metadata_check(doc)
                    actual=bool(next(report.objects(None,SH.conforms)).toPython()) and bool(targets)
                    record['target_count']=len(targets)
                    record['errors']=[{k:str(report.value(r,v)) for k,v in
                        [('focus_node',SH.focusNode),('path',SH.resultPath),('message',SH.resultMessage),
                         ('constraint',SH.sourceConstraintComponent)]} for r in report.subjects(RDF.type,SH.ValidationResult)]
                    (out/(p.stem+'.shacl.ttl')).write_text(report.serialize(format='turtle'),encoding='utf-8')
                    (out/(p.stem+'.shacl.txt')).write_text(raw,encoding='utf-8')
                    record['rule_sha256']=digest(INPUT/'shapes/resource-core-v1.ttl')
                record.update(actual_conforms=actual, status='PASS' if actual==expected else 'FAIL')
                # Negative verdict must also identify the intended defect.
                marker=next((m for fragment,m in [('missing-rights','rights_holder'),('missing-source','source'),('invalid-access','access_level')] if fragment in p.name),None)
                if marker and marker not in json.dumps(record['errors']): record['status']='FAIL'
            except Exception as e: record.update(status='ERROR', error=repr(e))
            rows.append(record)
    cases=[('recipe-valid.json','recipe',True,set()),('recipe-invalid.json','recipe',False,{'additionalProperties','enum'}),
           ('result-valid-fixture.json','result',True,set()),('result-invalid-leak.json','result',False,{'additionalProperties'}),
           ('grant-active.json','grant',True,set()),('grant-revoked.json','grant',True,set())]
    for filename,kind,expected,keywords in cases:
        p=INPUT/'examples'/filename; rule=INPUT/'schemas'/(kind+'.schema.json')
        errors=json_errors(read(p),read(rule)); actual=not errors
        rows.append({'input':'examples/'+filename,'engine':'JSONSchema','expected_conforms':expected,
          'actual_conforms':actual,'errors':errors,'input_sha256':digest(p),'rule_sha256':digest(rule),
          'status':'PASS' if actual==expected and keywords.issubset({e['keyword'] for e in errors}) else 'FAIL'})
    dump(out/'validation-results.json',rows)
    data=[]
    manifest=read(SOURCE/'data/data-manifest.json')
    for item in manifest['artifacts']:
        p=SOURCE/item['path']
        with p.open(encoding='utf-8-sig',newline='') as f: count=sum(1 for _ in csv.DictReader(f))
        data.append({'path':item['path'],'rows':count,'sha256':digest(p),
          'expected_sha256':item['sha256'],'status':'PASS' if count==item['rows'] and digest(p)==item['sha256'] else 'FAIL'})
    data.append({'check':'independent files','status':'PASS' if data[0]['sha256']!=data[1]['sha256'] else 'FAIL'})
    dump(out/'data-checks.json',data)
    # Preserve actual installed source for the researched call chain.
    import pyshacl.entrypoints, pyshacl.validator, pyshacl.shape
    source_dir=ROOT/'研究源码'; source_dir.mkdir(exist_ok=True)
    for module in [pyshacl.entrypoints,pyshacl.validator,pyshacl.shape]:
        shutil.copy2(inspect.getfile(module),source_dir/(module.__name__+'.py'))
    lines=['# 内容验证实际结果','',f'UTC 执行时间：{stamp}；真实本地 Validator，非 ITB Session。','',
           '|输入|验证器|预期合格|实际合格|用例结论|','|---|---|---|---|---|']
    lines += [f"|{r['input']}|{r['engine']}|{r['expected_conforms']}|{r.get('actual_conforms','ERROR')}|{r['status']}|" for r in rows]
    (out/'结果摘要.md').write_text('\n'.join(lines),encoding='utf-8')
    dump(ROOT/'证据/latest-validation.json',{'directory':out.name})
    print(json.dumps({'evidence':str(out),'checks':len(rows),'pass':sum(r['status']=='PASS' for r in rows),'data':data},ensure_ascii=False))
    return 0 if all(r['status']=='PASS' for r in rows+data) else 1
if __name__=='__main__': sys.exit(main())
