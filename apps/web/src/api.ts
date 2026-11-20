import {UserManager,WebStorageStateStore} from 'oidc-client-ts';
export type Config={auth_mode:string;authority:string;client_id:string;scope:string;redirect_uri:string;audience:string};
export let manager:UserManager|undefined;
export async function setupAuth():Promise<Config>{
 const response=await fetch('/api/config');if(!response.ok)throw Error('The application configuration could not be loaded.');
 const config:Config=await response.json();
 if(config.auth_mode==='oidc'){
  manager=new UserManager({authority:config.authority,client_id:config.client_id,redirect_uri:config.redirect_uri,response_type:'code',scope:config.scope,userStore:new WebStorageStateStore({store:sessionStorage}),automaticSilentRenew:false,loadUserInfo:false,extraQueryParams:{audience:config.audience}});
  if(location.pathname==='/auth/callback'){await manager.signinRedirectCallback();history.replaceState(null,'','/');}
 }
 return config;
}
export async function accessToken(){
 if(manager){const user=await manager.getUser();if(!user||user.expired)throw Error('Your session has expired. Sign in again to continue.');return user.access_token;}
 const token=sessionStorage.getItem('docs-development-token');if(!token)throw Error('Enter the development access token.');return token;
}
export async function request(path:string,data?:unknown):Promise<any>{
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),20000);
 try{
  const response=await fetch('/api/'+path,{method:data===undefined?'GET':'POST',signal:controller.signal,headers:{Authorization:'Bearer '+await accessToken(),...(data!==undefined?{'Content-Type':'application/json'}:{})},body:data===undefined?undefined:JSON.stringify(data)});
  if(!response.ok){let detail='Request failed. Refresh before retrying.';try{const result=await response.json();if(typeof result.detail==='string')detail=result.detail;}catch{}throw Error(detail);}
  return response.headers.get('content-type')?.startsWith('application/zip')?response.blob():response.json();
 }catch(e){if(e instanceof Error&&e.name==='AbortError')throw Error('Request timed out. Refresh to check its outcome before retrying.');throw e;}
 finally{clearTimeout(timer);}
}
