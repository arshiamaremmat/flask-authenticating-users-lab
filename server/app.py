#!/usr/bin/env python3
from flask import Flask, make_response, request, session
from flask_migrate import Migrate
from flask_restful import Api, Resource

from models import db, Article, User, ArticlesSchema, UserSchema

app = Flask(__name__)
app.secret_key = b'Y\xf1Xz\x00\xad|eQ\x80t \xca\x1a\x10K'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.json.compact = False

# Init DB & API BEFORE registering resources
migrate = Migrate(app, db)
db.init_app(app)
api = Api(app)

# -------- Utilities --------
def dump_article(article):
    return ArticlesSchema().dump(article)

def dump_user(user):
    return UserSchema().dump(user)

# -------- Routes --------
class ClearSession(Resource):
    def delete(self):
        # Used by tests to reset session state
        session['page_views'] = None
        session['user_id'] = None
        return {}, 204

class IndexArticle(Resource):
    def get(self):
        articles = [dump_article(a) for a in Article.query.all()]
        return articles, 200

class ShowArticle(Resource):
    def get(self, id):
        # simple page-views limit
        session['page_views'] = 0 if not session.get('page_views') else session['page_views']
        session['page_views'] += 1

        if session['page_views'] <= 3:
            article = Article.query.filter(Article.id == id).first()
            if not article:
                return {'error': 'Article not found'}, 404
            return make_response(dump_article(article), 200)

        return {'message': 'Maximum pageview limit reached'}, 401

# ---- Auth for the lab ----
class Login(Resource):
    # POST /login { "username": "..." } -> sets session['user_id']
    def post(self):
        data = request.get_json() or {}
        username = data.get('username')
        if not username:
            return {'error': 'Username required'}, 400

        user = User.query.filter_by(username=username).first()
        if not user:
            return {'error': 'User not found'}, 404

        session['user_id'] = user.id
        return dump_user(user), 200

class Logout(Resource):
    # DELETE /logout -> clears session['user_id']
    def delete(self):
        session.pop('user_id', None)
        return {}, 204

class CheckSession(Resource):
    # GET /check_session -> returns user if logged in else 401
    def get(self):
        user_id = session.get('user_id')
        if not user_id:
            return {}, 401
        user = User.query.get(user_id)
        if not user:
            session.pop('user_id', None)
            return {}, 401
        return dump_user(user), 200

# ---- Register resources (after api = Api(app)) ----
api.add_resource(ClearSession, '/clear')
api.add_resource(IndexArticle, '/articles')
api.add_resource(ShowArticle, '/articles/<int:id>')
api.add_resource(Login, '/login')
api.add_resource(Logout, '/logout')
api.add_resource(CheckSession, '/check_session')

if __name__ == '__main__':
    app.run(port=5555, debug=True)
