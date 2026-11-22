// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { WorkspaceSetup } from './Setup';
import { request } from './api';
vi.mock('./api', () => ({ request: vi.fn() }));
afterEach(() => {
  cleanup();
  vi.mocked(request).mockReset();
});
const saved = {
  app_url: 'https://demo.example',
  description: 'Demo workflow',
  revision: 2,
  connected: false,
  product_repo: '',
  docs_repo: '',
  branch: '',
  docs_root: '',
  discoveries: [],
  deliveries: [],
  members: [],
  invites: [],
};
it('resumes saved app details and reports a missing tenant binding without claiming a crawl', async () => {
  vi.mocked(request).mockResolvedValueOnce(saved).mockRejectedValueOnce(Error('Bind the saved app URL'));
  render(<WorkspaceSetup prefix="orgs/team/projects/docs" org="team" openItem={() => {}} />);
  expect(await screen.findByDisplayValue(saved.description)).toBeTruthy();
  await userEvent.click(screen.getByRole('button', { name: 'Start ContextQA crawl' }));
  expect((await screen.findByRole('alert')).textContent).toContain('Bind the saved app URL');
  expect(screen.queryByText('submitted')).toBeNull();
});
it('loads authorized GitHub choices and submits the selected destination separately', async () => {
  vi.mocked(request)
    .mockResolvedValueOnce(saved)
    .mockResolvedValueOnce({ 'org/product': 'main', 'org/docs': 'main' })
    .mockResolvedValueOnce(saved)
    .mockResolvedValueOnce({})
    .mockResolvedValueOnce({ ...saved, connected: true });
  render(<WorkspaceSetup prefix="orgs/team/projects/docs" org="team" openItem={() => {}} />);
  await screen.findByDisplayValue(saved.description);
  await userEvent.click(screen.getByRole('button', { name: 'GitHub' }));
  await userEvent.click(screen.getByRole('button', { name: 'Load installation repositories' }));
  await userEvent.selectOptions(screen.getByLabelText('Product repository'), 'org/product');
  await userEvent.selectOptions(screen.getByLabelText('Documentation repository'), 'org/docs');
  await userEvent.type(screen.getByLabelText('Documentation branch'), 'main');
  await userEvent.click(screen.getByRole('button', { name: 'Save GitHub scope' }));
  expect(request).toHaveBeenCalledWith('orgs/team/projects/docs/github/connect', {
    revision: 2,
    product_repo: 'org/product',
    docs_repo: 'org/docs',
    branch: 'main',
    docs_root: '',
  });
  await userEvent.click(screen.getByRole('button', { name: 'Members' }));
  expect(await screen.findByRole('heading', { name: 'Organization members' })).toBeTruthy();
  expect(screen.queryByText('GitHub scope saved.')).toBeNull();
});
it('checks the saved Pages destination and distinguishes reader verification', async () => {
  const connected = { ...saved, connected: true };
  vi.mocked(request).mockResolvedValueOnce(connected)
    .mockResolvedValueOnce({ branch: 'staging-publish', root: '/docs', url: 'https://sample.github.io/docs/' })
    .mockResolvedValueOnce(connected);
  render(<WorkspaceSetup prefix="orgs/team/projects/docs" org="team" openItem={() => {}} />);
  await screen.findByDisplayValue(saved.description);
  await userEvent.click(screen.getByRole('button', { name: 'GitHub' }));
  await userEvent.click(screen.getByRole('button', { name: 'Check Pages configuration' }));
  expect(request).toHaveBeenCalledWith('orgs/team/projects/docs/pages/check', {});
  expect((await screen.findByRole('status')).textContent).toContain('Reader verification is a separate check');
});
