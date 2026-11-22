import { useEffect, useState, type FormEvent } from 'react';
import { BookOpen, Github, Users } from 'lucide-react';
import { WritingProfile } from './WritingProfile';
import { request } from './api';
import { Heading, SourceLink } from './components';

type Person = { subject: string; role: string };
type Setup = {
  app_url: string;
  description: string;
  revision: number;
  product_repo: string;
  docs_repo: string;
  branch: string;
  docs_root: string;
  connected: boolean;
  source_branch: string;
  members: Person[];
  invites: (Person & { expires_at: string })[];
  discoveries: {
    id: string;
    status: string;
    provider_job: string | null;
    evidence_receipt?: { result_id: number; recordings: number };
  }[];
  pull_requests?: { item_id: string; status: string; pr_url: string | null }[];
  deliveries: { delivery: string; revision: string; item_id: string }[];
};
type Fields = Record<string, string>;
const values = (e: FormEvent<HTMLFormElement>) => {
  e.preventDefault();
  return Object.fromEntries(new FormData(e.currentTarget)) as Fields;
};
const roles = ['contributor', 'editor', 'admin'];
function RoleOptions() {
  return (
    <>
      {roles.map((r) => (
        <option key={r}>{r}</option>
      ))}
    </>
  );
}

export function WorkspaceEntry() {
  const [mode, setMode] = useState<'create' | 'join'>('create');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [key] = useState(() => crypto.randomUUID());
  async function submit(e: FormEvent<HTMLFormElement>) {
    const data = values(e);
    setBusy(true);
    setError('');
    try {
      if (mode === 'join') {
        const result = await request('invites/accept', data);
        const { projects } = await request('projects');
        const p = projects.find(
          (item: { organization_id: string }) => item.organization_id === result.organization_id,
        );
        location.assign(
          p
            ? '/?' + new URLSearchParams({ workspace: p.organization_id + '/' + p.id, view: 'home' })
            : '/',
        );
      } else {
        const result = await request('workspaces', { ...data, request_id: key });
        location.assign('/?' + new URLSearchParams({ workspace: result.workspace, view: 'settings' }));
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel setup-card">
      <h2>Workspace access</h2>
      <div className="setup-tabs">
        <button aria-pressed={mode === 'create'} onClick={() => setMode('create')}>
          Create workspace
        </button>
        <button aria-pressed={mode === 'join'} onClick={() => setMode('join')}>
          Accept invitation
        </button>
      </div>
      <form key={mode} onSubmit={submit}>
        <fieldset disabled={busy}>
          {mode === 'create' ? (
            <>
              <label>
                Workspace name (optional)
                <input name="name" maxLength={120} placeholder="Defaults to the product hostname" />
              </label>
              <label>
                Product URL
                <input name="app_url" type="url" placeholder="https://app.example.com" required />
              </label>
            </>
          ) : (
            <label>
              Invitation code
              <input name="token" type="password" autoComplete="off" required />
            </label>
          )}
          <button className="primary">
            {mode === 'create' ? 'Create and configure' : 'Join workspace'}
          </button>
        </fieldset>
      </form>
      {error && <p role="alert">{error}</p>}
    </section>
  );
}

export function WorkspaceSetup({
  prefix,
  org,
  openItem,
}: {
  prefix: string;
  org: string;
  openItem: (id: string) => void;
}) {
  const [tab, setTab] = useState<'app' | 'github' | 'members' | 'writing'>('app');
  const [data, setData] = useState<Setup | null>(null);
  const [repos, setRepos] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [message, setMessage] = useState('');
  const [invitation, setInvitation] = useState(''),
    [login, setLogin] = useState(false);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let active = true;
    request(prefix + '/setup')
      .then((v) => {
        if (active) setData(v);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [prefix, reload]);
  async function act(work: () => Promise<unknown>, notice: string) {
    setError('');
    setMessage('');
    setBusy(true);
    try {
      await work();
      setData(await request(prefix + '/setup'));
      if (notice) setMessage(notice);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const createInvite = async (fields: Fields) => {
    setInvitation('');
    const r = await request('orgs/' + org + '/invites', fields);
    setInvitation(r.token);
  };
  function selectTab(next: typeof tab) {
    setTab(next);
    setMessage('');
    setError('');
    setInvitation('');
  }
  const loadedRepos = Object.keys(repos);
  return (
    <>
      <Heading
        title="Workspace setup"
        description="Configure product discovery, documentation sources and team access."
      />
      <div className="setup-tabs" aria-label="Setup sections">
        <button aria-pressed={tab === 'app'} disabled={busy} onClick={() => selectTab('app')}>
          <BookOpen size={16} /> App discovery
        </button>
        <button aria-pressed={tab === 'github'} disabled={busy} onClick={() => selectTab('github')}>
          <Github size={16} /> GitHub
        </button>
        <button aria-pressed={tab === 'writing'} disabled={busy} onClick={() => selectTab('writing')}>
          Writing profile
        </button>
        <button aria-pressed={tab === 'members'} disabled={busy} onClick={() => selectTab('members')}>
          <Users size={16} /> Members
        </button>
      </div>
      {error && (
        <div className="error-banner" role="alert">
          {error}{' '}
          <button
            onClick={() => {
              setError('');
              setReload((n) => n + 1);
            }}
          >
            Reload setup
          </button>
        </div>
      )}
      {message && <p role="status">{message}</p>}
      {!data ? (
        !error && <p role="status">Loading setup…</p>
      ) : (
        <fieldset className="setup-fields" disabled={busy}>
          {tab === 'app' && (
            <>
              <section className="panel setup-card">
                <h2>Product to document</h2>
                <form
                  key={data.revision}
                  onSubmit={(e) => {
                    const fields = values(e);
                    void act(
                      () => request(prefix + '/setup', { ...fields, revision: data.revision }),
                      'Product details saved.',
                    );
                  }}
                >
                  <label>
                    Product URL
                    <input name="app_url" type="url" defaultValue={data.app_url} required />
                  </label>
                  <label>
                    What can users do here?
                    <textarea
                      name="description"
                      maxLength={600}
                      defaultValue={data.description}
                      required
                    />
                  </label>
                  <button>Save product details</button>
                </form>
              </section>
              <section className="panel setup-card">
                <h2>Discover user journeys</h2>
                <p>
                  ContextQA explores the saved product URL with the access you provide. Discovery can
                  spend credits and store the test login in the configured ContextQA workspace.
                </p>
                <form
                  onSubmit={(e) => {
                    const form = e.currentTarget;
                    const f = values(e);
                    void act(async () => {
                      try {
                        await request(prefix + '/discovery', {
                          revision: data.revision,
                          confirm: true,
                          login_required: login,
                          username: f.username || '',
                          password: f.password || null,
                        });
                      } finally {
                        form.reset();
                        setLogin(false);
                      }
                    }, 'Discovery receipt refreshed. Check the status below.');
                  }}
                >
                  <label className="setup-check">
                    <input
                      type="checkbox"
                      checked={login}
                      onChange={(e) => setLogin(e.target.checked)}
                    />{' '}
                    App requires a test login
                  </label>
                  {login && (
                    <>
                      <label>
                        Test username
                        <input name="username" autoComplete="off" required />
                      </label>
                      <label>
                        Test password
                        <input name="password" type="password" autoComplete="off" required />
                      </label>
                    </>
                  )}
                  <button className="primary" disabled={!data.description}>
                    Start ContextQA crawl
                  </button>
                </form>
                {data.discoveries.map((d) => (
                  <div key={d.id}>
                    <p>
                      <strong>{d.status.replaceAll('_', ' ')}</strong> ·{' '}
                      {d.provider_job ? 'Provider job ' + d.provider_job : 'Local receipt ' + d.id}
                    </p>
                    {d.evidence_receipt ? (
                      <p>
                        Result {d.evidence_receipt.result_id} · {d.evidence_receipt.recordings}{' '}
                        recording(s)
                      </p>
                    ) : (
                      <button
                        onClick={() =>
                          void act(async () => {
                            const result = await request(prefix + '/discovery/' + d.id + '/refresh', {});
                            setMessage(result.detail || result.status);
                          }, '')
                        }
                      >
                        Check crawl result
                      </button>
                    )}
                  </div>
                ))}
              </section>
            </>
          )}
          {tab === 'github' && (
            <section className="panel setup-card">
              <h2>GitHub connection</h2>
              <p>
                {data.connected
                  ? 'Receiving changes from ' + data.product_repo + ' on ' + data.source_branch
                  : 'Select the product source and the destination for documentation changes.'}
              </p>
              <button
                onClick={() =>
                  void act(
                    async () => setRepos(await request(prefix + '/github/repos')),
                    'Installation repositories loaded.',
                  )
                }
              >
                Load installation repositories
              </button>
              <form
                key={data.revision + '-' + loadedRepos.length}
                onSubmit={(e) => {
                  const fields = values(e);
                  void act(
                    () => request(prefix + '/github/connect', { ...fields, revision: data.revision }),
                    'GitHub scope saved.',
                  );
                }}
              >
                {(['product_repo', 'docs_repo'] as const).map((k, i) => (
                  <label key={k}>
                    {i ? 'Documentation repository' : 'Product repository'}
                    <select name={k} defaultValue={data[k]} required>
                      <option value="">Select a repository</option>
                      {Array.from(new Set([data[k], ...loadedRepos]))
                        .filter(Boolean)
                        .map((name) => (
                          <option key={name}>{name}</option>
                        ))}
                    </select>
                  </label>
                ))}
                <label>
                  Documentation branch
                  <input name="branch" defaultValue={data.branch} placeholder="main" required />
                </label>
                <label>
                  Documentation directory
                  <input
                    name="docs_root"
                    defaultValue={data.docs_root}
                    placeholder="Leave blank for repository root"
                  />
                </label>
                <button className="primary">Save GitHub scope</button>
              </form>
              {data.connected && (
                <>
                  <label>
                    Webhook URL
                    <input readOnly value={location.origin + '/api/' + prefix + '/github/webhook'} />
                  </label>
                  <p>
                    Disconnect pauses intake here. The GitHub App installation stays installed on GitHub.
                  </p>
                  <button
                    onClick={() =>
                      void act(
                        () => request(prefix + '/github/disconnect', { revision: data.revision }),
                        'GitHub intake paused.',
                      )
                    }
                  >
                    Disconnect GitHub
                  </button>
                </>
              )}
              <h3>GitHub Pages</h3>
              <p>Check that GitHub publishes the selected documentation branch and directory as a public site.</p>
              <button disabled={!data.connected} onClick={() => void act(async () => {
                const result = await request(prefix + '/pages/check', {});
                setMessage('Pages configuration verified for ' + result.branch + ' (' + result.root +
                  ') at ' + result.url + '. Reader verification is a separate check.');
              }, '')}>Check Pages configuration</button>
              <button disabled={!data.connected} onClick={() => void act(async () => {
                const result = await request(prefix + '/pages/verify', {});
                setMessage(result.verified_files.length + ' public files matched the Pages build for commit ' +
                  result.revision + '.');
              }, '')}>Verify deployed files</button>
              <h3>Recent source deliveries</h3>
              {data.deliveries.length ? (
                data.deliveries.map((d) => (
                  <p key={d.delivery}>
                    <button onClick={() => openItem(d.item_id)}>
                      Review source {d.revision.slice(0, 10)}
                    </button>
                  </p>
                ))
              ) : (
                <p>No deliveries received.</p>
              )}
              {data.pull_requests?.map((pr) => (
                <p key={pr.item_id}>
                  {pr.pr_url ? (
                    <SourceLink url={pr.pr_url}>Open draft documentation PR</SourceLink>
                  ) : (
                    'Draft PR awaiting reconciliation'
                  )}
                </p>
              ))}
            </section>
          )}
          {tab === 'writing' && <WritingProfile prefix={prefix} />}
          {tab === 'members' && (
            <section className="panel setup-card">
              <h2>Organization members</h2>
              {data.members.map((m) => (
                <form
                  className="member-row"
                  key={m.subject + m.role}
                  onSubmit={(e) => {
                    const f = values(e);
                    void act(
                      () => request('orgs/' + org + '/members', { subject: m.subject, role: f.role }),
                      'Membership updated.',
                    );
                  }}
                >
                  <strong>{m.subject}</strong>
                  <label>
                    Access for {m.subject}
                    <select name="role" defaultValue={m.role}>
                      <RoleOptions />
                      <option value="remove">Remove access</option>
                    </select>
                  </label>
                  <button>Apply</button>
                </form>
              ))}
              <h3>Invite a member</h3>
              <form
                onSubmit={(e) => {
                  const f = values(e);
                  void act(
                    () => createInvite(f),
                    'Invitation created. Share the code with the intended account.',
                  );
                }}
              >
                <label>
                  Account subject
                  <input name="subject" required placeholder="Identity provider subject" />
                </label>
                <label>
                  Role
                  <select name="role">
                    <RoleOptions />
                  </select>
                </label>
                <button>Create invitation</button>
              </form>
              {data.invites.map((i) => (
                <div key={i.subject} className="member-row">
                  <span>
                    {i.subject} · {i.role} · expires {new Date(i.expires_at).toLocaleDateString()}
                  </span>
                  <button
                    onClick={() =>
                      void act(
                        () => createInvite({ subject: i.subject, role: i.role }),
                        'Previous code replaced.',
                      )
                    }
                  >
                    Replace code
                  </button>
                </div>
              ))}
              {invitation && (
                <label>
                  One-time invitation code
                  <input readOnly value={invitation} onFocus={(e) => e.target.select()} />
                </label>
              )}
            </section>
          )}
        </fieldset>
      )}
    </>
  );
}
