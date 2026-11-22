export const escapeHTML=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function safeURL(value){try{const u=new URL(value);return ['https:','http:'].includes(u.protocol)&&!u.username&&!u.password?u.href:null;}catch{return null;}}
export function inline(value) {
  const tokens = /(\\[\\`*_{}\[\]()#+.!|>\-]|&(?:lt|gt|amp|quot|#x27);|`[^`]+`|\*\*[^*]+\*\*|\[[^\]\n]+\]\(https?:\/\/[^\s)]+\))/g;
  return String(value).split(tokens).map((part,index) => {
    if (index % 2 === 0) return escapeHTML(part);
    if (part.startsWith('\\')) return escapeHTML(part.slice(1));
    if (part.startsWith('&')) return part;
    if (part.startsWith('`')) return '<code>'+escapeHTML(part.slice(1,-1))+'</code>';
    if (part.startsWith('**')) return '<strong>'+escapeHTML(part.slice(2,-2))+'</strong>';
    const link = part.match(/^\[([^\]]+)\]\((.+)\)$/);
    const href = link && safeURL(link[2]);
    return href ? '<a href="'+escapeHTML(href)+'" rel="noopener noreferrer">'+escapeHTML(link[1])+'</a>' : escapeHTML(part);
  }).join('');
}
export function markdown(value){let code=false,lines=[];for(const line of String(value).split('\n')){if(line.startsWith('```')){code=!code;lines.push(code?'<pre><code>':'</code></pre>');continue;}if(code){lines.push(escapeHTML(line)+'\n');continue;}const h=line.match(/^(#{1,4})\s+(.*)/);if(h){lines.push(`<h${h[1].length}>${inline(h[2])}</h${h[1].length}>`);continue;}const list=line.match(/^(\d+\.|[-*])\s+(.*)/);if(list){lines.push(`<div class="md-list"><span>${escapeHTML(list[1])}</span><div>${inline(list[2])}</div></div>`);continue;}if(line.startsWith('> ')){lines.push(`<blockquote>${inline(line.slice(2))}</blockquote>`);continue;}if(line.trim())lines.push(`<p>${inline(line)}</p>`);}if(code)lines.push('</code></pre>');return lines.join('');}
export function itemMatches(item,filter,query,actor){const matches=filter==='all'||(filter==='assigned'?item.assignee===actor:filter==='review'?['open','ready'].includes(item.status):filter==='blocked'?item.status==='needs_input':filter==='done'?['resolved','delivered','no_change'].includes(item.status):item.status===filter);return matches&&`${item.title} ${item.source} ${item.event_id}`.toLowerCase().includes(query.toLowerCase());}
export const statusLabels={archived:'Archived',needs_input:'Needs evidence',open:'In review',ready:'Ready for approval',delivered:'Draft delivered',resolved:'Resolved',no_change:'No changes',pending:'Not reviewed',accepted:'Accepted',ignored:'Dismissed',FAILURE:'Failed',SUCCESS:'Passed'};
export function canFinish(item){return item.writing?.status!=='in_progress'&&!item.questions.length&&item.changes.every(c=>c.decision!=='pending')&&!['delivered','resolved','archived'].includes(item.status);}
