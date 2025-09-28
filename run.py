from app import create_app
app = create_app()

print("✅ App Flask creata!")
for rule in app.url_map.iter_rules():
    print(f"Route: {rule} -> endpoint: {rule.endpoint}")

if __name__ == "__main__":
    app.run(debug=True)
