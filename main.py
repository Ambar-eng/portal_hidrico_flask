from app import create_flask_app
import urllib3
from urllib3.exceptions import InsecureRequestWarning

urllib3.disable_warnings()

urllib3.disable_warnings(InsecureRequestWarning)


flask_app = create_flask_app()


if __name__ == '__main__':
    flask_app.run(
        host='127.0.0.1',
        port=8080,
        debug=True,
        use_reloader=False
    )