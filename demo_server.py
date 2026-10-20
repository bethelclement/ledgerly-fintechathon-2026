"""Local-only visual wrapper over the real Ledgerly engine. Synthetic demo, no external I/O."""
import json
from dataclasses import asdict, replace
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from ledgerly.agent import Agent
from ledgerly.ingest import load_csv
from ledgerly.models import Business
from ledgerly.security import AuditLog, Consent
from ledgerly.sandbox import SandboxEnv

ROOT = Path(__file__).resolve().parent
OPENING = 650_000
GOAL = "Review financing, apply for the best option, then disburse in the sandbox."

class Session:
    def __init__(self):
        self.reset()

    def reset(self, stress=False):
        self.stress, self.approved = stress, set()
        txns, self.quality = load_csv(str(ROOT / 'data/sample_trader.csv'))
        if stress:
            txns = [replace(t, amount=t.amount * 1.6) if t.amount < 0 else t for t in txns]
        self.txns = txns
        self.folder = ROOT / 'evidence' / ('browser_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f'))
        self.folder.mkdir(parents=True)
        self.env = SandboxEnv(OPENING, str(self.folder / 'execution_log.jsonl'))
        self.audit = AuditLog(str(self.folder / 'audit_log.jsonl'))
        self.agent = Agent(Business('Mama Ngozi Fabrics (synthetic)', 'Fabric retail', 'Lagos'), txns, OPENING,
            Consent(frozenset({'credit_assessment', 'share_with_lender'})), env=self.env, audit=self.audit,
            approver=lambda tool, preview: tool in self.approved)
        self.report = None

    def run(self, action):
        if action in ('reset', 'stress'):
            self.reset(action == 'stress')
        elif action == 'approve_application':
            if not self.report or self.report['pending'] != 'submit':
                raise ValueError('No application is awaiting approval')
            self.approved.add('submit')
        elif action == 'approve_disbursement':
            if not self.report or self.report['pending'] != 'disburse':
                raise ValueError('No disbursement is awaiting approval')
            self.approved.add('disburse')
        elif action not in ('analyze', 'replay'):
            raise ValueError('Unknown action')
        self.report = self.agent.run(GOAL)
        state = self.state()
        (self.folder / 'report.json').write_text(json.dumps(state, indent=2, default=str))
        return state

    def state(self):
        return {'report': self.report, 'quality': self.quality, 'stress': self.stress,
            'balance': self.env.balance, 'ops': self.env.ops, 'audit_entries': len(self.audit.entries),
            'audit_valid': self.audit.verify(), 'approved': sorted(self.approved),
            'data_start': str(self.txns[0].day), 'data_end': str(self.txns[-1].day),
            'forecast_points': {k: [asdict(w) for w in v['weeks']] for k,v in self.agent.ctx.get('scen',{}).items()},
            'evidence_folder': self.folder.name}

session = Session()
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/state':
            return self.respond(session.state())
        if self.path not in ('/', '/index.html'):
            self.send_error(404); return
        body = (ROOT / 'web/index.html').read_bytes()
        self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        if self.path != '/api/action': self.send_error(404); return
        # Browser demo is localhost only. Reject cross-origin requests; no deployment claim.
        origin = self.headers.get('Origin')
        if origin and origin not in ('http://127.0.0.1:8765', 'http://localhost:8765'):
            self.send_error(403); return
        try:
            n = int(self.headers.get('Content-Length', '0'))
            if n > 2000: raise ValueError('Request too large')
            data = json.loads(self.rfile.read(n))
            self.respond(session.run(data['action']))
        except (ValueError, KeyError) as e: self.respond({'error':str(e)}, 400)
    def respond(self, obj, code=200):
        self.send_response(code); self.send_header('Content-Type','application/json'); self.send_header('Cache-Control','no-store'); self.end_headers()
        self.wfile.write(json.dumps(obj, default=str).encode())

if __name__ == '__main__':
    print('Ledgerly synthetic local demo: http://127.0.0.1:8765', flush=True)
    HTTPServer(('127.0.0.1', 8765), Handler).serve_forever()
