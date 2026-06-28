module.exports = {
  apps: [
    {
      name: "vedaapex-api",
      script: "dist/server.js",
      instances: "max",
      exec_mode: "cluster",
      autorestart: true,
      watch: false,
      max_memory_restart: "512M",
      env: {
        NODE_ENV: "production",
      },
    },
    {
      name: "vedaapex-worker",
      script: "dist/worker.js",
      instances: 1,
      exec_mode: "fork",
      autorestart: true,
      watch: false,
      max_memory_restart: "768M",
      env: {
        NODE_ENV: "production",
        ENABLE_INLINE_QUEUE_WORKERS: "false",
      },
    },
  ],
};
