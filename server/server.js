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
      return;
    }

    if (msg.type === "relay" && myId) {
      const target = clients.get(msg.to);
      if (target) {
        target.send(JSON.stringify({ type: "relay", from: myId, payload: msg.payload }));
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
