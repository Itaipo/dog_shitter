const crypto = require("crypto");
const fs = require("fs");
const http = require("http");
const path = require("path");
const { WebSocketServer } = require("ws");

const PORT = 8080;
const SECRET = process.env.KORA_SECRET;
if (!SECRET) {
  console.error("KORA_SECRET is not set, refusing to start");
  process.exit(1);
}

// TURN relay (coturn on the same machine). Instead of one shared password that
// anyone loading the page could read, every client gets short-lived credentials:
// username = "<expiry timestamp>:<id>", credential = HMAC-SHA1(shared secret, username).
// coturn re-computes the HMAC itself, so the two only need to share the secret.
const TURN_SECRET = process.env.KORA_TURN_SECRET;
const TURN_HOST = process.env.KORA_TURN_HOST;
const TURN_TTL_SECONDS = 24 * 60 * 60;

function iceServersFor(id) {
  const servers = [{ urls: "stun:stun.l.google.com:19302" }];
  if (TURN_SECRET && TURN_HOST) {
    const username = `${Math.floor(Date.now() / 1000) + TURN_TTL_SECONDS}:${id}`;
    const credential = crypto.createHmac("sha1", TURN_SECRET).update(username).digest("base64");
    servers.push({
      urls: [
        `stun:${TURN_HOST}:3478`,
        `turn:${TURN_HOST}:3478?transport=udp`,
        `turn:${TURN_HOST}:3478?transport=tcp`,
      ],
      username,
      credential,
    });
  }
  return servers;
}

const VIEWER_PATH = path.join(__dirname, "public", "viewer.html");

function secretMatches(candidate) {
  if (typeof candidate !== "string") return false;
  const a = Buffer.from(candidate);
  const b = Buffer.from(SECRET);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

const server = http.createServer((req, res) => {
  const isRoot = req.url === "/" || req.url.startsWith("/?");
  if (req.method === "GET" && isRoot) {
    fs.readFile(VIEWER_PATH, (err, html) => {
      if (err) {
        res.writeHead(500);
        res.end("viewer page not found");
        return;
      }
      res.writeHead(200, {
        "Content-Type": "text/html; charset=utf-8",
        "Cache-Control": "no-store",
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
      });
      res.end(html);
    });
    return;
  }
  res.writeHead(404);
  res.end();
});

const wss = new WebSocketServer({ server });
const clients = new Map();

wss.on("connection", (ws) => {
  let myId = null;

  ws.on("message", (data) => {
    let msg;
    try {
      msg = JSON.parse(data);
    } catch {
      return;
    }

    if (msg.type === "register") {
      if (typeof msg.id !== "string" || !secretMatches(msg.secret)) {
        ws.send(JSON.stringify({ type: "error", message: "unauthorized" }));
        ws.close();
        return;
      }
      myId = msg.id;
      clients.set(myId, ws);
      console.log(`registered: ${myId}`);
      ws.send(JSON.stringify({ type: "registered", iceServers: iceServersFor(myId) }));
      return;
    }

    if (msg.type === "relay" && myId) {
      const target = clients.get(msg.to);
      if (target) {
        // Fresh credentials ride along with every relayed message, because the Pi
        // stays registered for days and its registration-time credentials expire.
        target.send(JSON.stringify({
          type: "relay",
          from: myId,
          payload: msg.payload,
          iceServers: iceServersFor(msg.to),
        }));
      }
    }
  });

  ws.on("close", () => {
    if (myId && clients.get(myId) === ws) {
      clients.delete(myId);
      console.log(`disconnected: ${myId}`);
    }
  });
});

server.listen(PORT, () => {
  console.log(`Signaling server listening on port ${PORT}`);
});
