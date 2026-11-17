"""Build a native TDL suite from unchanged supplied fixtures. Execution is separate."""
from run_validation import ROOT, INPUT, digest
from pathlib import Path
import shutil, zipfile, json
import xml.etree.ElementTree as ET

def main():
    suite=ROOT/'ITB/suite'; (suite/'testCases').mkdir(parents=True,exist_ok=True)
    for folder in ['metadata','schemas','shapes','examples']:
        shutil.copytree(INPUT/folder,suite/'resources'/folder,dirs_exist_ok=True)
    head='xmlns="http://www.gitb.com/tdl/v1/" xmlns:gitb="http://www.gitb.com/core/v1/"'
    cases=[]
    samples=[('P1_VALID','metadata/p1-valid.jsonld','metadata',False),
             ('P1_MISSING_RIGHTS','metadata/p1-missing-rights.jsonld','metadata',True),
             ('P1_MISSING_SOURCE','metadata/p1-missing-source.jsonld','metadata',True),
             ('P1_BAD_ACCESS','metadata/p1-invalid-access.jsonld','metadata',True),
             ('P3_VALID','examples/recipe-valid.json','recipe',False),
             ('P3_INVALID','examples/recipe-invalid.json','recipe',True),
             ('P4_VALID_FIXTURE','examples/result-valid-fixture.json','result',False),
             ('P4_LEAK','examples/result-invalid-leak.json','result',True)]
    for case,path,kind,negative in samples:
        imports=f'<artifact name="data">resources/{path}</artifact><artifact name="schema">resources/schemas/{kind}.schema.json</artifact>'
        steps=f'<verify id="jsonCheck" handler="JsonValidator" invert="{str(negative).lower()}" desc="Fixture JSON Schema validation"><input name="json">$data</input><input name="schema">$schema</input></verify>'
        if kind=='recipe':
            expected={'$schema':'https://json-schema.org/draft/2020-12/schema','type':'object',
                'required':['conforms','errors','engine','input_sha256','rule_sha256'],
                'properties':{'conforms':{'const':not negative},'engine':{'const':'jsonschema-4.26.0'},
                              'errors':{'type':'array'},
                              'input_sha256':{'const':digest(INPUT/path)},
                              'rule_sha256':{'const':digest(INPUT/'schemas/recipe.schema.json')}}}
            if negative:
                expected['properties']['errors']['allOf']=[{'contains':{'type':'object','required':['keyword','path'],
                    'properties':{'keyword':{'const':'enum'},'path':{'const':'$.smoothing_window'}}}},
                    {'contains':{'type':'object','required':['keyword','message'],
                     'properties':{'keyword':{'const':'additionalProperties'},'message':{'pattern':'script'}}}}]
            else:expected['properties']['errors']['maxItems']=0
            (suite/'resources'/(case+'-response.schema.json')).write_text(json.dumps(expected),encoding='utf-8')
            imports+=f'<artifact name="responseSchema">resources/{case}-response.schema.json</artifact>'
            steps='''<assign to="headers{Content-Type}">"application/json"</assign>
<assign to="headers{X-TIDE-Session}">$SESSION{sessionId}</assign>
<send id="validateHttp" from="TestDriver" to="TIDEProvider" handler="HttpMessagingV2" desc="Actual Python JSON Schema adapter">
<input name="uri">"http://validator-bridge:8081/validate/recipe"</input><input name="method">"POST"</input>
<input name="body">$data</input><input name="headers">$headers</input></send>
<verify handler="ExpressionValidator" desc="Require successful validator execution">
<input name="expression">number($validateHttp{response}{status}) = 200</input></verify>
<verify handler="JsonValidator" desc="Assert exact conforms and violation reasons">
<input name="json">$validateHttp{response}{body}</input><input name="schema">$responseSchema</input></verify>'''
        if kind=='metadata':
            imports+='<artifact name="shapes">resources/shapes/resource-core-v1.ttl</artifact>'
            steps+=f'''<assign to="shapeFile{{content}}">$shapes</assign><assign to="shapeFile{{contentType}}">"text/turtle"</assign>
<verify id="shaclCheck" handler="ShaclValidator" invert="{str(negative).lower()}" desc="Fixture SHACL validation">
<input name="model">$data</input><input name="contentType">"application/ld+json"</input><input name="shapes">$shapeFile</input><input name="showReport">true()</input></verify>'''
        xml=f'''<?xml version="1.0" encoding="UTF-8"?>
<testcase id="{case}" {head}><metadata><gitb:name>{case}</gitb:name><gitb:version>1.0.1</gitb:version><gitb:description>Supplied synthetic fixture only. No real identity or transfer. Negative reports require reason review.</gitb:description></metadata>
<imports>{imports}</imports><actors><gitb:actor id="TIDEProvider" name="TIDEProvider" role="SUT"/>{'<gitb:actor id="TestDriver" name="TestDriver" role="SIMULATED"/>' if kind=='recipe' else ''}</actors><steps stopOnError="true">{steps}</steps></testcase>'''
        ET.fromstring(xml)
        (suite/'testCases'/(case+'.xml')).write_text(xml,encoding='utf-8');cases.append(case)
    xml=f'''<?xml version="1.0" encoding="UTF-8"?>
<testsuite id="TIDE_D_W1W4" {head}><metadata><gitb:name>TIDE D Week 1-4 Fixture Validation</gitb:name><gitb:description>Content validation of synthetic fixtures; not integrated acceptance.</gitb:description><gitb:version>1.0.1</gitb:version></metadata><actors><gitb:actor id="TIDEProvider"><gitb:name>TIDEProvider</gitb:name><gitb:desc>Fixture resource producer</gitb:desc></gitb:actor><gitb:actor id="TestDriver"><gitb:name>TestDriver</gitb:name><gitb:desc>ITB simulated HTTP caller</gitb:desc></gitb:actor></actors>{''.join(f'<testcase id="{c}"/>' for c in cases)}</testsuite>'''
    ET.fromstring(xml);(suite/'testSuite.xml').write_text(xml,encoding='utf-8')
    with zipfile.ZipFile(ROOT/'ITB/TIDE_D_W1W4.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in suite.rglob('*'):
            if p.is_file():z.write(p,p.relative_to(suite))
    print('Built 8 test cases; XML well-formed. Native import/runtime validation remains separate.')
if __name__=='__main__': main()
