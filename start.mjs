import { spawn } from "node:child_process";
import net from "node:net";

function waitForPort(port, host = "127.0.0.1", timeoutMs = 20000) {
  const started = Date.now();
  return new Promise((resolve, reject) => {
    const tryConnect = () => {
      const socket = net.connect({ port, host }, () => {
        socket.end();
        resolve();
      });
      socket.on("error", () => {
        socket.destroy();
        if (Date.now() - started > timeoutMs) {
          reject(new Error(`backend port ${port} not ready`));
          return;
        }
        setTimeout(tryConnect, 250);
      });
    };
    tryConnect();
  });
}

const backend = spawn("python3", ["server/main.py"], {
  stdio: "inherit",
  env: { ...process.env, MPT_LISTEN_HOST: "127.0.0.1", MPT_LISTEN_PORT: "8080" },
});

backend.on("exit", (code) => {
  if (code && code !== 0) {
    console.error(`backend exited with code ${code}`);
    process.exit(code);
  }
});

await waitForPort(8080);

const frontend = spawn("npx", ["vite", "--host", "0.0.0.0", "--port", "8501"], {
  stdio: "inherit",
});

frontend.on("exit", (code) => {
  backend.kill();
  process.exit(code ?? 0);
});

const stop = () => {
  frontend.kill();
  backend.kill();
};

process.on("SIGINT", stop);
process.on("SIGTERM", stop);
