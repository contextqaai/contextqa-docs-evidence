class DCLogic{constructor(p){this.props=p||{};this.state={};}setState(p){Object.assign(this.state,p);window.__render();}}


class Component extends DCLogic {
  constructor(props) {
    super(props);
    this.state = { i: location.hash === "#run-and-review" ? 2 : 0, done: false, hint: false };
  }
  renderVals() {
    var steps = [
      { ch: 0, title: 'Open a test case', body: 'Each test case is one user flow. This one checks the login of a valid user.', hl: 466, ht: 22, tl: 512, tt: 14 },
      { ch: 0, title: 'Write steps in plain English', body: 'Each step is one sentence. ContextQA finds the element and does the action.', hl: 1038, ht: 158, tl: 716, tt: 210 },
      { ch: 1, title: 'Run the test', body: 'Click Run. ContextQA runs the steps in the selected environment and browser.', hl: 1012, ht: 16, tl: 668, tt: 70 },
      { ch: 1, title: 'Review the result', body: 'All 5 steps passed. Open the logs and the trace to see the evidence for each step.', hl: 1030, ht: 414, tl: 700, tt: 478 }
    ];
    var i = this.state.i, done = this.state.done, s = steps[i], last = steps.length - 1;
    var go = (n) => this.setState({ i: n, done: false, hint: false });
    var ran = i === last;
    return {
      step: s,
      stepNumber: i + 1,
      progress: (done ? 100 : ((i + 1) / steps.length) * 100) + '%',
      chapterLabel: s.ch === 0 ? 'CHAPTER 1 · AUTHOR A TEST' : 'CHAPTER 2 · RUN AND REVIEW',
      showGuide: !done,
      showResult: ran,
      done: done,
      hint: this.state.hint,
      isFirst: i === 0,
      backColor: i === 0 ? '#B4B6CC' : '#30355F',
      backOpacity: i === 0 ? 0.45 : 1,
      nextLabel: i === last ? 'Finish' : 'Next',
      badgeBg: ran ? '#EAF4EC' : '#EEEFFB',
      badgeFg: ran ? '#137333' : '#5457C9',
      row2Border: i === 1 ? '#7478F0' : '#EEEFF6',
      row2Bg: i === 1 ? '#F7F7FE' : '#FFFFFF',
      ch1Bg: s.ch === 0 ? '#EEEFFB' : 'transparent',
      ch1Fg: s.ch === 0 ? '#5457C9' : '#30355F',
      ch2Bg: s.ch === 1 ? '#EEEFFB' : 'transparent',
      ch2Fg: s.ch === 1 ? '#5457C9' : '#30355F',
      ch1Current: s.ch === 0 ? 'step' : 'false',
      ch2Current: s.ch === 1 ? 'step' : 'false',
      ch1Done: s.ch === 1,
      dots: steps.map((x, k) => ({ w: k === i ? 20 : 6, bg: k <= i ? '#5457C9' : '#DCDDF3' })),
      next: (e) => { if (e && e.stopPropagation) e.stopPropagation(); if (i === last) { this.setState({ done: true, hint: false }); } else { go(i + 1); } },
      back: (e) => { if (e && e.stopPropagation) e.stopPropagation(); if (i > 0) go(i - 1); },
      restart: () => go(0),
      goCh1: () => go(0),
      goCh2: () => go(2),
      misclick: () => { if (!done) this.setState({ hint: true }); }
    };
  }
}
const comp = new Component({});
let v = {};
const root = document.getElementById('app');
const tpl = (v) => `

<div class="ref-1">

  <header class="ref-2">
    <a class="ref-3" href="demo-hub.html">Context<span class="ref-4">QA</span></a>
    <div class="ref-5">
      <div class="ref-6">${v.chapterLabel}</div>
      <div class="ref-7">Explore ContextQA platform capabilities</div>
    </div>
    <div class="ref-8">
      <button class="ref-9" type="button" data-action="restart">
        <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/></svg>Restart</button>
      <a class="ref-10" href="demo-hub.html" aria-label="Close demo">
        <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
      </a>
    </div>
  </header>

  <div class="ref-11" role="progressbar" aria-label="Demo progress" aria-valuemin="0" aria-valuemax="4" aria-valuenow="${v.stepNumber}">
    <div class="ref-12"></div>
  </div>

  <div class="ref-13">
    <div class="ref-14">
      <span class="ref-15"></span><span class="ref-15"></span><span class="ref-15"></span>
      <div class="ref-16">app.contextqa.com/test-cases</div>
    </div>

    <div class="ref-17" data-action="misclick">
      <div class="ref-18">
        <div class="ref-19">Context<span class="ref-4">QA</span></div>
        <div class="ref-20">Test cases</div>
        <div class="ref-21">Test suites</div>
        <div class="ref-22">Test plans</div>
        <div class="ref-23">Environments</div>
        <div class="ref-24">Results</div>
      </div>

      <div class="ref-25">Test cases / Authentication</div>
      <div class="ref-26">Login with valid user</div>
      <div class="ref-27">
        <svg aria-hidden="true" width="12" height="12" viewBox="0 0 24 24" fill="#FFFFFF"><path d="M7 4l13 8-13 8z"/></svg>Run</div>

      <div class="ref-28"><span class="ref-29">1</span>Navigate to the login page</div>
      <div class="ref-30"><span class="ref-29">2</span>Enter “demo.user” in the Username field</div>
      <div class="ref-31"><span class="ref-29">3</span>Enter the password in the Password field</div>
      <div class="ref-32"><span class="ref-29">4</span>Click the Login button</div>
      <div class="ref-33"><span class="ref-29">5</span>Verify that the Dashboard is visible</div>

      ${v.showResult ? `
        <div class="ref-34">
          <div class="ref-35"><svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#137333" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l5 5L20 7"/></svg>Passed · 5 of 5 steps</div>
          <div class="ref-36"><span>View logs</span><span>View trace</span></div>
        </div>
      ` : ''}

      ${v.showGuide ? `
        <button class="ref-37" type="button" aria-label="${v.step.title}" data-action="next">
          <span class="ref-38 hs-ring"></span>
          <span class="ref-39"></span>
        </button>

        <div class="ref-40 tip" role="dialog" aria-label="${v.step.title}">
          <div class="ref-41">STEP ${v.stepNumber} OF 4</div>
          <div class="ref-42">
            <div class="ref-43">${v.step.title}</div>
            <div class="ref-44">${v.step.body}</div>
          </div>
          <div class="ref-45">
            <button class="ref-46" type="button" data-action="back" ${v.isFirst ? 'disabled' : ''}>Back</button>
            <button class="ref-47" type="button" data-action="next">${v.nextLabel}</button>
          </div>
        </div>
      ` : ''}
    </div>
  </div>

  <nav class="ref-48" aria-label="Demo navigation">
    <div class="ref-49">
      <button class="ref-50" type="button" data-action="goCh1" aria-current="${v.ch1Current}">
        ${v.ch1Done ? `<svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#137333" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l5 5L20 7"/></svg>` : ''}1 · Author a test</button>
      <button class="ref-51" type="button" data-action="goCh2" aria-current="${v.ch2Current}">2 · Run and review</button>
    </div>
    <div class="ref-52">
      ${v.hint ? `<span class="ref-53" role="status">Click the pulsing dot to continue</span>` : ''}
      <span class="ref-54">Step ${v.stepNumber} of 4</span>
      <div class="ref-55" aria-hidden="true">
        ${v.dots.map(d => `<span class="ref-56 ${d.w===20?"dot-active":"dot-idle"} ${d.bg==="#5457C9"?"dot-seen":"dot-pending"}"></span>`).join('')}
      </div>
    </div>
    <div class="ref-57">
      <button class="ref-58" type="button" data-action="back" ${v.isFirst ? 'disabled' : ''}>Back</button>
      <button class="ref-59" type="button" data-action="next">${v.nextLabel}</button>
    </div>
  </nav>

  <div class="ref-60">Powered by <a class="ref-4" href="https://contextqa.com">ContextQA</a></div>

  ${v.done ? `
    <div class="ref-61">
      <div class="ref-62" role="dialog" aria-label="Demo complete">
        <div class="ref-6">DEMO COMPLETE</div>
        <h2 class="ref-63">You authored and ran a test.<br><em class="ref-64">Now see it on your app.</em></h2>
        <ul class="ref-65">
          <li class="ref-66"><span class="ref-67" aria-hidden="true"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#5457C9" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l5 5L20 7"/></svg></span>Steps written in plain English</li>
          <li class="ref-66"><span class="ref-67" aria-hidden="true"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#5457C9" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l5 5L20 7"/></svg></span>One click to run</li>
          <li class="ref-66"><span class="ref-67" aria-hidden="true"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#5457C9" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l5 5L20 7"/></svg></span>Results with logs and traces as evidence</li>
        </ul>
        <div class="ref-68">
          <a class="ref-69" href="https://contextqa.com/book-a-demo?utm_source=demo&amp;utm_medium=interactive&amp;utm_campaign=platform-capabilities">Book a demo</a>
          <a class="ref-70" href="demo-hub.html">Explore more demos</a>
          <button class="ref-71" type="button" data-action="restart">Restart</button>
        </div>
      </div>
    </div>
  ` : ''}
</div>
`;
window.__render = () => { v = comp.renderVals(); root.dataset.scene = String(v.stepNumber); root.innerHTML = tpl(v); };
root.addEventListener('click', (e) => {
  const el = e.target.closest('[data-action]');
  if (!el || el.disabled) return;
  const fn = v[el.dataset.action];
  if (typeof fn === 'function') fn(e);
});
window.__render();
