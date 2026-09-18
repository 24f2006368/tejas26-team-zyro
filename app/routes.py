def register_blueprints(app):
    from app.controllers.main_controller import main_bp
    from app.controllers.auth_controller import auth_bp
    from app.controllers.customer_controller import customer_bp
    from app.controllers.shopkeeper_controller import shopkeeper_bp
    from app.controllers.admin_controller import admin_bp
    from app.controllers.search_controller import search_bp
    from app.controllers.map_controller import api_bp
    from app.controllers.product_controller import product_bp
    from app.controllers.chat_controller import chat_bp
    from app.controllers.reservation_controller import reservation_bp
    from app.controllers.review_controller import review_bp
    from app.controllers.delivery_controller import delivery_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(shopkeeper_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(reservation_bp)
    app.register_blueprint(review_bp)
    app.register_blueprint(delivery_bp)

