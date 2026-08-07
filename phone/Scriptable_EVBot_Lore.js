// Scriptable — EVBot Lore Boot (iPhone, no PC required for OFFLINE)
// App: Scriptable (https://scriptable.app)
//
 // 1. Create a new script in Scriptable, paste this file.
 // 2. Edit TEAKA_HOST if you want ONLINE sync when PC bridge is up.
 // 3. Run from Scriptable home screen / Shortcuts / widget.
 //
 // Behavior:
 //   - Always writes local lore brain files (OFFLINE-capable)
 //   - If TEAKA_HOST responds, pushes brain + starts EVBot (ONLINE)

const TEAKA_HOST = "http://127.0.0.1:5050"; // change to PC LAN IP when available
const ROUTE_MODE = "AUTO"; // AUTO | ONLINE | OFFLINE
const MASTER_NAME = "therruedevil7.json";
const SHARED_NAME = "Cross_device_brain.json";
const LORE_NAME = "evbot_lore_state.json";

function nowStamp() {
  const d = new Date();
  return d.toISOString().replace("T", " ").replace(/\.\d+Z$/, "");
}

function log(lines, msg) {
  const row = `${nowStamp()} | ${msg}`;
  lines.push(row);
  console.log(row);
}

function fm() {
  // iCloud if available, else local Scriptable docs
  try {
    const i = FileManager.iCloud();
    i.documentsDirectory();
    return i;
  } catch (e) {
    return FileManager.local();
  }
}

function docsDir(fileManager) {
  return fileManager.documentsDirectory();
}

function readJson(fileManager, path, fallback) {
  if (!fileManager.fileExists(path)) {
    fileManager.writeString(path, JSON.stringify(fallback, null, 2));
    return JSON.parse(JSON.stringify(fallback));
  }
  try {
    return JSON.parse(fileManager.readString(path));
  } catch (e) {
    fileManager.writeString(path, JSON.stringify(fallback, null, 2));
    return JSON.parse(JSON.stringify(fallback));
  }
}

function writeJson(fileManager, path, obj) {
  fileManager.writeString(path, JSON.stringify(obj, null, 2));
}

function defaultMaster() {
  return {
    identity: "therruedevil7",
    device: "scriptable",
    sentinel: "AL7",
    phase: "Starforge Phase 3",
    linked: true,
    route_mode: ROUTE_MODE,
    lore: {
      script: "Scriptable_EVBot_Lore.js",
      evbot: "Firemind Phase 3",
      author: "Forgekeeper-Blair"
    },
    teaka: { mode: "paper", live_trading_enabled: false },
    runtime: {
      sentinel_al7: true,
      scriptable: true,
      bridge_ready: false,
      evbot_online: false
    },
    memory: { status: "local_master" },
    thoughts: []
  };
}

async function probe(host) {
  const req = new Request(`${host.replace(/\/$/, "")}/api/phone/status`);
  req.timeoutInterval = 4;
  try {
    return await req.loadJSON();
  } catch (e) {
    return null;
  }
}

async function pushBrain(host, brain) {
  const req = new Request(`${host.replace(/\/$/, "")}/api/phone/brain/sync`);
  req.method = "POST";
  req.headers = { "Content-Type": "application/json", Accept: "application/json" };
  req.body = JSON.stringify({
    source: MASTER_NAME,
    shared: SHARED_NAME,
    device: "scriptable",
    sentinel: "AL7",
    brain
  });
  req.timeoutInterval = 8;
  try {
    return await req.loadJSON();
  } catch (e) {
    return null;
  }
}

async function startEvbot(host) {
  const req = new Request(`${host.replace(/\/$/, "")}/api/evbot/start`);
  req.method = "POST";
  req.headers = { "Content-Type": "application/json", Accept: "application/json" };
  req.body = JSON.stringify({ source: "scriptable_lore" });
  req.timeoutInterval = 8;
  try {
    return await req.loadJSON();
  } catch (e) {
    return null;
  }
}

