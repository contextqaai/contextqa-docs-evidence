// @vitest-environment jsdom
import { act, cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import App from './App';
import { request } from './api';
import type { State } from './types';

vi.mock('./api', () => ({ request: vi.fn(), manager: undefined }));
const projects = ['alpha', 'beta'].map((id) => ({
  id,
  organization_id: 'org',
  organization: 'Team',
  name: id,
  role: 'editor',
}));
function snapshot(name: string, role = 'editor'): State {
  return {
    actor: name + ' writer',
    role,
    manifest: {
      name,
      repository: 'team/docs',
      instructions: '',
      environment: 'qa',
      application_url: '',
      sections: [],
    },
    members: {},
    audit: [],
    events: {},
    articles: {},
    items: {},
  };
}

beforeEach(() => {
  history.replaceState(null, '', '/');
  vi.mocked(request).mockReset();
  vi.stubGlobal('scrollTo', vi.fn());
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it('recovers from failed project discovery and shows the first request action', async () => {
  vi.mocked(request)
    .mockRejectedValueOnce(Error('Connection lost'))
    .mockResolvedValueOnce({ projects })
    .mockResolvedValueOnce(snapshot('alpha'));
  render(<App onSignOut={vi.fn()} />);
  expect((await screen.findByRole('alert')).textContent).toContain('Connection lost');
  expect(screen.queryByText('Loaded')).toBeNull();
  await userEvent.click(screen.getByRole('button', { name: 'Retry load' }));
  expect(await screen.findByRole('button', { name: 'Create a documentation request' })).toBeTruthy();
  expect(location.search).toContain('workspace=org%2Falpha');
});

it('clears old content during a workspace switch and ignores a late refresh', async () => {
  let finishRefresh!: (value: State) => void;
  let finishSwitch!: (value: State) => void;
  vi.mocked(request)
    .mockResolvedValueOnce({ projects })
    .mockResolvedValueOnce(snapshot('alpha'))
    .mockReturnValueOnce(
      new Promise((resolve) => {
        finishRefresh = resolve;
      }),
    )
    .mockReturnValueOnce(
      new Promise((resolve) => {
        finishSwitch = resolve;
      }),
    );
  render(<App onSignOut={vi.fn()} />);
  await screen.findByText('alpha writer');
  await userEvent.click(screen.getByRole('button', { name: 'Refresh workspace' }));
  await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Workspace' }), 'org/beta');
  expect(screen.queryByText('alpha writer')).toBeNull();
  await act(async () => {
    finishRefresh(snapshot('old'));
    finishSwitch(snapshot('beta', 'contributor'));
  });
  expect(screen.getByText('beta writer')).toBeTruthy();
  expect(screen.queryByText('old writer')).toBeNull();
  expect(screen.queryByRole('button', { name: 'Import article' })).toBeNull();
  expect(screen.getByText('No requests assigned')).toBeTruthy();
});

it('restores the workspace together with its view on browser navigation', async () => {
  vi.mocked(request).mockImplementation(async path => {
    if(path==='projects') return {projects};
    if(path.endsWith('/inventory')) return null;
    if(path.endsWith('/state')) return snapshot(path.includes('/beta/')?'beta':'alpha');
    throw new Error('Unexpected route '+path);
  });
  render(<App onSignOut={vi.fn()} />);
  await screen.findByText('alpha writer');
  await userEvent.click(screen.getByRole('button', { name: 'Knowledge base' }));
  const previous = location.href;
  await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Workspace' }), 'org/beta');
  await screen.findByText('beta writer');
  act(() => {
    history.replaceState(null, '', previous);
    window.dispatchEvent(new PopStateEvent('popstate'));
  });
  expect(await screen.findByText('alpha writer')).toBeTruthy();
  expect(screen.getByRole('heading', { name: 'Knowledge base' })).toBeTruthy();
});

it('returns focus to the overview action after cancelling intake', async () => {
  HTMLDialogElement.prototype.showModal ??= function () { this.setAttribute('open',''); };
  HTMLDialogElement.prototype.close ??= function () { this.removeAttribute('open'); };
  vi.mocked(request).mockResolvedValueOnce({projects}).mockResolvedValueOnce(snapshot('alpha'));
  render(<App onSignOut={vi.fn()}/>);
  const start = await screen.findByRole('button',{name:'Create a documentation request'});
  await userEvent.click(start);
  expect(screen.getByRole('dialog')).toBeTruthy();
  await userEvent.click(screen.getByRole('button',{name:'Cancel'}));
  expect(document.activeElement).toBe(start);
});
