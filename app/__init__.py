from flask import Flask, request, url_for, jsonify
from refresh_logic import IS_RELOADING

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    from app.routes.root import root_bp
    from app.routes.tab1 import tab1_bp
    from app.routes.tab2 import tab2_bp
    from app.routes.tab3 import tab3_bp
    from app.routes.tab4 import tab4_bp
    from app.routes.tab5 import tab5_bp
    from app.routes.tab6 import tab6_bp

    app.register_blueprint(root_bp)
    app.register_blueprint(tab1_bp, url_prefix="/tab1")
    app.register_blueprint(tab2_bp, url_prefix="/tab2")
    app.register_blueprint(tab3_bp, url_prefix="/tab3")
    app.register_blueprint(tab4_bp, url_prefix="/tab4")
    app.register_blueprint(tab5_bp, url_prefix="/tab5")
    app.register_blueprint(tab6_bp, url_prefix="/tab6")


    @app.route('/status', methods=['GET'])
    def status():
        return jsonify({"is_reloading": IS_RELOADING}), 200

    @app.context_processor
    def utility_processor():
        def update_url_param(key, value):
            args = request.args.copy()
            args[key] = value
            return url_for(request.endpoint, **args)
        return dict(update_url_param=update_url_param)

    return app