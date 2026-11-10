const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async()=>{const b=await chromium.launch({channel:'msedge',headless:true});try{
const p=await b.newPage({viewport:{width:1440,height:1000}});
async function open(port){await p.goto(`http://127.0.0.1:${port}`);await p.locator('[data-oes-core]').focus();await p.keyboard.press('Enter');}
async function send(text){await p.locator('textarea').fill(text);await p.locator('[data-chat-send]').click();}
const responseError='Eyeball could not complete that response. Try again.';
await open(5057);await send('hello');await p.getByText(responseError,{exact:true}).waitFor();assert.equal(await p.getByRole('button',{name:'Retry message'}).count(),1);assert.equal(await p.locator('[data-chat-send]').isDisabled(),false);console.log('PASS real disabled endpoint gives graceful retry UI');
await open(5055);await send('hello');await p.waitForFunction(()=>document.querySelector('[data-chat-send]').disabled===false);assert.equal(await p.getByText(responseError,{exact:true}).count(),0);assert.ok(await p.locator('.eyeball-chat__message:not(.eyeball-chat__message--user)').count()>0);console.log('PASS enabled Ollama browser response');
await open(5055);let held;
await p.route('**/api/chat',r=>{if(r.request().postDataJSON().message==='first')held=r;else return r.fulfill({status:200,contentType:'text/event-stream',body:'event: start\ndata: {}\n\nevent: delta\ndata: {"text":"NEW RESPONSE"}\n\nevent: done\ndata: {}\n\n'});});
const firstRequested=p.waitForRequest('**/api/chat');await send('first');await firstRequested;
await p.locator('[data-chat-stop]').click();await send('second');await p.getByText('NEW RESPONSE',{exact:true}).waitFor();await held.fulfill({status:200,contentType:'text/event-stream',body:'event: delta\ndata: {"text":"STALE RESPONSE"}\n\nevent: done\ndata: {}\n\n'}).catch(()=>{});await p.waitForTimeout(100);assert.equal(await p.getByText('STALE RESPONSE',{exact:true}).count(),0);console.log('PASS Stop/new interaction rejects late response (transport fixture)');
await p.unroute('**/api/chat');await open(5055);await p.clock.install();await p.route('**/api/chat',()=>{});const requested=p.waitForRequest('**/api/chat');await send('timeout');await requested;await p.getByText('Thinking',{exact:true}).waitFor();await p.clock.fastForward(12001);await p.getByText('Still working',{exact:true}).waitFor();await p.clock.fastForward(318000);await p.getByText('Eyeball took too long to respond. Try again.',{exact:true}).waitFor();assert.equal(await p.getByRole('button',{name:'Retry message'}).count(),1);assert.equal(await p.locator('[data-chat-send]').isDisabled(),false);console.log('PASS stalled connection shows progress, timeout, and retry');
}finally{await b.close();}})().catch(e=>{console.error(e);process.exitCode=1});
