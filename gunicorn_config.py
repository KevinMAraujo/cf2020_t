from os import environ
import multiprocessing

PORT = int(environ.get("PORT", 8080))

# Gunicorn config
bind = ":" + str(PORT)
workers = 1
threads = 1