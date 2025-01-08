from app import app, db, User
with app.app_context():

    db.create_all()
    admin = User(username="admin", email="admin@example.com", password="admin", role="admin")
    db.session.add(admin)
    db.session.commit()
    print("Admin user created successfully.")