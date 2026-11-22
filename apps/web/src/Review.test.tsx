// @vitest-environment jsdom
import {afterEach,describe,it,expect,vi} from 'vitest';
import {render,screen,cleanup} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Review from './Review';
import {Markdown,SourceLink} from './components';
import {HealthReport,Intake} from './pages';
import type {Item,State} from './types';
afterEach(cleanup);
const item:Item={id:'one',event_id:'event',title:'Change title',source:'github',status:'needs_input',version:1,assignee:null,created_at:1,changes:[{id:'1',path:'guide.md',before:'',after:'# Guide\nText',decision:'pending',reason:'Source change',diff:'',kind:'new'}],questions:['Reviewed capture required'],comments:[],evidence:[],approval:null,delivery:null,affected:[]};
const state:State={actor:'editor',role:'editor',manifest:{name:'Workspace',repository:'org/product',environment:'qa',application_url:'https://product.example.test/',instructions:'Document only behavior verified by reviewed evidence.',sections:[{id:'guide',title:'Guide',path:'guide.md',owner:'editor'},{id:'setup',title:'Set up the product',path:'setup.md',owner:'editor'}]},items:{one:item},events:{event:{digest:'abc',event:{id:'event',source:'github',title:'Source',text:'Source change'}}},members:{editor:'editor'},articles:{},audit:[]};
describe('review console',()=>{
 it('blocks review completion while execution evidence is absent',()=>{render(<Review item={item} state={state} busy={false} dirty={false} setDirty={()=>{}} back={()=>{}} review={()=>{}} mutate={vi.fn()} confirm={()=>{}}/>);expect((screen.getByRole('button',{name:'Finish review'}) as HTMLButtonElement).disabled).toBe(true);expect(screen.getByText('Evidence required before delivery')).toBeTruthy()});
 it('saves the exact edited article against the current version',async()=>{const mutate=vi.fn().mockResolvedValue({}),setDirty=vi.fn();render(<Review item={item} state={state} busy={false} dirty={true} setDirty={setDirty} back={()=>{}} review={()=>{}} mutate={mutate} confirm={(_a,_b,fn)=>fn()}/>);const user=userEvent.setup();await user.click(screen.getByRole('tab',{name:'Article'}));await user.click(screen.getByRole('button',{name:'Edit Markdown'}));await user.clear(screen.getByLabelText('Article Markdown'));await user.type(screen.getByLabelText('Article Markdown'),'# Updated\nNew text');await user.click(screen.getByRole('button',{name:'Save draft'}));expect(mutate).toHaveBeenCalledWith('review',{item_id:'one',version:1,action:'edit',data:{change_id:'1',after:'# Updated\nNew text'}},expect.any(String))});
 it('renders malicious source markup as text and refuses unsafe links',()=>{const {container}=render(<><Markdown text={'<img src=x onerror=alert(1)>\n<script>alert(1)</script>'}/><SourceLink url="javascript:alert(1)">Source</SourceLink></>);expect(container.querySelector('img')).toBeNull();expect(container.querySelector('script')).toBeNull();expect(container.querySelector('a')).toBeNull()});
 it('turns audit findings into actionable health groups without raw JSON',async()=>{const importArticle=vi.fn(),newRequest=vi.fn();const {container}=render(<HealthReport state={state} importArticle={importArticle} newRequest={newRequest} result={{issues:[{path:'setup.md',kind:'coverage_gap',detail:'setup'},{path:'guide.md',kind:'broken_internal_link',detail:'missing.md'}],external_links_checked:false,semantic_contradictions_checked:false}}/>);expect(screen.getByText('Set up the product')).toBeTruthy();expect(screen.getByText('missing.md')).toBeTruthy();expect(screen.getByText('No article baseline is older than 30 days.')).toBeTruthy();expect(screen.getByText(/External links are not checked/)).toBeTruthy();expect(container.querySelector('pre')).toBeNull();const user=userEvent.setup();await user.click(screen.getByRole('button',{name:'Import article'}));await user.click(screen.getByRole('button',{name:'Create request'}));expect(importArticle).toHaveBeenCalledWith('setup.md');expect(newRequest).toHaveBeenCalledWith('guide.md')});
 it('hides health actions from contributors',()=>{render(<HealthReport state={{...state,role:'contributor'}} importArticle={()=>{}} newRequest={()=>{}} result={{issues:[{path:'setup.md',kind:'coverage_gap',detail:'setup'}],external_links_checked:false,semantic_contradictions_checked:false}}/>);expect(screen.queryByRole('button',{name:'Import article'})).toBeNull()});
 it('prefills the missing path when a health finding opens intake',()=>{HTMLDialogElement.prototype.showModal??=function(this:HTMLDialogElement){this.setAttribute('open','')};HTMLDialogElement.prototype.close??=function(this:HTMLDialogElement){this.removeAttribute('open')};render(<Intake kind="request" state={state} initialPath="setup.md" close={()=>{}} submit={vi.fn()}/>);expect((screen.getByLabelText('New article path') as HTMLInputElement).value).toBe('setup.md')});
});

it('opens and closes the compact review context without changing an article decision',async()=>{
 const review=vi.fn();
 render(<Review item={item} state={state} busy={false} dirty={false} setDirty={()=>{}} back={()=>{}} review={review} mutate={vi.fn()} confirm={()=>{}}/>);
 await userEvent.click(screen.getByRole('button',{name:'Show request details'}));
 expect(screen.getByRole('button',{name:'Hide request details'}).getAttribute('aria-expanded')).toBe('true');
 await userEvent.click(screen.getByRole('button',{name:'Hide request details'}));
 expect(screen.getByRole('button',{name:'Show request details'}).getAttribute('aria-expanded')).toBe('false');
 expect(review).not.toHaveBeenCalled();
});
