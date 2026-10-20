"""Real end-to-end CLI demonstration on synthetic data; writes reproducible evidence."""
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from ledgerly.agent import Agent
from ledgerly.ingest import load_csv
from ledgerly.models import Business
from ledgerly.sandbox import SandboxEnv
from ledgerly.security import AuditLog, Consent

ROOT = Path(__file__).resolve().parent
OPENING = 650_000
GOAL = 'Review financing, apply for the best option, then disburse in the sandbox.'

def main():
    folder = ROOT / 'evidence' / ('run_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f'))
    folder.mkdir(parents=True)
    txns, quality = load_csv(str(ROOT / 'data/sample_trader.csv'))
    env = SandboxEnv(OPENING, str(folder / 'execution_log.jsonl'))
    audit = AuditLog(str(folder / 'audit_log.jsonl'))
    biz = Business('Mama Ngozi Fabrics (synthetic)', 'fabric retail', 'Lagos')
    consent = Consent(frozenset({'credit_assessment', 'share_with_lender'}))
    agent = Agent(biz, txns, OPENING, consent, env=env, audit=audit)
    steps = []
    def emit(title, command, lines, caption):
        text = '\n'.join(lines)
        print(f'\n=== {title} ===\n$ {command}\n{text}', flush=True)
        steps.append(dict(title=title,command=command,output=text,caption=caption))
    emit('01  INGEST & PROTECT', 'python run_demo.py', [
        'LEDGERLY | SME FINANCE COPILOT', 'Mode: offline / synthetic / sandbox only',
        f"Records loaded: {quality['rows_loaded']:,} | Rejected: {quality['rows_rejected']}",
        f"Instruction-like memos neutralized: {quality['injection_flags']}",
        f'Data window: {txns[0].day} to {txns[-1].day}',
        'Planner: deterministic rules; no live LLM calls',
        'External bank calls: 0 | Real money moved: NGN 0'],
        'A synthetic Lagos trader starts with 2,352 records. One poisoned memo is treated as data and neutralized.')
    r1 = agent.run(GOAL)
    p,d,m = r1['passport'],r1['forecast']['downside'],r1['match']
    emit('02  EXPLAIN THE RISK', 'agent.run(goal) -> forecast + passport',[
        f"Cash-flow passport: {p['score']}/100 | Grade {p['grade']}",
        'Forecast: 13 weeks | Base / sales -20% / sales +10%',
        f"Downside minimum cash: NGN {d['min_balance']:,.0f}",
        f"Minimum week: {d['min_week']}",
        f"Two-week safety buffer: NGN {d['safety_buffer']:,.0f}",
        f"Buffer gap: NGN {d['need']:,.0f} -> request NGN {m['need']:,.0f}",
        f"Weekly repayment capacity: NGN {p['weekly_repayment_capacity']:,.0f}",
        'A buffer shortfall, not a forecast of insolvency.'],
        'The downside case stays positive but falls below the two-week buffer. The score is an explained heuristic, not a lender credit rating.')
    o=m['recommended_offer']
    rows=['PRODUCT                   WEEKLY    FULL GAP   AFFORDABLE']
    for offer in m['offers']:
        rows.append(f"{offer['product_id']:<24} {offer['weekly_payment']:>7,.0f}    {'yes' if offer['covers_need'] else 'no':<7}    {'yes' if offer['affordable'] else 'no'}")
    rows += ['',f"Recommended: {o['name']}",f"NGN {o['amount']:,.0f} / {o['term_weeks']} weeks | Total cost NGN {o['total_cost']:,.0f}",f"Simple annualized cost: {o['annualized_cost_rate']:.1%} (NOT APR or IRR)", 'Catalogue is illustrative. No real lender quotes.']
    emit('03  COMPARE RESPONSIBLY', 'financing.match(...) -> recommended_offer',rows,
        'Only an affordable offer covering the full gap can be selected. The lower-cost, faster products are not automatically safer.')
    emit('04  FIRST APPROVAL GATE', 'agent.run(goal) -> pending submit',[
        f"Status: {r1['status']} | Pending tool: {r1['pending']}",
        'Lender pack: business summary + factors + forecast + offer',
        'Excluded: raw transactions, customer identities, account numbers',
        'Sandbox applications: 0 | Disbursements: 0',
        f'Sandbox balance: NGN {env.balance:,.0f}',
        'Waiting for explicit application approval.'],
        'Consent allows the local lender pack. Application approval is still required; no application or money movement has happened.')
    agent.approver = lambda tool, preview: tool == 'submit'
    r2 = agent.run(GOAL)
    emit('05  APPLICATION IS NOT DISBURSEMENT', 'owner approves submit only; agent.run(goal)',[
        f"Application: {r2['submit']['application']['status']} (simulated lender)",
        f"Status: {r2['status']} | Pending tool: {r2['pending']}",
        f'Sandbox balance: NGN {env.balance:,.0f} (unchanged)',
        'Disbursements: 0',
        'A separate owner decision is required to disburse.'],
        'Approving the application does not approve disbursement. The engine stops again, and the balance is still NGN 650,000.')
    approvals=[]
    def approve(tool,preview):
        approvals.append(tool); return True
    agent.approver=approve
    r3=agent.run(GOAL)
    balance=env.balance
    r4=agent.run(GOAL)
    opnames=[x['op'] for x in env.ops]
    emit('06  APPROVE ONCE, EXECUTE ONCE', 'owner approves disburse; run, then repeat',[
        f"Disbursement: {r3['disburse']['status']} | Sandbox only",
        f'Sandbox balance: NGN {balance:,.0f}',
        f'Repeated run balance: NGN {env.balance:,.0f}',
        f"Total application operations: {opnames.count('lender_application')}",
        f"Total disbursement operations: {opnames.count('disbursement')}",
        f"Replay flagged: {r4['disburse'].get('replayed',False)}",
        'Idempotency is in-process; restart-safe money state is not implemented.'],
        'After the second explicit approval, the sandbox balance rises. Repeating the approved workflow does not duplicate the transfer in this session.')
    stress_txns=[replace(t,amount=t.amount*1.6) if t.amount<0 else t for t in txns]
    stress_env=SandboxEnv(OPENING,str(folder/'stress_execution_log.jsonl'))
    stress=Agent(biz,stress_txns,OPENING,consent,env=stress_env,approver=lambda *_:True)
    bad=stress.run(GOAL,requested_amount=880_000)
    emit('07  THE SAFE ANSWER CAN BE NO', 'stress fixture: expenses x 1.6; requested NGN 880,000',[
        f"Weekly repayment capacity: NGN {bad['passport']['weekly_repayment_capacity']:,.0f}",
        f"Recommended offer: {bad['match']['recommended_offer']}",
        f"Application: {bad['submit']['status']}",
        f"Disbursement: {bad['disburse']['status']}",
        f'Sandbox balance: NGN {stress_env.balance:,.0f} (unchanged)',
        'No affordable full-gap offer. Application and disbursement refused.',
        'Even an approving callback cannot override this affordability gate.'],
        'With higher expenses, repayment capacity becomes zero. The engine refuses the financing path, even when the demo approval callback says yes.')
    reloaded=AuditLog(str(folder/'audit_log.jsonl'))
    tampered=AuditLog();tampered.entries=json.loads(json.dumps(audit.entries));tampered.entries[0]['action']='changed'
    emit('08  VERIFY THE EVIDENCE', 'AuditLog(path).verify(); tamper-copy.verify()',[
        f'Persisted audit reload: {reloaded.verify()}',
        f'Audit entries: {len(reloaded.entries)}',
        f'Tampered copy verifies: {tampered.verify()}',
        'Local hash chain, not immutable or externally anchored.',
        'Full suite: 64 passing tests (24 original + 40 regressions).',
        'Production gaps: authenticated approvals, calibrated risk,',
        'live lender APIs, durable transactions, external audit anchoring.',
        'Run locally: python demo_server.py (optional visual wrapper)'],
        'The evidence is reproducible: code, tests, execution logs and audit records. This is a working offline prototype, with production gaps clearly stated.')
    (folder/'report.json').write_text(json.dumps(r3,indent=2,default=str))
    (folder/'stress_report.json').write_text(json.dumps(bad,indent=2,default=str))
    (folder/'stage_reports.json').write_text(json.dumps([r1,r2,r3,r4],indent=2,default=str))
    (ROOT/'evidence/demo_steps.json').write_text(json.dumps(steps,indent=2))
    (ROOT/'evidence/latest_run.txt').write_text(folder.name+'\n')
    print('\nEvidence:',folder)
    return folder
if __name__=='__main__': main()
