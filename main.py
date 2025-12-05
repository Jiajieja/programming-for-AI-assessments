from app import create_app
import os

if __name__ == "__main__":
    app = create_app()
    # host=0.0.0.0 Easy access from local machine/LAN；use_reloader=False Avoid port being bound repeatedly
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)