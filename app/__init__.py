import os
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

def create_app():
    app = Flask(__name__)
    app.secret_key = "bjj_super_secret_key"

    # Config DB
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        raise Exception("⚠️ DATABASE_URL non impostata!")
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

    from . import models
    models.db = scoped_session(sessionmaker(bind=engine))
    models.init_db_if_needed()

    # Registrazione blueprints
    from .routes.user import user_bp
    from .routes.admin import admin_bp
    from .routes.prenotazioni import prenotazioni_bp

    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(prenotazioni_bp)

    return app
