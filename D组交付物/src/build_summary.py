from run_validation import ROOT, read, dump, digest
import html

def main():
    v=ROOT/'证据'/read(ROOT/'证据/latest-validation.json')['directory']
    m=ROOT/'证据'/read(ROOT/'证据/latest-mock.json')['directory']
    vals=read(v/'validation-results.json'); mocks=read(m/'mock-results.json')
    def esc(x):return html.escape(str(x))
    def exchange(name):
        if 'grant' in name.lower():return '【样例】S03：B实际签发/审批与授权；A访问入口'
        if 'recipe' in name.lower() or name.startswith('P3_'):return '【样例】S05：C确认规则；A实际P2入口/运行；B授权'
        if 'result' in name.lower() or name.startswith('P4_'):return '【样例】S06：A实际P4/job；C规则/来源；B领取权限'
        return '【样例】S01：C确认模型/规则；A实际待发布产品'
    rows=''.join(f"<tr><td>{esc(r['input'])}</td><td>{r['engine']}</td><td>{r['expected_conforms']}</td><td>{r.get('actual_conforms','ERROR')}</td><td>{r['status']}</td><td>{exchange(r['input'])}</td></tr>" for r in vals)
    def mock_exchange(case):
        if case.startswith(('TC01','D2')):return '【模拟】S02：A实际准入/发布；C规则版本'
        if case.startswith('TC06'):return '【派生负例】S05：A实际P2入口；C规则'
        if case.startswith(('TC07','TC09')):return '【模拟】S08：A/B实际撤权/故障与访问入口'
        return '【模拟】S03：B真实工具签发与审批；A实际访问'
    mockrows=''.join(f"<tr><td>{esc(r['case'])}</td><td>{esc(r['expected'])}</td><td>{esc(r['actual'])}</td><td>{r['status']}</td><td>{mock_exchange(r['case'])}</td></tr>" for r in mocks)
    native=''
    if (ROOT/'证据/ITB最终结果索引.json').exists():
        itb=read(ROOT/'证据/ITB最终结果索引.json')
        native='<h2>ITB 原生实验：8 / 8 成功</h2><p>【真实工具证据 / 样例输入】ITB 1.30.3 / Suite 1.0.1；真实Session，样例内容验证。P3调用D组适配器，尚未接入A/B业务服务。</p><div class="table"><table><tr><th>用例</th><th>原生Session</th><th>报告</th><th>需交换的实际输入</th></tr>'
        for x in itb['reviewed_cases']:
            native+=f'<tr><td>{x["test_case"]}</td><td>{x["native_session"]}</td><td><a href="证据/{itb["directory"]}/{x["native_session"]}.xml">SUCCESS / {x["review"]}</a></td><td>{exchange(x["test_case"])}</td></tr>'
        native+='</table></div>'
    page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>D组第1–4周 · 证据总览</title>
