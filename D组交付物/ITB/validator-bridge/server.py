"""Local HTTP adapter for actual JSON Schema validation, not a GITB SOAP service."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import hashlib, json, threading
from datetime import datetime, timezone
from jsonschema import Draft202012Validator, FormatChecker

RULE=Path('/rules/recipe.schema.json')
schema=json.loads(RULE.read_text(encoding='utf-8-sig'))
Draft202012Validator.check_schema(schema)
validator=Draft202012Validator(schema,format_checker=FormatChecker())
audit_lock=threading.Lock()
class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path!='/validate/recipe':self.send_error(404);return
        size=int(self.headers.get('Content-Length','0'))
        if size<1 or size>1048576:self.send_error(413);return
        body=self.rfile.read(size)
        try:
            obj=json.loads(body)
            errors=[{'path':e.json_path,'keyword':e.validator,'message':e.message} for e in validator.iter_errors(obj)]
            result={'conforms':not errors,'errors':errors,'engine':'jsonschema-4.26.0',
                    'input_sha256':hashlib.sha256(body).hexdigest(),'rule_sha256':hashlib.sha256(RULE.read_bytes()).hexdigest()}
            with audit_lock:
                with Path('/evidence/adapter-calls.jsonl').open('a',encoding='utf-8') as f:
                    f.write(json.dumps({'time_utc':datetime.now(timezone.utc).isoformat(),
                        'native_itb_session':self.headers.get('X-TIDE-Session'),
                        'request':obj,'response':result,'scope':'synthetic recipe fixtures only'},ensure_ascii=False)+'\n')
            data=json.dumps(result,ensure_ascii=False).encode()
            self.send_response(200);self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        except (ValueError,TypeError):self.send_error(400,'Malformed JSON')
    def log_message(self,format,*args):print(format%args,flush=True)
ThreadingHTTPServer(('0.0.0.0',8081),Handler).serve_forever()
