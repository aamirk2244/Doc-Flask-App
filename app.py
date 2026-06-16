import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask

from settings import UPLOAD_DIR, INITIAL_DIR
from services import ensure_dirs


def create_app():
    app = Flask(__name__)
    app.config['UPLOAD_FOLDER'] = UPLOAD_DIR
    app.secret_key = 'dev-change-me'

    # configure logging
    os.makedirs('logs', exist_ok=True)
    handler = RotatingFileHandler('logs/app.log', maxBytes=1000000, backupCount=3)
    formatter = logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s')
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    app.logger.info('Starting app; upload_dir=%s initial_dir=%s', UPLOAD_DIR, INITIAL_DIR)

    # create upload dirs and initial dir
    ensure_dirs()

    # register routes
    from controllers import routes as controllers_routes
    controllers_routes.register_routes(app)

    return app


if __name__ == '__main__':
    create_app().run(debug=True)
