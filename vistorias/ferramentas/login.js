// Uso: PLENO_USER=... PLENO_PASS=... node login.js <arquivo_token>
// Faz login no portal Pleno com Chromium (Playwright), captura o header Authorization
// do módulo Vistoria e grava no arquivo indicado. O token expira em algumas horas e um
// login novo invalida o anterior: o pleno.py chama este script de novo quando recebe 401.
const { chromium } = require('playwright');
const fs = require('fs');

// O botão de login já mudou de nome ("Próximo" -> "Entrar", out/2026). Para não quebrar de novo:
// tenta os nomes conhecidos e, se nenhum existir, usa o botão da tela que não é "Esqueceu sua senha?"
// nem o olho da senha. NUNCA usar Enter (aciona "Esqueceu sua senha?").
async function clicarEntrar(page) {
  const conhecido = page.getByRole('button', { name: /^\s*(Entrar|Próximo|Acessar|Login)\b/i });
  if (await conhecido.count()) return conhecido.first().click();
  const outros = page.locator('button').filter({ hasNotText: /esqueceu|senha|visibility/i });
  if (await outros.count()) {
    console.error('Aviso: botão de login com nome novo:', (await outros.first().innerText()).trim());
    return outros.first().click();
  }
  throw new Error('Botão de login não encontrado na tela do portal.');
}

(async () => {
  const out = process.argv[2];
  if (!out || !process.env.PLENO_USER || !process.env.PLENO_PASS) {
    console.error('Uso: PLENO_USER=... PLENO_PASS=... node login.js <arquivo_token>'); process.exit(2);
  }
  const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 1000 }, locale: 'pt-BR' });
  const page = await ctx.newPage();
  // O portal também chama a API de vistoria com o token DO PORTAL: só vale o que vier depois de abrir o módulo.
  // O endereço da API mudou em 19/11/2026 (api.sistemaspleno.com/api/vistoria/ -> api-vistorias.sistemaspleno.com/):
  // aceita os dois e grava o endereço visto em api_base.txt (ao lado do token), que o pleno.py usa.
  const APIS = [/^https:\/\/api-vistorias\.sistemaspleno\.com\//, /^https:\/\/api\.sistemaspleno\.com\/api\/vistoria\//];
  let auth = null, base = null, modulo = false;
  ctx.on('request', r => {
    const h = r.headers(); if (!modulo || auth || !h.authorization) return;
    for (const re of APIS) { const m = r.url().match(re); if (m) { auth = h.authorization; base = m[0]; return; } }
  });
  await page.goto('https://plusvistorias.sistemaspleno.com/portal/login', { waitUntil: 'networkidle' });
  await page.fill('#usu_email', process.env.PLENO_USER);
  await page.fill('#usu_senha', process.env.PLENO_PASS);
  await clicarEntrar(page);
  await page.waitForTimeout(8000);
  modulo = true;
  await page.goto('https://plusvistorias.sistemaspleno.com/vistorias/vistorias', { waitUntil: 'networkidle' });
  for (let i = 0; i < 60 && !auth; i++) await page.waitForTimeout(1000); // a entrada no módulo pode levar 20 s ou mais
  await browser.close();
  if (!auth) { console.error('Login falhou: token do módulo Vistoria não capturado.'); process.exit(1); }
  fs.writeFileSync(out, auth);
  fs.writeFileSync(require('path').join(require('path').dirname(out), 'api_base.txt'), base);
  console.log('token ok', base);
})().catch(e => { console.error(e); process.exit(1); });
