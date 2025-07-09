from flask import Flask, send_from_directory, abort
import os

app = Flask(__name__)
REPORTS_DIR = os.path.join(os.getcwd(), 'reports')

@app.route('/reports/<string:symbol>.png')
def serve_report(symbol):
    filename = f"{symbol}_score.png"
    try:
        return send_from_directory(REPORTS_DIR, filename)
    except FileNotFoundError:
        abort(404, description=f"Grafika za token '{symbol}' nije pronađena.")

if __name__ == '__main__':
    app.run(port=8080, debug=True)