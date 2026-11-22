import {clearDrafts} from './drafts';
import {GuideLibrary} from './GuideLibrary';
import {Operations} from './Operations';
import {Ask} from './Ask';
import {Captures} from './Captures';
import {Workflows} from './Workflows';
import {Articles} from './Inventory';
import { useEffect, useRef, useState } from 'react';
import { Plus, RefreshCw, Menu } from 'lucide-react';
import { request, manager } from './api';
import { Empty, Modal, Heading, SourceLink, date } from './components';
import { InboxPage, Sources, Health, Intake } from './pages';
import Review from './Review';
import type { Project, Item } from './types';
import { useWorkspaceState } from './useWorkspaceState';
import { WorkspaceSidebar } from './WorkspaceSidebar';
import { Home } from './Home';
import { navigation, readRoute } from './navigation';
import { WorkspaceSetup, WorkspaceEntry } from './Setup';
export default function App({ onSignOut }: { onSignOut: () => void }) {
  const [projects, setProjects] = useState<Project[]>([]),
    [project, setProject] = useState(''),
    [route, setRoute] = useState(readRoute),
    [projectsError, setProjectsError] = useState(''),
    [busy, setBusy] = useState(false),
    [projectsLoading, setProjectsLoading] = useState(true),
    [toast, setToast] = useState(''),
    [mobile, setMobile] = useState(false),
    [modal, setModal] = useState<'request' | 'article' | null>(null),
    [modalPath, setModalPath] = useState(''),
    [confirmation, setConfirmation] = useState<null | { title: string; text: string; action: () => void }>(
      null,
    ),
    [dirty, setDirty] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const scope = useRef('');
  const pending = useRef(false);
  const prefix = project ? 'orgs/' + project.split('/')[0] + '/projects/' + project.split('/')[1] : '';
  const {
    state,
    error: stateError,
    setError,
    loading: stateLoading,
    clear,
    refresh,
  } = useWorkspaceState(prefix);
  const error = projectsError || stateError;
  const loading = projectsLoading || stateLoading;
  useEffect(() => {
    let active = true;
    setProjectsLoading(true);
    request('projects')
      .then(({ projects: available }: { projects: Project[] }) => {
        if (!active) return;
        setProjectsError('');
        setProjects(available);
        const query = new URLSearchParams(location.search);
        const saved = query.get('workspace');
        const selected = available.find((p) => p.organization_id + '/' + p.id === saved) || available[0];
        if (selected) {
          const key = selected.organization_id + '/' + selected.id;
          scope.current = key;
          clear();
          setProject(key);
          if (saved && saved !== key) {
            query.delete('item');
            query.set('view', 'home');
            setRoute({ view: 'home', item: '' });
          }
          query.set('workspace', key);
          history.replaceState(null, '', '/?' + query);
        }
      })
      .catch((err) => {
        if (active) setProjectsError(err.message);
      })
      .finally(() => {
        if (active) setProjectsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [attempt, clear]);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(''), 5000);
    return () => clearTimeout(t);
  }, [toast]);
  useEffect(() => {
    if (!mobile) return;
    const media = window.matchMedia('(max-width:720px)');
    const resize = () => {
      if (!media.matches) setMobile(false);
    };
    media.addEventListener('change', resize);
    return () => media.removeEventListener('change', resize);
  }, [mobile]);
  const confirm = (title: string, text: string, action: () => void) => {
    setMobile(false);
    setConfirmation({ title, text, action });
  };
  const navigate = (view: string, item = '') => {
    const action = () => {
      setDirty(false);
      setRoute({ view, item });
      setMobile(false);
      const q = new URLSearchParams({ view, workspace: project });
      if (item) q.set('item', item);
      history.pushState(null, '', '/?' + q);
      window.scrollTo(0, 0);
      requestAnimationFrame(() => document.getElementById('content')?.focus());
    };
    dirty
      ? confirm(
          'Discard unsaved edits?',
          'Your saved article is unchanged. Discard the text you have not saved?',
          action,
        )
      : action();
  };
  useEffect(() => {
    const unload = (e: BeforeUnloadEvent) => {
      if (dirty) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    const pop = () => {
      const next = readRoute();
      const nextProject = new URLSearchParams(location.search).get('workspace') || project;
      const restore = () => {
        if (projects.some((p) => p.organization_id + '/' + p.id === nextProject) && nextProject !== project) {
          scope.current = nextProject;
          clear();
          setModalPath('');
          setProject(nextProject);
          setModal(null);
          setToast('');
        }
        setRoute(next);
        setMobile(false);
      };
      if (dirty) {
        history.pushState(null, '', '/?' + new URLSearchParams({ ...route, workspace: project }));
        confirm('Discard unsaved edits?', 'Returning to another page discards unsaved article text.', () => {
          setDirty(false);
          restore();
          history.pushState(null, '', '/?' + new URLSearchParams({ ...next, workspace: nextProject }));
        });
      } else restore();
    };
    window.addEventListener('beforeunload', unload);
    window.addEventListener('popstate', pop);
    return () => {
      window.removeEventListener('beforeunload', unload);
      window.removeEventListener('popstate', pop);
    };
  }, [dirty, route, project, projects]);
  async function mutate(action: string, data: unknown, message: string) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    try {
      const result = await request(prefix + '/' + action, data);
      if (scope.current !== project) throw Error('Workspace changed.');
      setDirty(false);
      await refresh();
      if (scope.current !== project) throw Error('Workspace changed.');
      setToast(message);
      return result;
    } catch (e) {
      if (scope.current === project) setError((e as Error).message);
      throw e;
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  const review = (item: Item, action: string, data: Record<string, unknown> = {}) => {
    void mutate('review', { item_id: item.id, version: item.version, action, data }, 'Review saved').catch(
      () => {},
    );
  };
  const changeProject = (next: string) => {
    const action = () => {
      scope.current = next;
      clear();
      setToast('');
      setMobile(false);
      setModal(null);
      setModalPath('');
      setDirty(false);
      setProject(next);
      setRoute({ view: 'home', item: '' });
      history.pushState(null, '', '/?' + new URLSearchParams({ view: 'home', workspace: next }));
    };
    dirty
      ? confirm('Discard unsaved edits?', 'Switching workspaces discards unsaved article text.', action)
      : action();
  };
  const signOut = () => {
    const action = async () => {
      if (manager) await manager.removeUser();
      clearDrafts();
      sessionStorage.removeItem('docs-development-token');
      onSignOut();
    };
    dirty
      ? confirm(
          'Discard unsaved edits?',
          'Signing out discards your unsaved article text.',
          () => void action(),
        )
      : void action();
  };
  function openRequest(id: string) {
    navigate('inbox', id);
    if (!state?.items[id]) void refresh();
  }
  const item = state?.items[route.item];
  return (
    <div className={mobile ? 'nav-open' : ''}>
      <a className="skip" href="#content">
        Skip to content
      </a>
      <WorkspaceSidebar
        state={state}
        projects={projects}
        project={project}
        view={route.view}
        mobile={mobile}
        busy={busy}
        changeProject={changeProject}
        navigate={navigate}
        signOut={signOut}
        close={() => {
          setMobile(false);
          requestAnimationFrame(() => document.getElementById('menu-toggle')?.focus());
        }}
      />
      <main inert={mobile}>
        <header>
          <div className="breadcrumb">
            <button
              id="menu-toggle"
              aria-label="Toggle navigation"
              aria-controls="workspace-navigation"
              aria-expanded={mobile}
              className="icon-button"
              onClick={() => setMobile(!mobile)}
            >
              <Menu />
            </button>
            <span>{state?.manifest.name || 'Documentation'}</span>
            <span className="slash">/</span>
            <strong>{navigation.find((n) => n[0] === route.view)?.[1] || 'Review inbox'}</strong>
          </div>
          <div className="header-actions">
            <span role="status">
              {busy
                ? 'Saving…'
                : loading
                  ? 'Loading…'
                  : error
                    ? 'Needs attention'
                    : dirty
                      ? 'Unsaved edits'
                      : state
                        ? 'Loaded'
                        : ''}
            </span>
            <button
              className="icon-button"
              disabled={loading || busy || dirty}
              aria-label="Refresh workspace"
              onClick={() => (project ? void refresh() : setAttempt((n) => n + 1))}
            >
              <RefreshCw />
            </button>
            <button
              className="primary"
              disabled={!state || state.role === 'contributor' || busy}
              onClick={() => setModal('request')}
            >
              <Plus />
              New request
            </button>
          </div>
        </header>
        {error && (
          <div role="alert" className="error-banner">
            <span>{error}</span>
            <button
              disabled={busy || loading || dirty}
              onClick={() => (project ? void refresh() : setAttempt((n) => n + 1))}
            >
              Retry load
            </button>
            <button onClick={signOut}>Sign in again</button>
          </div>
        )}
        <section className="page" id="content" tabIndex={-1}>
          {loading && !state ? (
            <>
              <div className="skeleton" />
              <div className="skeleton" />
              <p role="status">Loading your workspace…</p>
            </>
          ) : !state ? (
            <><Empty title={error ? 'Workspace unavailable' : 'No workspace assigned'}>
              {error
                ? 'Retry after checking your connection.'
                : 'Create a workspace or use an invitation from your administrator.'}
            </Empty>{!error && <WorkspaceEntry />}</>
          ) : route.item ? (
            <>
              {item ? (
                <Review
                  prefix={prefix}
                  key={item.id}
                  item={item}
                  state={state}
                  busy={busy}
                  dirty={dirty}
                  setDirty={setDirty}
                  back={() => navigate('inbox')}
                  review={review}
                  mutate={mutate}
                  confirm={confirm}
                />
              ) : (
                <Empty title="Request unavailable">
                  It may belong to another workspace or no longer be assigned to you.
                </Empty>
              )}
            </>
          ) : route.view === 'home' ? (
            <Home
              state={state}
              review={(id) => navigate('inbox', id)}
              importArticle={() => setModal('article')}
              newRequest={() => setModal('request')}
            />
          ) : route.view === 'inbox' ? (
            <InboxPage key={prefix} state={state} mutate={mutate} busy={busy} open={(id) => navigate('inbox', id)} />
          ) : route.view === 'articles' ? (
            <Articles key={prefix} prefix={prefix} refresh={refresh} state={state} create={() => setModal('article')} />
          ) : route.view === 'journeys' ? (
            <Captures key={prefix} prefix={prefix} role={state.role}/>
          ) : route.view === 'workflows' ? (
            <Workflows key={prefix} prefix={prefix} role={state.role}/>
          ) : route.view === 'sources' ? (
            <Sources state={state} />
          ) : route.view === 'library' ? (
            <GuideLibrary key={prefix} prefix={prefix} state={state} open={openRequest}/>
          ) : route.view === 'ask' ? (
            <Ask key={prefix} prefix={prefix} open={openRequest}/>
          ) : route.view === 'operations' ? (
            <Operations key={prefix} prefix={prefix} open={openRequest}/>
          ) : route.view === 'health' ? (
            <Health
              prefix={prefix}
              state={state}
              importArticle={(path: string) => {
                setModalPath(path);
                setModal('article');
              }}
              newRequest={(path: string) => {
                setModalPath(path);
                setModal('request');
              }}
            />
          ) : route.view === 'activity' ? (
            <>
              <Heading
                title="Activity log"
                description="Recorded changes and review decisions in this workspace."
              />
              <div className="panel">
                {[...state.audit].reverse().map((a, n) => (
                  <div className="timeline-item" key={n}>
                    <strong>{a.action}</strong>
                    <p>
                      {a.actor} · {date(a.at)}
                    </p>
                  </div>
                ))}
              </div>
            </>
          ) : state.role === 'admin' ? (
            <><WorkspaceSetup key={prefix} prefix={prefix} org={project.split('/')[0]} openItem={id=>navigate('inbox',id)}/>
              <details><summary>Join or create another workspace</summary><WorkspaceEntry /></details></>
          ) : (
            <>
              <Heading title="Workspace settings" description="Product context, access and review policy." />
              <details><summary>Join or create another workspace</summary><WorkspaceEntry /></details>
              <div className="grid-two">
                <div className="panel">
                  <h2>{state.manifest.name}</h2>
                  <p>{state.manifest.repository}</p>
                  <p>{state.manifest.environment}</p>
                  <SourceLink url={state.manifest.application_url}>Open product</SourceLink>
                  <h3>Writing instructions</h3>
                  <p>{state.manifest.instructions}</p>
                </div>
                <div className="panel">
                  <h2>Review policy</h2>
                  <p>
                    Organization membership controls access. Contributors review assigned requests; editors
                    approve delivery. Changes invalidate previous approval. Required captures must be reviewed
                    before delivery.
                  </p>
                  <h3>Integration status</h3>
                  <p>
                    Records are imported snapshots. No background synchronization or billed execution is
                    started by this interface.
                  </p>
                </div>
              </div>
            </>
          )}
        </section>
      </main>
      {toast && (
        <div id="toast" role="status">
          {toast}
        </div>
      )}
      {confirmation && (
        <Modal
          title={confirmation.title}
          description={confirmation.text}
          onClose={() => setConfirmation(null)}
        >
          <div className="modal-footer">
            <button onClick={() => setConfirmation(null)}>Cancel</button>
            <button
              className="primary"
              onClick={() => {
                const action = confirmation.action;
                setConfirmation(null);
                action();
              }}
            >
              Confirm
            </button>
          </div>
        </Modal>
      )}
      {modal && state && (
        <Intake
          kind={modal}
          state={state}
          initialPath={modalPath}
          close={() => {
            setModal(null);
            setModalPath('');
          }}
          submit={async (data) => {
            const result = await mutate(
              modal === 'request' ? 'events' : 'articles',
              data,
              modal === 'request' ? 'Request created' : 'Article imported',
            );
            setModal(null);
            setModalPath('');
            if (result?.item_id) navigate('inbox', result.item_id);
          }}
        />
      )}
    </div>
  );
}
