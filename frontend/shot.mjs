import { chromium } from 'playwright';

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });
page.on('pageerror', (err) => errors.push(String(err)));

await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });
await page.waitForTimeout(800);
await page.screenshot({ path: '/tmp/claude-1000/-home-rudra-Desktop-SIH26/caf20e0f-3988-44bd-ad1e-cfc17f6a5785/scratchpad/landing.png', fullPage: true });

// Navigate to risk map via the header nav link
await page.click('text=RISK MAP');
await page.waitForTimeout(2500);
await page.screenshot({ path: '/tmp/claude-1000/-home-rudra-Desktop-SIH26/caf20e0f-3988-44bd-ad1e-cfc17f6a5785/scratchpad/riskmap.png', fullPage: false });

console.log('ERRORS:', JSON.stringify(errors, null, 2));
await browser.close();
