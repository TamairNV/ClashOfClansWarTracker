from app import app
from waitress import serve

if __name__ == "__main__":
    print("🚀 Server is running on http://0.0.0.0:5001")
    # threads=6 handles multiple clan members clicking at once
    serve(app, host='0.0.0.0', port=5001, threads=6)

