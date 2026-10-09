// Uso: PLENO_USER=... PLENO_PASS=... node login.js <arquivo_token>
// Faz login no portal Pleno com Chromium (Playwright), captura o header Authorization
// do módulo Vistoria e grava no arquivo indicado. O token expira em algumas horas e um
// login novo invalida o anterior: o pleno.py chama este script de novo quando recebe 401.
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const out = process.argv[2];
  if (!out || !process.env.PLENO_USER || !process.env.PLENO_PASS) {
    console.error('Uso: PLENO_USER=... PLENO_PASS=... node login.js <arquivo_token>'); process.exit(2);
  }
  const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 1000 }, locale: 'pt-BR' });
  const page = await ctx.newPage();
  let auth = null;
  ctx.on('request', r => { const h = r.headers(); if (!auth && r.url().includes('api.sistemaspleno.com/api/vistoria/') && h.authorization) auth = h.authorization; });
  await page.goto('https://plusvistorias.sistemaspleno.com/portal/login', { waitUntil: 'networkidle' });
  await page.fill('#usu_email', process.env.PLENO_USER);
  await page.fill('#usu_senha', process.env.PLENO_PASS);
  await page.getByRole('button', { name: 'Próximo' }).first().click(); // NÃO usar Enter (aciona "Esqueceu sua senha?")
  await page.waitForTimeout(8000);
  await page.goto('https://plusvistorias.sistemaspleno.com/vistorias/vistorias', { waitUntil: 'networkidle' });
  for (let i = 0; i < 20 && !auth; i++) await page.waitForTimeout(1000);
  await browser.close();
  if (!auth) { console.error('Login falhou: token do módulo Vistoria não capturado.'); process.exit(1); }
  fs.writeFileSync(out, auth);
  console.log('token ok');
})().catch(e => { console.error(e); process.exit(1); });
