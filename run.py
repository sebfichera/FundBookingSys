import os
from app import create_app

app = create_app()

print("✅ App Flask creata!")
for rule in app.url_map.iter_rules():
    print(f"Route: {rule} -> endpoint: {rule.endpoint}")

if __name__ == "__main__":
    debug_mode = os.environ.get("_DEBUG", "False").lower() == "true"
    print(f"🚀 Avvio server Flask (debug={debug_mode})")
    app.run(debug=debug_mode)
