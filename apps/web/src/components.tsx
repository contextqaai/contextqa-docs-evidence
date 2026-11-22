import {useEffect,useRef,type ReactNode} from 'react';
import {FileText,ExternalLink} from 'lucide-react';
import {markdown,safeURL,statusLabels} from '../../../cqa_artifacts/loop_ui/ui-core.js';
export const labels=statusLabels as Record<string,string>;
export function Badge({status}:{status:string}){return <span className={'badge '+status}>{labels[status]||status}</span>}
export function SourceLink({url,children}:{url?:string;children:ReactNode}){const safe=safeURL(url);return safe?<a href={safe} target="_blank" rel="noopener noreferrer">{children} <ExternalLink size={12}/></a>:<span>{children}</span>}
export function Markdown({text}:{text:string}){return <div className="document-content" dangerouslySetInnerHTML={{__html:markdown(text)}}/>}
export function Empty({title,children}:{title:string;children?:ReactNode}){return <div className="empty"><FileText/><h2>{title}</h2><p>{children}</p></div>}
export function Heading({title,description,children}:{title:string;description:string;children?:ReactNode}){return <div className="page-heading"><div><h1>{title}</h1><p>{description}</p></div>{children}</div>}
export function Modal({title,description,children,onClose,busy=false}:{title:string;description?:string;children:ReactNode;onClose:()=>void;busy?:boolean}){
 const ref=useRef<HTMLDialogElement>(null);const original=useRef<Element|null>(document.activeElement);
 useEffect(()=>{ref.current?.showModal();return()=>{ref.current?.close();(original.current as HTMLElement)?.focus?.();}},[]);
 return <dialog ref={ref} aria-labelledby="modal-title" onCancel={e=>{e.preventDefault();if(!busy)onClose();}}><div className="modal-header"><h2 id="modal-title">{title}</h2>{description&&<p>{description}</p>}<button className="icon-button" aria-label="Close dialog" disabled={busy} onClick={onClose}>×</button></div><div className="modal-body">{children}</div></dialog>
}
export const titleOf=(body:string,path:string)=>body.match(/^#\s+(.+)/m)?.[1]||path.split('/').pop();
export const date=(value:number)=>new Date(value*1000).toLocaleDateString(undefined,{month:'short',day:'numeric'});
