import { Activity, Workflow, BookOpen, House, Inbox, Link, Settings, ShieldCheck } from 'lucide-react';

export const navigation = [
  ['home', 'Overview', House],
  ['inbox', 'Review inbox', Inbox],
  ['articles', 'Knowledge base', BookOpen],
  ['sources', 'Sources & evidence', Link],
  ['workflows', 'Workflows', Workflow],
  ['health', 'Content health', ShieldCheck],
  ['activity', 'Activity log', Activity],
  ['settings', 'Workspace settings', Settings],
] as const;

export function readRoute() {
  const query = new URLSearchParams(location.search);
  const item = query.get('item') || '';
  const view = item ? 'inbox' : query.get('view') || 'home';
  return { view: navigation.some(([id]) => id === view) ? view : 'home', item };
}
