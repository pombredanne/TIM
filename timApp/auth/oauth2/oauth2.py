from typing import List, Dict

from authlib.integrations.flask_oauth2 import AuthorizationServer, ResourceProtector
from authlib.integrations.sqla_oauth2 import create_save_token_func, \
    create_bearer_token_validator
from authlib.oauth2.rfc6749 import grants
from flask import Flask

from timApp.auth.oauth2.models import OAuth2Client, OAuth2Token, OAuth2AuthorizationCode
from timApp.timdb.sqa import db
from timApp.user.user import User
from tim_common.marshmallow_dataclass import class_schema

ALLOWED_CLIENTS: Dict[str, OAuth2Client] = {}


class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
    TOKEN_ENDPOINT_AUTH_METHODS = [
        'client_secret_basic',
        'client_secret_post',
        # TODO: Do we need 'none'?
    ]

    def save_authorization_code(self, code, request):
        auth_code = OAuth2AuthorizationCode(
            code=code,
            client_id=request.client.client_id,
            redirect_uri=request.redirect_uri,
            scope=request.scope,
            user_id=request.user.id,
        )
        db.session.add(auth_code)
        db.session.commit()
        return auth_code

    def query_authorization_code(self, code, client):
        auth_code = OAuth2AuthorizationCode.query.filter_by(code=code, client_id=client.client_id).first()
        if auth_code and not auth_code.is_expired():
            return auth_code

    def delete_authorization_code(self, authorization_code):
        db.session.delete(authorization_code)
        db.session.commit()

    def authenticate_user(self, authorization_code):
        return User.query.get(authorization_code.user_id)


def query_client(client_id: str):
    if client_id not in ALLOWED_CLIENTS:
        raise Exception(f"OAuth2 client {client_id} is not in allowed list")
    return ALLOWED_CLIENTS[client_id]


save_token = create_save_token_func(db.session, OAuth2Token)
auth_server = AuthorizationServer(query_client=query_client, save_token=save_token)

require_oauth = ResourceProtector()
"""Special decorator to request for permission scopes"""


def init_oauth(app: Flask):
    global ALLOWED_CLIENTS
    clients = app.config.get('OAUTH2_CLIENTS', [])
    schema = class_schema(OAuth2Client)()
    clients_obj: List[OAuth2Client] = [schema.load(c) for c in clients]
    ALLOWED_CLIENTS = {c.client_id: c for c in clients_obj}

    auth_server.init_app(app)
    auth_server.register_grant(AuthorizationCodeGrant)

    # TODO: Do we need to support revocation?

    from timApp.auth.oauth2.routes import oauth
    app.register_blueprint(oauth)

    bearer_cls = create_bearer_token_validator(db.session, OAuth2Token)
    require_oauth.register_token_validator(bearer_cls())
