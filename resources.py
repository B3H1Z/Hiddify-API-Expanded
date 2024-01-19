# Description: Hiddify API Expanded Edition
import json
import re
from urllib.parse import urlparse
from flask import abort, jsonify, request
from flask_restful import Resource
# from flask_simplelogin import login_required
import datetime
from hiddifypanel.models import *
from urllib.parse import urlparse
from hiddifypanel.panel import hiddify
from hiddifypanel.drivers import user_driver
from hiddifypanel.models import User
from hiddifypanel.panel.database import db




class UserResource(Resource):
    decorators = [hiddify.super_admin]

    def get(self):
        uuid = request.args.get('uuid') 
        actoin = request.args.get('action')
        if uuid and not actoin:
            user = user_by_uuid(uuid) or abort(404, "user not found")
            return jsonify(user.to_dict())

        if uuid and actoin == 'delete':
            user = user_by_uuid(uuid) or abort(404, "user not found")
            try:
                db.session.delete(user)
                db.session.commit()
                user_driver.remove_client(user)
                hiddify.quick_apply_users()
                
                return jsonify({'status': 200, 'msg': 'ok user deleted'})
    
            except Exception as e:
                return jsonify({'status': 502, 'msg': 'user not deleted','error':str(e),'line':str(e.__traceback__.tb_lineno)})
        users = User.query.all() or abort(502, "WTF!")
        return jsonify([user.to_dict() for user in users])

    def post(self):
        data = request.json
        uuid = data.get('uuid') or abort(422, "Parameter issue: 'uuid'")
        hiddify.add_or_update_user(**data)
        user = user_by_uuid(uuid) or abort(502, "unknown issue! user is not added")
        user_driver.add_client(user)
        hiddify.quick_apply_users()
        return jsonify({'status': 200, 'msg': 'ok'})

    def delete(self):
        # uuid = request.args.get('uuid') or abort(422, "Parameter issue: 'uuid'")
        data = request.json
        uuid = data.get('uuid') or abort(422, "Parameter issue: 'uuid'")
        user = user_by_uuid(uuid) or abort(404, "user not found")
        user.remove()
        hiddify.quick_apply_users()
        return jsonify({'status': 200, 'msg': 'ok'})

class bulkUsers(Resource):
    decorators = [hiddify.super_admin]

    #def get(self):
    #    uuid_list  = request.json
    #    users = User.query.filter(User.uuid.in_(uuid_list)).all()
    #    return jsonify([user.to_dict() for user in users])

    def get(self):
        return jsonify({'status': 200, 'msg': 'Hello Hidi-bot'})
        
    def post(self):
        users = request.json
        hiddify.bulk_register_users(users)
        for newuser in users:
            user = user_by_uuid(newuser['uuid']) or abort(502, "unknown issue! user is not added")
            user_driver.add_client(user)
        hiddify.quick_apply_users()

        return jsonify({'status': 200, 'msg': 'All users  updated successfully'})
    
    
class Sub(Resource):
    decorators = [hiddify.super_admin]

    def get(self):
        return jsonify({'status': 200, 'msg': 'Hello Hidi-bot'})

    def post(self):
        list_url = request.json
        if not list_url:
            abort(502, "List is empty")
        try:
            with open("nodes.json", 'w') as f:
                json.dump(list_url, f)
                return jsonify({'status': 200, 'msg': 'Nodes was saved successfully'})
        except Exception as e:
            return jsonify({'status': 502, 'msg': 'Nodes File not created\n{e}'})
        
class hidybot_configs(Resource):
    decorators = [hiddify.super_admin]

    def get(self):
        return jsonify({'status': 200, 'msg': 'Hello Hidi-bot'})

    def post(self):
        configs = request.json
        if not configs:
            abort(502, "Configs is empty")
        try:
            with open("hidybotconfigs.json", 'w') as f:
                json.dump(configs, f)
                return jsonify({'status': 200, 'msg': 'configs was saved successfully'})
        except Exception as e:
            return jsonify({'status': 502, 'msg': 'configs File not created\n{e}'})


class AdminUserResource(Resource):
    decorators = [hiddify.super_admin]

    def get(self, uuid=None):
        uuid = request.args.get('uuid')
        if uuid:
            admin = get_admin_user_db(uuid) or abort(404, "user not found")
            return jsonify(admin.to_dict())

        admins = AdminUser.query.all() or abort(502, "WTF!")
        return jsonify([admin.to_dict() for admin in admins])

    def post(self):
        data = request.json
        uuid = data.get('uuid') or abort(422, "Parameter issue: 'uuid'")
        hiddify.add_or_update_admin(**data)

        return jsonify({'status': 200, 'msg': 'ok'})

    def delete(self):
        uuid = request.args.get('uuid') or abort(422, "Parameter issue: 'uuid'")
        admin = get_admin_user_db(uuid) or abort(404, "admin not found")
        admin.remove()
        return jsonify({'status': 200, 'msg': 'ok'})


# class DomainResource(Resource):
#     def get(self,domain=None):
#         if domain:
#             product = Domain.query.filter(Domain.domain==domain).first() or abort(204)
#             return jsonify(hiddify.domain_dict(product))
#         products = Domain.query.all() or abort(204)
#         return jsonify(
#             [hiddify.domain_dict(product) for product in products]
#         )
#     def post(self):
#         hiddify.add_or_update_domain(**request.json)
#         return jsonify({'status':200,'msg':'ok'})

# class ParentDomainResource(Resource):
#     def get(self,parent_domain=None):
#         if domain:
#             product = ParentDomain.query.filter(ParentDomain.domain==domain).first() or abort(204)
#             return jsonify(hiddify.parent_domain_dict(product))
#         products = ParentDomain.query.all() or abort(204)
#         return jsonify(
#             [hiddify.parent_domain_dict(product) for product in products]
#         )
#     def post(self):
#         hiddify.add_or_update_parent_domain(**request.json)
#         return jsonify({'status':200,'msg':'ok'})

# class ConfigResource(Resource):
#     def get(self,key=None,child_id=0):
#         if key:
#             return jsonify(hconfig(key,child_id))
#         return jsonify(get_hconfigs(child_id))

#     def post(self):
#         hiddify.add_or_update_config(**request.json)
#         return jsonify({'status':200,'msg':'ok'})

class HelloResource(Resource):
    def get(self):
        return jsonify({"status": 200, "msg": "ok"})


# class UpdateUsageResource(Resource):
#     def get(self):
#         return jsonify({"status": 200, "msg": "ok"})
