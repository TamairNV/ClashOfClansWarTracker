from decimal import Decimal
from flask import Flask
from flask.json import tojson_filter # Flask's tojson

def test_decimal_json():
    # Flask app context might be needed for tojson filter default behavior
    app = Flask(__name__)
    
    data = [Decimal('2.5'), Decimal('3.0')]
    
    try:
        with app.app_context():
            json_out = tojson_filter(data)
            print(f"✅ Success: {json_out}")
    except TypeError as e:
        print(f"❌ Failed as expected: {e}")
    except Exception as e:
        print(f"❌ Other error: {e}")

if __name__ == "__main__":
    test_decimal_json()
