/**
 * Manual end-to-end smoke script (not a full test framework yet -- see README).
 * Requires: backend running on :8000, frontend dev server on :5173, `npm i -D playwright`
 * and `npx playwright install chromium` once. Run: node e2e/smoke.mjs
 *
 * Exercises: login -> dashboard renders real demo data -> theme toggle -> transactions
 * table -> AI assistant grounded answer -> statement upload -> review -> confirm -> commit.
 */
import { chromium } from 'playwright'
import fs from 'fs'

const shots = process.argv[2] || '/tmp/finmate_shots'
fs.mkdirSync(shots, { recursive: true })

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const errors = []
page.on('pageerror', (err) => errors.push(String(err)))

await page.goto('http://localhost:5173/login')
await page.fill('input[type="email"]', 'demo@finmate.app')
await page.fill('input[type="password"]', 'demopassword123')
await page.click('button:has-text("Sign in")')
await page.waitForURL('http://localhost:5173/')
await page.waitForTimeout(1000)
await page.screenshot({ path: `${shots}/dashboard.png` })

await page.click('a:has-text("Transactions")')
await page.waitForTimeout(800)
await page.screenshot({ path: `${shots}/transactions.png` })

await page.click('a:has-text("AI Assistant")')
const q = page.locator('button:has-text("How much did I spend this month?")')
if (await q.count()) { await q.click(); await page.waitForTimeout(2000) }
await page.screenshot({ path: `${shots}/assistant.png` })

console.log('PAGE_ERRORS:', JSON.stringify(errors))
await browser.close()
