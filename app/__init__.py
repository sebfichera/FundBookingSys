import os
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import Flask, redirect, url_for
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "default_secret")

    # Config DB
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        raise Exception("⚠️ DATABASE_URL non impostata!")
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"sslmode": "require"})

    from . import models
    models.db = scoped_session(sessionmaker(bind=engine))
    models.init_db_if_needed()

    # Registrazione blueprints
    from .routes.user import user_bp
    from .routes.admin import admin_bp
    from .routes.prenotazioni import prenotazioni_bp

    app.register_blueprint(user_bp, url_prefix="/user")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(prenotazioni_bp, url_prefix="/prenota")

    # ✅ Redirect root "/" -> "/user"
    @app.route("/")
    def root():
        return redirect(url_for("user_bp.home"))
    
     # Gestore errori globale
    @app.errorhandler(Exception)
    def handle_exception(e):
        import traceback
        print("❌ Errore globale:", e)
        traceback.print_exc()
        return "Internal Server Error", 500

    return app
