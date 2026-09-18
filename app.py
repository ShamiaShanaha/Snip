import os
import string
import secrets

from flask import Flask, request, jsonify, redirect, render_template
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:///snip.db"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True)
    short_code = Column(String(10), unique=True, nullable=False)
    original_url = Column(String(2048), nullable=False)
    clicks = Column(Integer, default=0, nullable=False)


Base.metadata.create_all(engine)

app = Flask(__name__)


def generate_short_code(length=6):
    characters = string.ascii_letters + string.digits
    return "".join(
        secrets.choice(characters)
        for _ in range(length)
    )


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html")

    data = request.get_json(silent=True) or {}
    original_url = data.get("url")

    if not original_url:
        return jsonify({
            "error": "Missing 'url' in request body"
        }), 400

    session = SessionLocal()

    try:
        short_code = generate_short_code()

        while session.query(Link).filter_by(
            short_code=short_code
        ).first():
            short_code = generate_short_code()

        link = Link(
            short_code=short_code,
            original_url=original_url,
            clicks=0
        )

        session.add(link)
        session.commit()

        return jsonify({
            "short_code": short_code,
            "short_url": request.host_url + short_code,
            "original_url": original_url
        }), 201

    finally:
        session.close()


@app.route("/<short_code>")
def go_to_url(short_code):
    session = SessionLocal()

    try:
        link = session.query(Link).filter_by(
            short_code=short_code
        ).first()

        if not link:
            return jsonify({
                "error": "Short link not found"
            }), 404

        link.clicks += 1
        session.commit()

        return redirect(link.original_url)

    finally:
        session.close()


@app.route("/stats/<short_code>")
def stats(short_code):
    session = SessionLocal()

    try:
        link = session.query(Link).filter_by(
            short_code=short_code
        ).first()

        if not link:
            return jsonify({
                "error": "Short link not found"
            }), 404

        return jsonify({
            "short_code": link.short_code,
            "original_url": link.original_url,
            "clicks": link.clicks
        })

    finally:
        session.close()


@app.route("/health")
def health():
    return jsonify({
        "status": "ok"
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000
    )

