"""
Example JWT auth API for TeAka / EV remote.
Secrets come from environment only — never hardcode.
"""
from __future__ import annotations

import os
from datetime import timedelta

from flask import Flask, jsonify, request
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt_identity,
    jwt_required,
)
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
CORS(app)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///teaka_auth.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "dev-only-jwt-change-me")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=1)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default="user")


@app.route("/register", methods=["POST"])
def register():
    data = request.json or {}
    if User.query.filter_by(email=data.get("email")).first():
        return jsonify({"msg": "Email already registered"}), 409
    hashed_pw = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
    user = User(email=data["email"], password=hashed_pw)
    db.session.add(user)
    db.session.commit()
    return jsonify({"msg": "User created"}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.json or {}
    user = User.query.filter_by(email=data.get("email")).first()
    if not user or not bcrypt.check_password_hash(user.password, data.get("password", "")):
        return jsonify({"msg": "Bad credentials"}), 401
    token = create_access_token(identity={"email": user.email, "role": user.role})
    return jsonify({"token": token})


@app.route("/me", methods=["GET"])
@jwt_required()
def me():
    return jsonify(get_jwt_identity())


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=False, port=int(os.environ.get("AUTH_PORT", "5000")))
