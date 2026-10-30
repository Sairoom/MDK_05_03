const fs = require('node:fs/promises');
const path = require('node:path');
const {chromium} = require(process.env.PW_MODULE || 'playwright');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'evidence');
const results = [];
async function main() {
  console.log('Starting checks');
  await fs.mkdir(out, {recursive:true});
  const browser = await chromium.launch({headless:true, timeout:30000, ...(process.env.PW_EXECUTABLE ? {executablePath:process.env.PW_EXECUTABLE} : {})});
  console.log('Browser started');
  const context = await browser.newContext({viewport:{width:1280,height:900}});
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  const cdp = await context.newCDPSession(page);
  await cdp.send('Network.enable');
  let request, response;
  const extraHeaders = new Map();
  cdp.on('Network.requestWillBeSentExtraInfo', e => extraHeaders.set(e.requestId,e.headers));
  cdp.on('Network.requestWillBeSent', e => {if(e.type==='Document' && e.request.url==='https://www.saucedemo.com/') request=e;});
  cdp.on('Network.responseReceived', e => {if(e.type==='Document' && e.response.url==='https://www.saucedemo.com/') response=e;});
  await page.goto('https://www.saucedemo.com/', {waitUntil:'domcontentloaded',timeout:30000});
  console.log('Page loaded');
  if(!request || !response) throw Error('Document network events were not captured');
  const body = await cdp.send('Network.getResponseBody', {requestId:response.requestId});
  const http={capturedAt:new Date().toISOString(),tool:'Chrome DevTools Protocol Network domain',request:{url:request.request.url,method:request.request.method,headers:request.request.headers,body:request.request.postData||null},response:{status:response.response.status,protocol:response.response.protocol,mimeType:response.response.mimeType,headers:response.response.headers,fromDiskCache:response.response.fromDiskCache||false,bodyBase64Encoded:body.base64Encoded},browser:browser.version()};
  if(extraHeaders.has(request.requestId))http.request.headers=extraHeaders.get(request.requestId);
  await fs.writeFile(path.join(out,'http.json'),JSON.stringify(http,null,2));
  await fs.writeFile(path.join(out,'response.html'),body.base64Encoded?Buffer.from(body.body,'base64'):body.body);
  await page.screenshot({path:path.join(out,'login.png')});
  async function login(user,pass) {
    await context.clearCookies();
    await page.goto('https://www.saucedemo.com/');
    await page.evaluate(()=>localStorage.clear());
    await page.reload();
    await page.locator('[data-test="username"]').fill(user);
    await page.locator('[data-test="password"]').fill(pass);
    await page.locator('[data-test="login-button"]').click();
  }
  async function record(id,name,expected,fn) {
    try {const r=await fn();results.push({id,name,expected,...r});}
    catch(e){results.push({id,name,expected,status:'ERROR',actual:e.message});}
  }
  await record('TC-01','Авторизация standard_user','Открыт каталог inventory.html',async()=>{
    await login('standard_user','secret_sauce');await page.waitForURL('**/inventory.html');
    return {status:'PASS',actual:page.url()};
  });
  await record('TC-02','Добавление товара в корзину','Корзина содержит Sauce Labs Backpack и счётчик 1',async()=>{
    await page.locator('[data-test="add-to-cart-sauce-labs-backpack"]').click();
    const badge=await page.locator('[data-test="shopping-cart-badge"]').innerText();
    await page.locator('[data-test="shopping-cart-link"]').click();
    await page.waitForURL('**/cart.html');
    await page.locator('[data-test="cart-list"]').waitFor();
    const names=await page.locator('[data-test="cart-list"] [data-test="inventory-item-name"]').allTextContents();
    return {status:badge==='1'&&names.length===1&&names[0]==='Sauce Labs Backpack'?'PASS':'FAIL',actual:JSON.stringify({badge,names})};
  });
  await record('TC-03','Удаление товара из корзины','Корзина пуста, счётчик отсутствует',async()=>{
    await page.locator('[data-test="remove-sauce-labs-backpack"]').click();
    await page.locator('[data-test="inventory-item"]').waitFor({state:'hidden'});
    const count=await page.locator('[data-test="inventory-item"]').count();
    const badge=await page.locator('[data-test="shopping-cart-badge"]').count();
    return {status:count===0&&badge===0?'PASS':'FAIL',actual:JSON.stringify({count,badge})};
  });
  const prices=async()=> (await page.locator('[data-test="inventory-item-price"]').allTextContents()).map(x=>Number(x.replace('$','')));
  await record('TC-04','Сортировка standard_user по возрастанию цены','Цены расположены по возрастанию',async()=>{
    await page.goto('https://www.saucedemo.com/inventory.html');
    await page.locator('[data-test="product-sort-container"]').selectOption('lohi');
    const p=await prices();return {status:p.every((v,i)=>i===0||v>=p[i-1])?'PASS':'FAIL',actual:JSON.stringify(p)};
  });
  await record('TC-05','Сортировка problem_user по возрастанию цены','Цены расположены по возрастанию',async()=>{
    await login('problem_user','secret_sauce');await page.waitForURL('**/inventory.html');
    await page.locator('[data-test="inventory-item-price"]').first().waitFor();
    const before=await prices();
    await page.locator('[data-test="product-sort-container"]').selectOption('lohi');
    const after=await prices();
    await page.screenshot({path:path.join(out,'bug-sort.png'),fullPage:true});
    return {status:after.every((v,i)=>i===0||v>=after[i-1])?'PASS':'FAIL',actual:JSON.stringify({before,after})};
  });
  const auth=[
    ['AUTH-01','','','Epic sadface: Username is required'],
    ['AUTH-02','standard_user','','Epic sadface: Password is required'],
    ['AUTH-03','','secret_sauce','Epic sadface: Username is required'],
    ['AUTH-04','standard_user','wrong_password','Epic sadface: Username and password do not match any user in this service'],
    ['AUTH-05','unknown_user','secret_sauce','Epic sadface: Username and password do not match any user in this service'],
    ['AUTH-06','locked_out_user','secret_sauce','Epic sadface: Sorry, this user has been locked out.'],
    ['AUTH-07','STANDARD_USER','secret_sauce','Epic sadface: Username and password do not match any user in this service'],
    ['AUTH-08','standard_user','SECRET_SAUCE','Epic sadface: Username and password do not match any user in this service'],
    ['AUTH-09',' standard_user ','secret_sauce','Epic sadface: Username and password do not match any user in this service'],
    ['AUTH-10',"' OR 1=1 --",'secret_sauce','Epic sadface: Username and password do not match any user in this service']
  ];
  for(const [id,u,p,expected] of auth) await record(id,'Негативный сценарий авторизации',expected,async()=>{
    await login(u,p);const actual=await page.locator('[data-test="error"]').innerText();
    if(id==='AUTH-01'||id==='AUTH-06')await page.screenshot({path:path.join(out,id+'.png')});
    return {status:actual===expected&&!page.url().endsWith('/inventory.html')?'PASS':'FAIL',username:u,password:p,actual};
  });
  await record('AUTH-11','Позитивная авторизация','Открыт каталог, показаны 6 товаров',async()=>{
    await login('standard_user','secret_sauce');await page.waitForURL('**/inventory.html');
    await page.locator('[data-test="inventory-item"]').first().waitFor();
    const count=await page.locator('[data-test="inventory-item"]').count();
    await page.screenshot({path:path.join(out,'auth-success.png')});
    return {status:count===6?'PASS':'FAIL',actual:`${page.url()}; товаров: ${count}`};
  });
  await record('AUTH-12','Выход и защита каталога','После выхода прямой переход в каталог отклонён',async()=>{
    await page.locator('#react-burger-menu-btn').click();await page.locator('[data-test="logout-sidebar-link"]').click();
    await page.goto('https://www.saucedemo.com/inventory.html');
    const actual=await page.locator('[data-test="error"]').innerText();
    return {status:page.url()==='https://www.saucedemo.com/'&&actual.includes('only access')?'PASS':'FAIL',actual};
  });
  const fields=await page.locator('input').evaluateAll(es=>es.map(e=>({name:e.name,type:e.type,required:e.required,maxLength:e.maxLength,autocomplete:e.autocomplete})));
  await fs.writeFile(path.join(out,'results.json'),JSON.stringify({executedAt:new Date().toISOString(),target:'https://www.saucedemo.com/',browser:browser.version(),platform:process.platform,viewport:{width:1280,height:900},fields,results},null,2));
  console.log(JSON.stringify(results.map(({id,status,actual})=>({id,status,actual})),null,2));
  await browser.close();
  if(results.some(r=>r.status==='ERROR'||(r.status==='FAIL'&&r.id!=='TC-05')) || results.find(r=>r.id==='TC-05')?.status!=='FAIL')process.exitCode=1;
}
main().catch(e=>{console.error(e);process.exitCode=1;});
