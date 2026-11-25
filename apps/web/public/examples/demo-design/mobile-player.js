class DCLogic{constructor(p){this.props=p||{};this.state={};}setState(p){Object.assign(this.state,p);window.__render();}}


class Component extends DCLogic {
  constructor(props) {
    super(props);
    this.state = { i: location.hash === "#run-and-review" ? 2 : 0, done: false };
  }
  renderVals() {
    var steps = [
      { ch: 0, title: 'Open a test case', body: 'Each test case is one user flow. This one checks the login of a valid user.', hl: 174, ht: 4 },
      { ch: 0, title: 'Write steps in plain English', body: 'Each step is one sentence. ContextQA finds the element and does the action.', hl: 298, ht: 104 },
      { ch: 1, title: 'Run the test', body: 'Tap Run. ContextQA runs the steps in the selected environment and browser.', hl: 284, ht: 7 },
      { ch: 1, title: 'Review the result', body: 'All 5 steps passed. Open the logs and the trace to see the evidence for each step.', hl: 298, ht: 294 }
    ];
    var i = this.state.i, done = this.state.done, s = steps[i], last = steps.length - 1, ran = i === last;
    var go = (n) => this.setState({ i: n, done: false });
    return {
      step: s,
      stepNumber: i + 1,
      progress: (done ? 100 : ((i + 1) / steps.length) * 100) + '%',
      chapterLabel: s.ch === 0 ? 'CHAPTER 1 · AUTHOR' : 'CHAPTER 2 · RUN AND REVIEW',
      showGuide: !done,
      showResult: ran,
      done: done,
      isFirst: i === 0,
      backOpacity: i === 0 ? 0.45 : 1,
      nextLabel: i === last ? 'Finish' : 'Next',
      badgeBg: ran ? '#EAF4EC' : '#EEEFFB',
      badgeFg: ran ? '#137333' : '#5457C9',
      row2Border: i === 1 ? '#7478F0' : '#EEEFF6',
      row2Bg: i === 1 ? '#F7F7FE' : '#FFFFFF',
      dots: steps.map((x, k) => ({ w: k === i ? 20 : 6, bg: k <= i ? '#5457C9' : '#DCDDF3' })),
      next: () => { if (i === last) { this.setState({ done: true }); } else { go(i + 1); } },
      back: () => { if (i > 0) go(i - 1); },
      restart: () => go(0)
    };
  }
}
const comp = new Component({});
let v = {};
const root = document.getElementById('app');
const tpl = (v) => `

<div class="ref-1">

  <header class="ref-2">
    <div class="ref-3">
      <span class="ref-4">${v.chapterLabel}</span>
      <span class="ref-5">Platform capabilities</span>
    </div>
    <a class="ref-6" href="demo-hub.html" aria-label="Close demo">
      <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
    </a>
  </header>
  <div class="ref-7" role="progressbar" aria-label="Demo progress" aria-valuemin="0" aria-valuemax="4" aria-valuenow="${v.stepNumber}">
    <div class="ref-8"></div>
  </div>

  <div class="ref-9">
    <div class="ref-10">
      <div class="ref-11">Login with valid user</div>
      <div class="ref-12">Run</div>

      <div class="ref-13"><span class="ref-14">1</span>Navigate to the login page</div>
      <div class="ref-15"><span class="ref-14">2</span>Enter “demo.user” in Username</div>
      <div class="ref-16"><span class="ref-14">3</span>Enter the password</div>
      <div class="ref-17"><span class="ref-14">4</span>Click the Login button</div>
      <div class="ref-18"><span class="ref-14">5</span>Verify the Dashboard is visible</div>

      ${v.showResult ? `
        <div class="ref-19">
          <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#137333" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l5 5L20 7"/></svg>Passed · 5 of 5 steps</div>
      ` : ''}

      ${v.showGuide ? `
        <button class="ref-20" type="button" aria-label="${v.step.title}" data-action="next">
          <span class="ref-21 hs-ring"></span>
          <span class="ref-22"></span>
        </button>
      ` : ''}
    </div>
  </div>

  ${v.showGuide ? `
    <section class="ref-23" role="dialog" aria-label="${v.step.title}">
      <div class="ref-24" aria-hidden="true"></div>
      <div class="ref-25">
        <span class="ref-26">STEP ${v.stepNumber} OF 4</span>
        <div class="ref-27" aria-hidden="true">
          ${v.dots.map(d => `<span class="ref-28 ${d.w===20?"dot-active":"dot-idle"} ${d.bg==="#5457C9"?"dot-seen":"dot-pending"}"></span>`).join('')}
        </div>
      </div>
      <div class="ref-29">${v.step.title}</div>
      <div class="ref-30">${v.step.body}</div>
      <div class="ref-31">
        <button class="ref-32" type="button" data-action="back" ${v.isFirst ? 'disabled' : ''}>Back</button>
        <button class="ref-33" type="button" data-action="next">${v.nextLabel}</button>
      </div>
    </section>
  ` : ''}

  ${v.done ? `
    <section class="ref-34" role="dialog" aria-label="Demo complete">
      <div class="ref-35">
        <div class="ref-26">DEMO COMPLETE</div>
        <h2 class="ref-36">You authored and ran a test.<br><em class="ref-37">Now see it on your app.</em></h2>
        <a class="ref-38" href="https://contextqa.com/book-a-demo?utm_source=demo&amp;utm_medium=interactive&amp;utm_campaign=platform-capabilities">Book a demo</a>
        <a class="ref-39" href="demo-hub.html">Explore more demos</a>
        <button class="ref-40" type="button" data-action="restart">Restart</button>
      </div>
    </section>
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
