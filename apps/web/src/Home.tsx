import { Badge, Empty, Heading } from './components';
import type { State } from './types';

type Props = {
  state: State;
  review: (id: string) => void;
  importArticle: () => void;
  newRequest: () => void;
};

export function Home({ state, review, importArticle, newRequest }: Props) {
  const editor = state.role !== 'contributor';
  const active = Object.values(state.items)
    .filter((item) => !['resolved', 'delivered', 'no_change'].includes(item.status))
    .sort(
      (a, b) =>
        Number(b.status === 'needs_input') - Number(a.status === 'needs_input') ||
        b.created_at - a.created_at,
    );
  const articles = Object.keys(state.articles).length;
  const verified = Object.values(state.items)
    .filter((item) => state.events[item.event_id]?.event.verification?.summary)
    .sort((a, b) => b.created_at - a.created_at);
  return (
    <>
      <Heading title="Workspace overview" description={state.manifest.name} />
      <section className="panel home-queue" aria-label="Review queue">
        <h2>{editor ? 'Requests needing attention' : 'Your assigned requests'}</h2>
        {active.length ? (
          <ul>
            {active.map((item) => (
              <li key={item.id}>
                <div>
                  <button className="text-link" onClick={() => review(item.id)}>
                    {item.title}
                  </button>
                  {item.status === 'needs_input' && item.questions[0] && <p>{item.questions[0]}</p>}
                </div>
                <Badge status={item.status} />
              </li>
            ))}
          </ul>
        ) : (
          <Empty title={editor ? 'Your review queue is clear' : 'No requests assigned'}>
            {editor
              ? 'Start a request when a product change affects a guide.'
              : 'Requests appear here when an editor assigns them to you.'}
          </Empty>
        )}
        {editor && <button onClick={newRequest}>Create a documentation request</button>}
      </section>
      <section className="panel">
        <h2>Execution evidence</h2>
        {verified.length ? (
          <ul>
            {verified.slice(0, 3).map((item) => (
              <li key={item.id}>
                <button className="text-link" onClick={() => review(item.id)}>
                  {item.title}
                </button>
                <p>{state.events[item.event_id].event.verification?.summary}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p>No execution summaries have been imported for these requests.</p>
        )}
      </section>
      {editor && (
        <section className="panel">
          <h2>Article baselines</h2>
          <p>
            {articles
              ? articles + ' imported in this workspace.'
              : 'Import an existing guide to compare future changes against its current text.'}
          </p>
          <button onClick={importArticle}>Import article</button>
        </section>
      )}
    </>
  );
}
