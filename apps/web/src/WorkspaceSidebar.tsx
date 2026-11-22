import { useEffect, useRef } from 'react';
import { LogOut, X } from 'lucide-react';
import { navigation } from './navigation';
import type { Project, State } from './types';

type Props = {
  state: State | null;
  projects: Project[];
  project: string;
  view: string;
  mobile: boolean;
  busy: boolean;
  changeProject: (key: string) => void;
  navigate: (view: string) => void;
  signOut: () => void;
  close: () => void;
};

export function WorkspaceSidebar({
  state,
  projects,
  project,
  view,
  mobile,
  busy,
  changeProject,
  navigate,
  signOut,
  close,
}: Props) {
  const closeButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (mobile) closeButton.current?.focus();
  }, [mobile]);
  const open = Object.values(state?.items || {}).filter(
    (item) => !['resolved', 'delivered', 'no_change', 'archived'].includes(item.status),
  ).length;
  return (
    <aside
      className="sidebar"
      id="workspace-navigation"
      onKeyDown={(event) => {
        if (mobile && event.key === 'Escape') close();
      }}
    >
      <button
        className="mobile-close icon-button"
        ref={closeButton}
        onClick={close}
        aria-label="Close navigation"
      >
        <X />
      </button>
      <a
        className="brand"
        href="/"
        onClick={(event) => {
          event.preventDefault();
          navigate('home');
        }}
      >
        <img src="/logo.svg" alt="ContextQA" />
        <span className="product-label">Docs</span>
      </a>
      <div className="workspace-switch">
        <label htmlFor="workspace-select" className="sr-only">
          Workspace
        </label>
        <select
          id="workspace-select"
          disabled={busy}
          value={project}
          onChange={(event) => changeProject(event.target.value)}
        >
          {projects.map((p) => (
            <option key={p.organization_id + '/' + p.id} value={p.organization_id + '/' + p.id}>
              {p.name} · {p.organization}
            </option>
          ))}
        </select>
      </div>
      <nav aria-label="Main navigation">
        {navigation.filter(([id])=>state?.role!=='contributor'||!['library','operations'].includes(id)).map(([id, label, Icon]) => (
          <button
            key={id}
            className={view === id ? 'active' : ''}
            aria-current={view === id ? 'page' : undefined}
            onClick={() => navigate(id)}
          >
            <Icon />
            {label}
            {id === 'inbox' && state && <b>{open}</b>}
          </button>
        ))}
      </nav>
      <div className="identity">
        <span className="user-avatar">{state?.actor[0]?.toUpperCase() || '·'}</span>
        <div>
          <strong title={state?.actor}>{state?.actor || 'Workspace member'}</strong>
          <small>{state?.role || 'Authenticated session'}</small>
        </div>
        <button className="icon-button" aria-label="Sign out of application" onClick={signOut}>
          <LogOut />
        </button>
      </div>
    </aside>
  );
}
