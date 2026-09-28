/**
 * 浏览器端渲染验证（通过 Chrome DevTools Protocol）。
 *
 * 只用 Node 内置能力（child_process + fetch + 全局 WebSocket），不依赖任何 npm 包，
 * 也不需要 agent-browser 守护进程。用于「类型检查 + 构建通过」之后的那一步：
 * 确认页面**真的能渲染**，并捕获控制台错误、未捕获异常与失败请求。
 *
 * 用法：
 *   node scripts/browser_check.mjs <url> <输出png> [要点击的文本]
 *
 * 示例：
 *   node scripts/browser_check.mjs http://127.0.0.1:18080/ .verify/landing.png
 *   node scripts/browser_check.mjs "http://127.0.0.1:18080/result?plan_id=e2e00001" \
 *        .verify/graph.png 知识图谱
 *
 * 环境变量：
 *   CHROME_PATH  指定 Chrome/Chromium 可执行文件；未设置时按常见路径自动探测。
 */
import { spawn } from 'node:child_process'
import { existsSync, mkdirSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'

const PORT = Number(process.env.CDP_PORT || 9333)
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

function findChrome() {
  if (process.env.CHROME_PATH && existsSync(process.env.CHROME_PATH)) {
    return process.env.CHROME_PATH
  }
  const home = process.env.USERPROFILE || process.env.HOME || ''
  const localAppData = process.env.LOCALAPPDATA || ''
  const candidates = [
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    `${localAppData}/Google/Chrome/Application/chrome.exe`,
    `${home}/.agent-browser/browsers/chrome-154.0.8037.57/chrome.exe`,
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  ]
  const hit = candidates.find((p) => p && existsSync(p))
  if (!hit) {
    throw new Error('未找到 Chrome，请用 CHROME_PATH 环境变量指定')
  }
  return hit
}

const url = process.argv[2]
const outPng = process.argv[3]
const clickText = process.argv[4] || ''

if (!url || !outPng) {
  console.error('用法: node browser_check.mjs <url> <输出png> [要点击的文本]')
  process.exit(2)
}

let ws
let msgId = 0
const pending = new Map()
const consoleErrors = []
const pageErrors = []
const failedRequests = []

function send(method, params = {}) {
  const id = ++msgId
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject })
    ws.send(JSON.stringify({ id, method, params }))
    setTimeout(() => {
      if (pending.has(id)) {
        pending.delete(id)
        reject(new Error(`CDP 超时: ${method}`))
      }
    }, 30000)
  })
}

async function waitForDevtools() {
  for (let i = 0; i < 60; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/json/list`)
      const page = (await res.json()).find((t) => t.type === 'page')
      if (page?.webSocketDebuggerUrl) return page.webSocketDebuggerUrl
    } catch {
      /* 端口尚未就绪，继续等 */
    }
    await sleep(500)
  }
  throw new Error('DevTools 端口未就绪')
}

const chrome = spawn(
  findChrome(),
  [
    '--headless=new',
    '--disable-gpu',
    '--no-sandbox',
    '--hide-scrollbars',
    '--window-size=1440,1000',
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${process.env.TEMP || '/tmp'}/cdp-profile-${Date.now()}`,
    'about:blank',
  ],
  { stdio: 'ignore' }
)

try {
  ws = new WebSocket(await waitForDevtools())
  await new Promise((resolve, reject) => {
    ws.addEventListener('open', resolve, { once: true })
    ws.addEventListener('error', reject, { once: true })
  })

  ws.addEventListener('message', (ev) => {
    const msg = JSON.parse(ev.data)
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id)
      pending.delete(msg.id)
      msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg.result)
      return
    }
    if (msg.method === 'Runtime.consoleAPICalled' && msg.params.type === 'error') {
      consoleErrors.push(
        (msg.params.args || []).map((a) => a.value ?? a.description ?? a.type).join(' ')
      )
    }
    if (msg.method === 'Runtime.exceptionThrown') {
      const d = msg.params.exceptionDetails
      pageErrors.push(d.exception?.description || d.text)
    }
    if (msg.method === 'Network.loadingFailed') {
      failedRequests.push(`${msg.params.type} ${msg.params.errorText}`)
    }
    if (msg.method === 'Network.responseReceived' && msg.params.response.status >= 400) {
      failedRequests.push(`${msg.params.response.status} ${msg.params.response.url}`)
    }
  })

  await send('Runtime.enable')
  await send('Page.enable')
  await send('Network.enable')
  await send('Page.navigate', { url })
  await sleep(9000)

  if (clickText) {
    const expr = `(() => {
      const els = [...document.querySelectorAll('li, a, button, span, div')]
      const hit = els.reverse().find(e => e.textContent && e.textContent.trim() === ${JSON.stringify(clickText)})
      if (!hit) return 'NOT_FOUND'
      hit.click()
      return 'CLICKED'
    })()`
    const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true })
    console.log(`点击「${clickText}」→ ${r.result.value}`)
    await sleep(6000)
  }

  const probe = await send('Runtime.evaluate', {
    expression: `JSON.stringify({
      title: document.title,
      appChildren: (document.querySelector('#app')?.children.length ?? -1),
      bodyText: document.body.innerText.replace(/\\s+/g,' ').slice(0, 200),
      canvases: [...document.querySelectorAll('canvas')].map(c => c.width + 'x' + c.height)
    })`,
    returnByValue: true,
  })
  console.log('页面状态:', probe.result.value)

  mkdirSync(dirname(outPng), { recursive: true })
  const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true })
  writeFileSync(outPng, Buffer.from(shot.data, 'base64'))
  console.log('截图已保存:', outPng)

  console.log('控制台错误:', consoleErrors.length ? consoleErrors : '无')
  console.log('未捕获异常:', pageErrors.length ? pageErrors : '无')
  console.log('失败请求:', failedRequests.length ? failedRequests : '无')

  if (consoleErrors.length || pageErrors.length) process.exitCode = 1
} catch (e) {
  console.error('验证失败:', e.message)
  process.exitCode = 1
} finally {
  try {
    ws?.close()
  } catch {
    /* ignore */
  }
  chrome.kill()
  await sleep(500)
}
