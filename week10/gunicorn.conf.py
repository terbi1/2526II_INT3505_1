import multiprocessing
import os

workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"
threads = 2
worker_connections = 1000
timeout = 30
keepalive = 5
max_requests = 1000          
max_requests_jitter = 100    

bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"

accesslog = "logs/gunicorn_access.log"
errorlog = "logs/gunicorn_error.log"
loglevel = os.getenv("LOG_LEVEL", "info").lower()
access_log_format = (
    '{"time":"%(t)s","remote_ip":"%(h)s","method":"%(m)s",'
    '"path":"%(U)s","status":%(s)s,"bytes":%(B)s,"duration_ms":%(D)s}'
)

proc_name = "flask-production-api"
