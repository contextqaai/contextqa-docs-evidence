import { useEffect, useRef, useState, type ReactNode } from 'react';
import { ChevronLeft, ChevronRight, RotateCcw, X } from 'lucide-react';
import './tokens.css';
import './player.css';

export type PlayerScene = {
  title: string;
  chapter: string;
  instruction: string;
  media: ReactNode;
  hotspot?: { x: number; y: number };
};

export function Player({title, scenes, close, guide}: {title:string; scenes:PlayerScene[]; close:()=>void; guide?:string}) {
  const [index, setIndex] = useState(0);
  const [complete, setComplete] = useState(false);
  const [hint, setHint] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const nextHeading = useRef(false);
  const scene = scenes[index];
  function go(n:number) {
    nextHeading.current = true;
    setComplete(false);
    setHint(false);
    setIndex(n);
    if (n === index && !complete) heading.current?.focus();
  }
  function next() {
    if (index + 1 < scenes.length) go(index + 1);
    else { nextHeading.current = true; setComplete(true); }
  }
  useEffect(() => {
    if (nextHeading.current) { heading.current?.focus({preventScroll:true}); nextHeading.current=false; }
  }, [index,complete]);
  if (!scene) return <p role="status">This guide has no reviewed scenes.</p>;
  const chapters = [...new Set(scenes.map(s=>s.chapter))];
  return <main className="cqa-player" aria-label={title} onKeyDown={e=>{
    if(e.altKey || e.ctrlKey || e.metaKey || e.target instanceof HTMLVideoElement) return;
    if(e.key === 'Escape') {e.preventDefault(); close();}
    if(!complete && e.key === 'ArrowRight') {e.preventDefault(); next();}
    if(!complete && e.key === 'ArrowLeft' && index>0) {e.preventDefault(); go(index-1);}
  }}>
    <header className="player-head"><span className="wordmark">Context<b>QA</b></span>
      <div className="player-title"><small>Chapter {chapters.indexOf(scene.chapter)+1} · {scene.chapter}</small><strong>{title}</strong></div>
      <div className="player-tools"><button onClick={()=>go(0)} aria-label="Restart demo"><RotateCcw size={16}/><span>Restart</span></button><button aria-label="Close demo" onClick={close}><X size={19}/></button></div>
    </header>
    <progress aria-label="Demo progress" max={scenes.length} value={complete?scenes.length:index+1}/>
    {complete ? <section className="player-end"><small>Demo complete</small><h1 tabIndex={-1} ref={heading}>You finished <em>{title}.</em></h1>
      {guide && <a className="primary" href={guide}>Read the illustrated guide</a>}<button onClick={()=>go(0)}>Restart demo</button></section> :
    <><div className="player-stage"><section className="player-frame" aria-label="Product screenshot">
      <div className="frame-bar" aria-hidden="true"><i/><i/><i/><span>SoFa Docs</span></div>
      <div className="scene-image" onClick={e=>{if (!(e.target as HTMLElement).closest('button,video,a')) setHint(true);}}>
        {scene.media}
        {scene.hotspot && <button className="player-hotspot" style={{left:scene.hotspot.x+'%',top:scene.hotspot.y+'%'}} aria-label={'Continue from '+scene.title} onClick={next}><i/></button>}
      </div>
      <section className={'player-tip'+(scene.hotspot && scene.hotspot.x>50?' tip-left':'')} aria-label="Step instructions">
        <small>Step {index+1} of {scenes.length}</small><h2 ref={heading} tabIndex={-1}>{scene.title}</h2>
        <p>{scene.instruction}</p>{hint && <p role="status">{scene.hotspot?'Select the highlighted point or Next.':'Select Next to continue.'}</p>}
        <div className="step-controls"><button disabled={index===0} onClick={()=>go(index-1)}><ChevronLeft size={16}/>Back</button><button className="primary" onClick={next}>{index===scenes.length-1?'Finish':'Next'}<ChevronRight size={16}/></button></div>
      </section>
    </section></div>
    <footer className="player-foot"><nav aria-label="Chapters">{chapters.map(ch=><button key={ch} aria-current={ch===scene.chapter?'step':undefined} onClick={()=>go(scenes.findIndex(s=>s.chapter===ch))}>{ch}</button>)}</nav>
      <div className="step-dots" aria-hidden="true">{scenes.map((_,n)=><i key={n} className={n===index?'active':''}/>)}</div></footer></>}
  </main>;
}
