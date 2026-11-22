import { useEffect, useRef, useState } from 'react';
import {
  ArrowLeft,
  BookOpen,
  FileText,
  FolderOpen,
  GitBranch,
  Search,
} from 'lucide-react';
import { request } from './api';
import { Empty, Heading, Markdown } from './components';
import type { State } from './types';

type FileRow = {
  path: string;
  kind: string;
  status: string;
  issue?: string;
  title?: string;
  duplicate_title: boolean;
};
type ImportJob = {
  id: string;
  scope: { docs_repo: string; docs_root: string; branch: string };
  commit: string;
  status: string;
  files: FileRow[];
  warnings: string[];
  summary: Record<string, number>;
};

function Figure({
  url,
  alt,
  path,
}: {
  url: string;
  alt: string;
  path: string;
}) {
  const [src, setSrc] = useState(''),
    [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    request(url)
      .then((r) => {
        if (active) setSrc(r.src);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [url]);
  return (
    <figure>
      {src ? (
        <img src={src} alt={alt} />
      ) : (
        <p role="status">{error || 'Loading figure…'}</p>
      )}
      <figcaption>{path}</figcaption>
    </figure>
  );
}

function Preview({ job }: { job: ImportJob }) {
  const pages = job.files.filter((f) => f.kind === 'page'),
    images = job.files.filter((f) => f.kind === 'image');
  return (
    <section
      className="panel inventory-preview"
      aria-label="Repository preview"
    >
      <div className="inventory-title">
        <GitBranch />
        <h2>
          {job.status === 'imported' ? 'Import receipt' : 'Repository preview'}
        </h2>
      </div>
      <p>
        <strong>{job.scope.docs_repo}</strong> · {job.scope.branch} ·{' '}
        {job.scope.docs_root || '/'} · <code>{job.commit.slice(0, 8)}</code>
      </p>
      <p>
        {pages.length} pages · {images.length} images ·{' '}
        {job.files.filter((f) => f.kind === 'navigation').length} navigation
        files
      </p>
      {job.status === 'imported' && (
        <p role="status">
          {job.summary.created} created · {job.summary.updated} updated ·{' '}
          {job.summary.unchanged} unchanged · {job.summary.skipped} skipped
        </p>
      )}
      {job.warnings.map((w) => (
        <p key={w}>{w}</p>
      ))}
      <details open={job.status === 'preview'}>
        <summary>Review files ({job.files.length})</summary>
        <ul className="inventory-files">
          {job.files.map((f) => (
            <li key={f.path}>
              <code>{f.path}</code>
              <span>
                {f.issue ||
                  (f.duplicate_title
                    ? 'Shared title · kept by path'
                    : f.status)}
              </span>
            </li>
          ))}
        </ul>
      </details>
    </section>
  );
}

export function Articles({
  state,
  prefix,
  create,
  refresh,
}: {
  state: State;
  prefix: string;
  create: () => void;
  refresh: () => Promise<void>;
}) {
  const [job, setJob] = useState<ImportJob | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('');
  const [selected, setSelected] = useState(''),
    [query, setQuery] = useState(''),
    [page, setPage] = useState(0);
  const [loading, setLoading] = useState(false);
  const live = useRef(true),
    canImport = state.role === 'admin' || state.role === 'editor';
  const base = prefix + '/inventory';
  useEffect(() => {
    live.current = true;
    let active = true;
    if (canImport) {
      setLoading(true);
      request(base)
        .then((r) => {
          if (active) setJob(r?.id ? r : null);
        })
        .catch((e) => {
          if (active) setError(e.message);
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    }
    return () => {
      active = false;
      live.current = false;
    };
  }, [base, canImport]);
  async function run(action: 'preview' | 'read' | 'apply') {
    setError('');
    setBusy(true);
    try {
      let next: ImportJob = await request(
        action === 'preview'
          ? base + '/preview'
          : base + '/' + job!.id + '/' + action,
        {},
      );
      while (live.current) {
        setJob(next);
        if (next.status !== 'reading') break;
        next = await request(base + '/' + next.id + '/read', {});
      }
      if (action === 'apply' && live.current) await refresh();
    } catch (e) {
      if (live.current) setError((e as Error).message);
    } finally {
      if (live.current) setBusy(false);
    }
  }
  const article = state.articles[selected];
  if (article) {
    const source = article.imported;
    return (
      <>
        <button onClick={() => setSelected('')}>
          <ArrowLeft />
          All articles
        </button>
        <Heading title={article.title} description={article.path} />
        {source && (
          <section className="panel inventory-metadata">
            <h2>Source version</h2>
            <dl>
              <dt>Repository path</dt>
              <dd>
                {source.repo} / {source.repo_path}
              </dd>
              <dt>Reader path</dt>
              <dd>{source.reader_path}</dd>
              <dt>Navigation</dt>
              <dd>{source.navigation.join(' › ') || 'Unlisted'}</dd>
              <dt>Baseline</dt>
              <dd>
                Version {source.version} ·{' '}
                <code>{source.commit.slice(0, 12)}</code>
              </dd>
            </dl>
          </section>
        )}
        <section className="panel inventory-article">
          <Markdown text={article.body} />
          {canImport &&
            source?.images.map((i, n) =>
              i.sha ? (
                <Figure
                  key={source.job + i.path + n}
                  path={i.path}
                  alt={i.alt}
                  url={
                    base +
                    '/figure/' +
                    source.job +
                    '?path=' +
                    encodeURIComponent(i.path)
                  }
                />
              ) : (
                <p key={n}>Figure unavailable: {i.path}</p>
              ),
            )}
        </section>
      </>
    );
  }
  const visible = Object.values(state.articles)
    .filter((a) =>
      (a.title + ' ' + a.path).toLowerCase().includes(query.toLowerCase()),
    )
    .sort((a, b) => a.path.localeCompare(b.path));
  const group: Record<string, typeof visible> = Object.create(null);
  for (const a of visible.slice(page * 30, (page + 1) * 30)) {
    const folder = a.path.includes('/')
      ? a.path.slice(0, a.path.lastIndexOf('/'))
      : 'Repository root';
    (group[folder] ??= []).push(a);
  }
  return (
    <>
      <Heading
        title="Knowledge base"
        description="Browse the existing articles used to review documentation changes."
      >
        {canImport && (
          <div className="inventory-actions">
            <button onClick={create}>Import article</button>
            <button
              className="primary"
              disabled={busy || loading}
              onClick={() => run('preview')}
            >
              <GitBranch />
              Preview repository
            </button>
          </div>
        )}
      </Heading>
      {loading && <p role="status">Loading import status…</p>}
      {error && (
        <p className="error-banner" role="alert">
          {error}
        </p>
      )}
      {job && (
        <>
          <Preview job={job} />
          <div className="inventory-actions">
            {job.status === 'reading' && (
              <button disabled={busy} onClick={() => run('read')}>
                {busy ? 'Reading files…' : 'Resume reading files'}
              </button>
            )}
            {job.status === 'preview' && (
              <button
                className="primary"
                disabled={
                  busy ||
                  !job.files.some(
                    (f) => f.kind === 'page' && f.status === 'ready',
                  )
                }
                onClick={() => run('apply')}
              >
                Import reviewed pages
              </button>
            )}
          </div>
        </>
      )}
      <div className="inventory-bar">
        <h2>
          <BookOpen />
          Article inventory
        </h2>
        <label className="search-box">
          <Search />
          <input
            aria-label="Search articles"
            placeholder="Search title or path…"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setPage(0);
            }}
          />
        </label>
      </div>
      {!visible.length ? (
        <Empty
          title={query ? 'No matching articles' : 'No article baselines yet'}
        >
          {query
            ? 'Try another title or repository path.'
            : 'Preview the connected documentation repository or import an article.'}
        </Empty>
      ) : (
        <section className="panel inventory-tree">
          {Object.entries(group).map(([folder, items]) => (
            <div key={folder}>
              <h3>
                <FolderOpen />
                {folder}
              </h3>
              {items.map((a) => (
                <button
                  className="inventory-item"
                  key={a.path}
                  onClick={() => setSelected(a.path)}
                >
                  <FileText />
                  <span>
                    <strong>{a.title}</strong>
                    <small>{a.path}</small>
                  </span>
                </button>
              ))}
            </div>
          ))}
          {visible.length > 30 && (
            <div className="inventory-actions">
              <button disabled={!page} onClick={() => setPage(page - 1)}>
                Previous
              </button>
              <span>
                Page {page + 1} of {Math.ceil(visible.length / 30)}
              </span>
              <button
                disabled={(page + 1) * 30 >= visible.length}
                onClick={() => setPage(page + 1)}
              >
                Next
              </button>
            </div>
          )}
        </section>
      )}
    </>
  );
}
