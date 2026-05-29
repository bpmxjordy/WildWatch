from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis

db = SQLAlchemy()
migrate = Migrate()
socketio = SocketIO()
cors = CORS()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per minute"])

redis_client: redis.Redis | None = None


def init_redis(app):
    global redis_client
    redis_client = redis.from_url(app.config["REDIS_URL"])
