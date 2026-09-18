from app.extensions import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    type = db.Column(db.String(20), nullable=False, index=True)  # SHOP / SERVICE / FOOD / SPECIALTY
    icon = db.Column(db.String(40), nullable=True)

    parent = db.relationship("Category", remote_side=[id], backref="subcategories")

    def __repr__(self):
        return f"<Category {self.name}>"
