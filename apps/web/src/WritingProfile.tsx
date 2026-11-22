import { useEffect, useState } from 'react';
import { request } from './api';

export type Profile = { revision: number; brand?: string; audience?: string; voice?: string };

export function WritingProfile({ prefix }: { prefix: string }) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let active = true;
    setProfile(null);
    request(prefix + '/writing-profile').then(value => { if (active) setProfile(value); })
      .catch(e => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [prefix, reload]);
  return <section className="panel setup-card">
    <h2>Writing profile</h2>
    {profile && <form key={profile.revision} onSubmit={async e => {
      e.preventDefault();
      const fields = Object.fromEntries(new FormData(e.currentTarget));
      setBusy(true); setError(''); setMessage('');
      try {
        const next = await request(prefix + '/writing-profile', { ...fields, revision: profile.revision });
        setProfile(next); setMessage('Saved writing profile revision ' + next.revision + '.');
      } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
    }}>
      <fieldset disabled={busy}>
        <label>Brand name<input name="brand" defaultValue={profile.brand} maxLength={120} required /></label>
        <label>Default reader<input name="audience" defaultValue={profile.audience} maxLength={120} required /></label>
        <label>Writing voice<select name="voice" defaultValue={profile.voice ?? 'Technical'}>
          <option>Technical</option><option>Business outcome</option>
        </select></label>
        <button className="primary">Save writing profile</button>
      </fieldset>
    </form>}
    {message && <p role="status">{message}</p>}
    {error && <p role="alert">{error} <button onClick={() => { setError(''); setMessage(''); setReload(n => n + 1); }}>Reload profile</button></p>}
  </section>;
}
