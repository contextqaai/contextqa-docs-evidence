import {useState} from 'react';
import {createRoot} from 'react-dom/client';
import {Player, type PlayerScene} from './Player';

function ReviewedScreenshot({src, alt}: {src: string; alt: string}) {
  const [status, setStatus] = useState<'loading' | 'ready' | 'failed'>('loading');
  return <figure aria-label="Reviewed screenshot" aria-busy={status === 'loading'}>
    {status === 'failed'
      ? <figcaption role="alert">This screenshot could not be loaded.</figcaption>
      : <img src={src} alt={alt}
          onLoad={event => setStatus(event.currentTarget.naturalWidth > 0 ? 'ready' : 'failed')}
          onError={() => setStatus('failed')} />}
  </figure>;
}

async function loadGuide(): Promise<PlayerScene[]> {
  const response = await fetch('/product-guide.html');
  if (!response.ok) throw Error('The illustrated guide could not be loaded.');
  const doc = new DOMParser().parseFromString(await response.text(), 'text/html');
  const points: Record<string, {x:number;y:number}> = {
    import:{x:34,y:45},write:{x:50,y:38},review:{x:62,y:43},read:{x:36,y:45},demo:{x:60,y:50}
  };
  const scenes = Array.from(doc.querySelectorAll('main > section')).flatMap(section => {
    const image=section.querySelector<HTMLImageElement>('figure img');
    const src=image?.getAttribute('src');
    const title=section.querySelector('h2')?.textContent;
    const instruction=section.querySelector('li')?.textContent;
    if (!src || !title || !instruction || !image) return [];
    const url=new URL(src,response.url);
    if(url.origin!==location.origin) return [];
    return [{title,instruction,chapter:['import','write','review'].includes(section.id)?'Prepare and review':'Share the guide',hotspot:points[section.id],media:<ReviewedScreenshot key={url.href} src={url.href} alt={image.alt}/> }];
  });
  if (!scenes.length) throw Error('No reviewed screenshots are available for this guide.');
  return scenes;
}

const root=createRoot(document.getElementById('player')!);
loadGuide().then(scenes=>root.render(<Player title="Explore SoFa Docs" scenes={scenes} guide="/product-guide.html" close={()=>location.assign('/product-guide.html')}/>))
  .catch(()=>root.render(<main><p role="alert">Unable to open the demo.</p><a href="/product-guide.html">Open the illustrated guide</a></main>));
