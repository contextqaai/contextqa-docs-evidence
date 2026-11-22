import { useEffect, useRef, useState } from 'react';
import { Clock, Play, GitBranch } from 'lucide-react';
import { request } from './api';
import { Empty, Heading } from './components';

type Config = {
  instructions: string;
  trigger: 'github' | 'daily';
  timezone: string;
  local_time: string;
  page_limit: number;
};
type Workflow = {
  version: number;
  active: boolean;
  config: Config;
  live_cursor: string | null;
};
type Run = {
  id: string;
  mode: string;
  status: string;
  workflow_version: number;
  stage: number;
  reason: string | null;
};
type Data = { workflow: Workflow | null; runs: Run[] };
type Detail = Run & {
  config: Config;
  receipts: {
    stage: number;
    completed_at: string;
    receipt: {
      name: string;
      pages?: number;
      candidate_paths?: string[];
      instructions?: string;
      next_action?: string;
    };
  }[];
};
const initial: Config = {
  instructions:
    'Review source changes against the existing documentation and identify guides that need new evidence.',
  trigger: 'github',
  timezone: 'UTC',
  local_time: '09:00',
  page_limit: 50,
};

export function Workflows({ prefix, role }: { prefix: string; role: string }) {
  const [data, setData] = useState<Data | null>(null),
    [form, setForm] = useState<Config>(initial),
    [backlog, setBacklog] = useState('skip');
  const [selected, setSelected] = useState(''),
    [detail, setDetail] = useState<Detail | null>(null);
  const [error, setError] = useState(''),
    [notice, setNotice] = useState(''),
    [busy, setBusy] = useState(false),
    [edited, setEdited] = useState(false);
  const base = prefix + '/workflow',
    retryKey = useRef(''),
    alive = useRef(true),
    timer = useRef(0);
  const editable = role === 'admin' || role === 'editor';
  useEffect(() => {
    alive.current = true;
    let cancelled = false;
    if (editable)
      request(base)
        .then((d: Data) => {
          if (!cancelled) {
            setData(d);
            setForm(d.workflow?.config || initial);
          }
        })
        .catch((e) => {
          if (!cancelled) setError(e.message);
        });
    return () => {
      cancelled = true;
      alive.current = false;
    };
  }, [base, editable]);
  useEffect(() => {
    if (!selected) return;
    let active = true;
    async function poll() {
      try {
        const value = await request(base + '/runs/' + selected);
        if (!active) return;
        setDetail(value);
        if (['queued', 'running'].includes(value.status)) {
          timer.current = window.setTimeout(poll, 1000);
        } else {
          const next = await request(base);
          if (active) setData(next);
        }
      } catch (e) {
        if (active) setError((e as Error).message);
      }
    }
    void poll();
    return () => {
      active = false;
      clearTimeout(timer.current);
    };
  }, [base, selected]);
  function field<K extends keyof Config>(key: K, value: Config[K]) {
    setForm({ ...form, [key]: value });
    setEdited(true);
    setNotice('');
  }
  async function act(action: string) {
    setError('');
    setNotice('');
    setBusy(true);
    try {
      const version = data?.workflow?.version || 0;
      let next: Data;
      if (action === 'test') {
        retryKey.current ||= crypto.randomUUID();
        const r = await request(base + '/test', {
          version,
          request_id: retryKey.current,
        });
        if (!alive.current) return;
        retryKey.current = '';
        setDetail(null);
        setSelected(r.id);
        next = await request(base);
      } else if (action === 'resume' && selected) {
        next = await request(base + '/runs/' + selected + '/resume', {});
        const id = selected;
        setSelected('');
        setDetail(null);
        window.setTimeout(() => {
          if (alive.current) setSelected(id);
        }, 0);
      } else {
        const body =
          action === 'save'
            ? { ...form, version }
            : action === 'activate'
              ? { version, backlog }
              : { version };
        next = await request(base + '/' + action, body);
      }
      if (alive.current) {
        setData(next);
        if (action === 'save') {
          setEdited(false);
          setNotice('Workflow saved.');
        }
      }
    } catch (e) {
      if (alive.current) setError((e as Error).message);
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  if (!editable)
    return (
      <Empty title="Workflow access requires an editor">
        Ask a workspace administrator to review your role.
      </Empty>
    );
  const w = data?.workflow;
  return (
    <>
      <Heading
        title="Workflows"
        description="Test a documentation workflow, then choose when it runs."
      />
      {error && (
        <p role="alert" className="error-banner">
          {error}
        </p>
      )}
      {notice && <p role="status">{notice}</p>}
      {!data ? (
        <p role="status">Loading workflow…</p>
      ) : (
        <>
          <section className="panel setup-card">
            <div className="inventory-title">
              <GitBranch />
              <h2>Documentation workflow</h2>
            </div>
            <p>
              {w
                ? 'Version ' +
                  w.version +
                  ' · ' +
                  (w.active ? 'Active' : 'Paused')
                : 'New workflow'}
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void act('save');
              }}
            >
              <label>
                Instructions
                <textarea
                  value={form.instructions}
                  required
                  maxLength={2400}
                  onChange={(e) => field('instructions', e.target.value)}
                />
              </label>
              <label>
                Trigger
                <select
                  value={form.trigger}
                  disabled={w?.active}
                  onChange={(e) =>
                    field('trigger', e.target.value as Config['trigger'])
                  }
                >
                  <option value="github">GitHub changes</option>
                  <option value="daily">Daily schedule</option>
                </select>
              </label>
              {form.trigger === 'daily' && (
                <>
                  <label>
                    Local time
                    <input
                      type="time"
                      required
                      value={form.local_time}
                      disabled={w?.active}
                      onChange={(e) => field('local_time', e.target.value)}
                    />
                  </label>
                  <label>
                    Time zone
                    <input
                      required
                      value={form.timezone}
                      disabled={w?.active}
                      onChange={(e) => field('timezone', e.target.value)}
                    />
                  </label>
                </>
              )}
              <label>
                Maximum articles per run
                <input
                  type="number"
                  min={1}
                  max={500}
                  value={form.page_limit}
                  onChange={(e) => field('page_limit', Number(e.target.value))}
                />
              </label>
              <button disabled={busy || (!!w && !edited)} className="primary">
                Save workflow
              </button>
            </form>
            {w && (
              <>
                <p>
                  Live cursor:{' '}
                  <strong>{w.live_cursor || 'No live dispatch yet'}</strong>
                </p>
                {!w.active && (
                  <label>
                    On activation
                    <select
                      value={backlog}
                      onChange={(e) => setBacklog(e.target.value)}
                    >
                      <option value="skip">Skip existing backlog</option>
                      <option value="process">Process existing backlog</option>
                    </select>
                  </label>
                )}
                <div className="inventory-actions">
                  <button disabled={busy || edited} onClick={() => act('test')}>
                    <Play />
                    Run test
                  </button>
                  <button
                    disabled={busy || edited}
                    onClick={() => act(w.active ? 'pause' : 'activate')}
                  >
                    {w.active ? 'Pause workflow' : 'Activate workflow'}
                  </button>
                </div>
              </>
            )}
          </section>
          <section className="panel inventory-preview">
            <div className="inventory-title">
              <Clock />
              <h2>Run history</h2>
            </div>
            {data.runs.length ? (
              data.runs.map((r) => (
                <button
                  key={r.id}
                  className="inventory-item"
                  onClick={() => {
                    setSelected(r.id);
                    setDetail(null);
                    if (r.id === selected)
                      request(base + '/runs/' + r.id)
                        .then(setDetail)
                        .catch((e) => setError(e.message));
                  }}
                >
                  {r.mode} · Version {r.workflow_version} · {r.status}
                </button>
              ))
            ) : (
              <p>No runs yet.</p>
            )}
          </section>
          {detail && (
            <section
              className="panel inventory-preview"
              aria-label="Run timeline"
            >
              <h2>Run timeline</h2>
              <p>
                {detail.mode} · Version {detail.workflow_version} ·{' '}
                <strong>{detail.status}</strong>
              </p>
              <p>{detail.config.instructions}</p>
              {detail.reason && <p role="alert">{detail.reason}</p>}
              <ol>
                {detail.receipts.map((s) => (
                  <li key={s.stage}>
                    <strong>{s.receipt.name}</strong>
                    {s.receipt.pages != null &&
                      ' · ' + s.receipt.pages + ' articles'}
                    {s.receipt.next_action && <p>{s.receipt.next_action}</p>}
                    {s.receipt.candidate_paths && (
                      <details>
                        <summary>Candidate articles</summary>
                        <ul>
                          {s.receipt.candidate_paths.map((p) => (
                            <li key={p}>{p}</li>
                          ))}
                        </ul>
                      </details>
                    )}
                  </li>
                ))}
              </ol>
              {detail.status === 'needs_input' && (
                <button disabled={busy} onClick={() => act('resume')}>
                  Resume run
                </button>
              )}
            </section>
          )}
        </>
      )}
    </>
  );
}
