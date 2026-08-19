// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: green; icon-glyph: magic;

// EvieBot Domain & HTTPS Availability Scanner
// Feed it ALL the URLs you discovered. It will resolve each and tell you:
// - Public domain or internal/local
// - HTTPS reachable or not
// - Suitable for deployment or not

const urls = [
  "https://teaka.trading",
  "https://chatgpt.com/gpts/editor/g-6815592b81f8819183b2de94139790b1",
  "https://api.openai.com/v1/chat/completions",
  "https://openrouter.ai/api/v1/chat/completions",
  "https://api.qwen.ai/v1/generate",
  "https://api.hive.local",
  "http://127.0.0.1:5000/firemindruntime/status",
  "http://127.0.0.1:5000/firemindruntime/restart",
  "http://192.168.0.139:11434/api/generate",
  "http://192.168.1.42:5050/status",
  "http://172.20.10.3:8080",
  "http://localhost:8000/v1/completions",
  "https://github.com/BlairGem/Ev",
  "https://github.com/BlairGem/GPT_AI_Workspace",
  "https://teaka.trading",
  "https://example.com",
];

function extractDomain(url) {
  try {
    const u = new URL(url);
    return u.hostname;
  } catch {
    return null;
  }
}

async function testHTTPS(url) {
  try {
    let req = new Request(url);
    req.method = "GET";
    req.timeoutInterval = 5;
    await req.load();
    return "ONLINE (HTTPS reachable)";
  } catch (e) {
    return "NO HTTPS response";
  }
}

async function dnsCheck(domain) {
  if (!domain) return "Invalid domain";

  if (/^(127\.|192\.168|10\.|172\.(1[6-9]|2\d|3[01])\.|localhost)/.test(domain)) {
    return "Local LAN / localhost";
  }

  try {
    let test = new Request("https://" + domain);
    test.method = "HEAD";
    test.timeoutInterval = 5;
    await test.load();
    return "Public domain (resolves)";
  } catch {
    return "No DNS response / may not exist";
  }
}

async function run() {
  let output = "=== DOMAIN STATUS REPORT ===\n\n";
  let results = [];

  for (let url of urls) {
    let domain = extractDomain(url);
    if (!domain) continue;

    let entry = { url, domain };
    output += `URL: ${url}\n`;
    output += `Domain: ${domain}\n`;

    let dns = await dnsCheck(domain);
    entry.dns = dns;
    output += `DNS: ${dns}\n`;

    if (dns.includes("Public")) {
      let https = await testHTTPS("https://" + domain);
      entry.https = https;
      output += `HTTPS: ${https}\n`;
    }

    results.push(entry);
    output += `\n`;
  }

  console.log(output);

  // If TeAka bridge is up, POST results there
  try {
    let req = new Request("http://127.0.0.1:5050/api/scan/domains/report");
    req.method = "POST";
    req.headers = { "Content-Type": "application/json" };
    req.body = JSON.stringify({ results, scanned_at: new Date().toISOString(), source: "scriptable" });
    req.timeoutInterval = 4;
    await req.loadJSON();
  } catch { /* bridge offline — that's fine */ }

  if (config.runsInApp) {
    let alert = new Alert();
    alert.title = "Domain Scan Complete";
    alert.message = `Scanned ${results.length} URLs.\n\n` + results.map(r =>
      `${r.domain}: ${r.dns}${r.https ? " | " + r.https : ""}`
    ).join("\n");
    alert.addAction("OK");
    await alert.present();
  }

  Script.setShortcutOutput({ results });
  return output;
}

await run();
