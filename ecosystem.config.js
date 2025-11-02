module.exports = {
  apps: [{
    name: 'agentsmith',
    script: '/opt/agentsmith/venv/bin/python',
    args: '-m gunicorn --config gunicorn_config.py app:app',
    cwd: '/opt/agentsmith',
    interpreter: 'none',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
    env: {
      NODE_ENV: 'production'
    },
    error_file: '/var/log/pm2/agentsmith-error.log',
    out_file: '/var/log/pm2/agentsmith-out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
  }]
};