<style>body{{margin:0;background:#f3f6fa;color:#183047;font:16px/1.7 "Microsoft YaHei",sans-serif}}main{{max-width:1160px;margin:auto;padding:48px 24px}}h1{{font-size:34px}}h2{{margin-top:36px}}.sub{{color:#52667a}}.cards{{display:flex;gap:18px;flex-wrap:wrap}}.card{{background:white;padding:22px;border-radius:14px;min-width:220px;flex:1;border-top:4px solid #187f78}}b.num{{font-size:36px;display:block;color:#12645f}}.notice{{background:#fff4d9;border-left:4px solid #bd8423;padding:18px;margin:26px 0}}table{{border-collapse:collapse;width:100%;background:white;font-size:14px}}td,th{{padding:11px;text-align:left;border-bottom:1px solid #dce4ec;overflow-wrap:anywhere}}th{{background:#e4edf4}}a{{color:#126a8b}}.table{{overflow-x:auto}}code{{font-size:13px}}footer{{margin-top:28px;color:#52667a}}</style>
<main><p class="sub">TIDE / D组 / 2026-11-17 / 样例 mock 阶段</p><h1>第1–4周任务 · 证据总览</h1><p>原始样例保留，真实验证器执行，业务授权以明确模拟状态测试。</p>
<div class="cards"><div class="card">真实内容验证<b class="num">{sum(x['status']=='PASS' for x in vals)} / {len(vals)}</b>JSON Schema + SHACL</div><div class="card">进程内 mock 断言<b class="num">{sum(x['status']=='PASS' for x in mocks)} / {len(mocks)}</b>准入、审批、范围与故障</div><div class="card">数据完整性<b class="num">2400 × 2</b>P1/P2 行数及 SHA-256 符合清单</div></div>
<div class="notice"><strong>边界：</strong>这里的PASS仅对应所列检查，不是TC01–TC11整体验收。没有真实VC、EDC交换或Benchmark指标。ITB原生执行状态请查看<a href="ITB/运行状态.md">独立记录</a>。</div>
<h2>哪些地方仍需与其他小组交换实际输入？</h2>
<div class="notice"><strong>全部已通过检查均基于文件夹中的样例或D组模拟状态。</strong>真实的是验证器执行和ITB Session；跨组接收状态仍为待提供/待确认。<a href="05_样例数据与跨组实际输入对照.md">查看S01–S10完整逐项对照</a>。实际输入可以是经确认、真正部署使用的合成数据，不要求企业生产数据，也不要求交换P2原始记录。</div>
<div class="table"><table><tr><th>当前样例/模拟位置</th><th>向哪组交换什么</th><th>收到后验证</th></tr>
<tr><td>S01–S02：metadata、Schema/Shapes、MockAdmission</td><td>C：确认版本与规则；A：实际产品/准入/发布入口</td><td>重验实际版本，检查Asset发布及错误不更新</td></tr>
<tr><td>S03：claims模板、Grant样例、模拟资格/审批</td><td>B：实际签发测试资格、个人映射、owner审批及授权API；A：访问入口</td><td>资格验证、未批准/批准/撤销真实对照</td></tr>
<tr><td>S04：本地P1/P2 CSV与清单</td><td>C：确认数据清单；A：Connector传回P1与原生ID；B：授权</td><td>对实际传回字节算hash；P2保留提供方</td></tr>
<tr><td>S05–S06：Recipe/P4样例、D组HTTP验证适配器</td><td>C：规则/来源；A：实际P2、job与P4；B：执行及领取权限</td><td>真实执行、实际指标、出口不泄漏、复现</td></tr>
<tr><td>S07–S08：OpenAPI占位、模拟撤权/故障</td><td>A/B：地址、鉴权、错误码、旧入口、任务及故障操作</td><td>原生业务流程、旁路、异步、幂等和失效界限</td></tr>
<tr><td>S09–S10：新接入、需求与独立复现未测</td><td>A/B/C与业务角色：独立新配置/资源、实际确认及复现记录</td><td>新增接入先拒绝后成功；实际需求确认</td></tr></table></div>
<h2>交付材料</h2><ul><li><a href="01_第1至4周研究与实验报告.md">研究与实验报告</a></li><li><a href="02_测试矩阵与接口对接.md">TC01–TC11矩阵与接口缺口</a></li><li><a href="03_复现与演示指南.md">复现与演示指南</a></li><li><a href="ITB/TIDE_D_W1W4.zip">8例TDL测试包</a></li><li><a href="证据/{v.name}/validation-results.json">本地内容验证原始结果</a> · <a href="证据/{m.name}/mock-results.json">mock原始结果</a></li></ul>
{native}<h2>内容符合性</h2><p>【样例输入】预期false且实际false为正确拒绝，因此用例为PASS。尚需用其他组确认的实际版本重跑。</p><div class="table"><table><tr><th>输入</th><th>验证器</th><th>预期合格</th><th>实际合格</th><th>结论</th><th>样例标注 / 需交换实际输入</th></tr>{rows}</table></div>
<h2>Mock行为检查</h2><p>【模拟行为】状态与错误码为D组测试替身约定，不冒充A/B的实际响应。</p><div class="table"><table><tr><th>用例</th><th>预期</th><th>实际</th><th>结论</th><th>模拟标注 / 需交换实际输入</th></tr>{mockrows}</table></div>
<h2>失败记录保留</h2><p>首轮SHACL报告读取适配错误：13/20通过、7项ERROR；修复后20/20通过。原失败目录仍保留，不将基础设施或代码错误解释为正确拒绝。</p><footer>本页为静态证据索引，不是业务Portal。源报告与代码在同目录，可离线查看。</footer></main></html>'''
    (ROOT/'交付物总览.html').write_text(page,encoding='utf-8')
    inventory={str(p.relative_to(ROOT)).replace('\\','/'):digest(p) for p in ROOT.rglob('*') if p.is_file()
               and '.venv' not in p.parts and '__pycache__' not in p.parts and p.name!='交付文件hash.json'}
    dump(ROOT/'交付文件hash.json',inventory)
    print('Created evidence overview and file hashes:',len(inventory))
if __name__=='__main__':main()