async function main() {
  const lines = [];
  const fileManager = fm();
  const documents = docsDir(fileManager);
  const masterPath = fileManager.joinPath(documents, MASTER_NAME);
  const sharedPath = fileManager.joinPath(documents, SHARED_NAME);
  const lorePath = fileManager.joinPath(documents, LORE_NAME);

  log(lines, `ST_BOOT: DOCUMENTS=${documents}`);
  log(lines, `ST_BOOT: MASTER=${masterPath}`);
  log(lines, `ST_BOOT: SHARED=${sharedPath}`);
  log(lines, `ST_BOOT: LORE=${lorePath}`);
  log(lines, `ST_BOOT: ROUTE_MODE=${ROUTE_MODE}`);
  log(lines, "ST_BOOT: SENTINEL_AL7_DAEMON_STARTED");
  log(lines, "ST_BOOT: SCRIPTABLE_LORE_ATTACHED");

  const master = readJson(fileManager, masterPath, defaultMaster());
  let shared = JSON.parse(JSON.stringify(master));
  shared.synced_from = MASTER_NAME;
  shared.synced_at = new Date().toISOString();
  shared.cross_device = true;
  shared.device = "scriptable";

  let route = "OFFLINE";
  let hostStatus = null;
  let pushResult = null;
  let evbotResult = null;
  const wantOnline = ["AUTO", "ONLINE", "ON"].includes(ROUTE_MODE);

  if (wantOnline) {
    hostStatus = await probe(TEAKA_HOST);
    if (hostStatus) {
      shared.runtime = shared.runtime || {};
      shared.runtime.bridge_ready = true;
      shared.host_status = {
        mode: hostStatus.mode,
        paper_trading: hostStatus.paper_trading,
        evbot_online: hostStatus.evbot_online
      };
      pushResult = await pushBrain(TEAKA_HOST, shared);
      evbotResult = await startEvbot(TEAKA_HOST);
      if (pushResult && pushResult.ok) {
        route = "ONLINE";
        shared.runtime.evbot_online = !!(evbotResult && evbotResult.ok);
      }
    }
  }

  // Always keep local lore runnable without PC
  const lore = {
    script: "Scriptable_EVBot_Lore.js",
    route,
    teaka_host: TEAKA_HOST,
    updated_at: new Date().toISOString(),
    evbot: {
      online: route === "ONLINE" && !!(evbotResult && evbotResult.ok),
      mode: "paper",
      local_ready: true,
      note:
        route === "ONLINE"
          ? "Synced to PC bridge and EVBot start requested"
          : "PC bridge not required — local lore state active on phone"
    },
    boot_log: lines.slice()
  };

  shared.route = route;
  shared.teaka_host = TEAKA_HOST;
  shared.lore = lore.evbot;
  master.memory = {
    last_confirmed: shared.synced_at,
    status: `synced_to_${SHARED_NAME}`,
    route
  };

  writeJson(fileManager, sharedPath, shared);
  writeJson(fileManager, masterPath, master);
  writeJson(fileManager, lorePath, lore);

  log(lines, `BRAIN_SYNCED: ${MASTER_NAME} -> ${SHARED_NAME} route=${route}`);
  log(lines, `LORE_READY: ${LORE_NAME} local_ready=true`);

  const summary = [
    `route=${route}`,
    `local lore ready`,
    route === "ONLINE" ? "EVBot start sent to bridge" : "OFFLINE phone lore only"
  ].join("\n");

  if (config.runsInApp) {
    const alert = new Alert();
    alert.title = "EVBot Lore";
    alert.message = summary + "\n\n" + lines.slice(-4).join("\n");
    alert.addAction("OK");
    await alert.present();
  }

  Script.setShortcutOutput({
    route,
    lorePath,
    sharedPath,
    masterPath,
    online: route === "ONLINE",
    log: lines
  });
}

await main();
