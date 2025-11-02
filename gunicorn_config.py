# Gunicorn конфигурация для production
bind = "0.0.0.0:5005"
workers = 2
worker_class = "sync"
timeout = 120
keepalive = 5
accesslog = "-"
errorlog = "-"
loglevel = "info"

