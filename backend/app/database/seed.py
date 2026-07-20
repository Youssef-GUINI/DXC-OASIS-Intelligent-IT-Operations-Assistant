from app.database.session import SessionLocal
from app.models.role import Role
from app.models.user import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed_roles(db):
    role_names = ["linux_engineer", "storage_engineer", "administrator"]
    roles = {}
    for name in role_names:
        existing = db.query(Role).filter(Role.name == name).first()
        if existing:
            roles[name] = existing
            continue
        role = Role(name=name)
        db.add(role)
        db.flush()  # pour obtenir role.id sans commit complet
        roles[name] = role
    db.commit()
    return roles


def seed_users(db, roles):
    test_users = [
        ("linux@oasis.com", "linux123", "linux_engineer"),
        ("storage@oasis.com", "storage123", "storage_engineer"),
        ("admin@oasis.com", "admin123", "administrator"),
    ]
    for email, plain_password, role_name in test_users:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"Utilisateur {email} existe déjà, ignoré.")
            continue
        user = User(
            email=email,
            hashed_password=pwd_context.hash(plain_password),
            full_name=email.split("@")[0].capitalize(),
            is_active=True,
            role_id=roles[role_name].id,
        )
        db.add(user)
    db.commit()


if __name__ == "__main__":
    db = SessionLocal()
    try:
        roles = seed_roles(db)
        print("Rôles créés/vérifiés :", list(roles.keys()))
        seed_users(db, roles)
        print("Utilisateurs de test créés.")
    finally:
        db.close()