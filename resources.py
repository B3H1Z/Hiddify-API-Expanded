import json
import re
from urllib.parse import urlparse
from hiddifypanel.panel.user import link_maker
from hiddifypanel.panel.user.user import add_headers, do_base_64, get_common_data
import requests
from flask import Response, abort, jsonify, request
from flask_restful import Resource
# from flask_simplelogin import login_required
import datetime
from hiddifypanel.models import *
from urllib.parse import urlparse
from hiddifypanel.panel import hiddify
from hiddifypanel.drivers import user_driver
# class AllResource(Resource):
#     def get(self):
#         return jsonify(
#             hiddify.dump_db_to_dict()
#         )


class UserResource(Resource):
    decorators = [hiddify.super_admin]

    def get(self):
        uuid = request.args.get('uuid')
        if uuid:
            user = user_by_uuid(uuid) or abort(404, "user not found")
            return jsonify(user.to_dict())

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
        uuid = request.args.get('uuid') or abort(422, "Parameter issue: 'uuid'")
        user = user_by_uuid(uuid) or abort(404, "user not found")
        user.remove()
        hiddify.quick_apply_users()
        return jsonify({'status': 200, 'msg': 'ok'})

class bulkUsers(Resource):
    def post(self):
        users = request.json
        hiddify.bulk_register_users(users)
        for user in users:
            user_driver.add_client(user)
        hiddify.quick_apply_users()

        return jsonify({'status': 200, 'msg': 'All users  updated successfully'})
    
    def get(self):
        return jsonify({'status': 200, 'msg': 'Hello Hidi-bot'})
    
class Sub(Resource):
    def get(self):
        uuid = request.args.get("uuid")
        base64 = request.args.get("base64")
        mode = "new"  # request.args.get("mode")
        if not uuid:
            return {"error": "UUID needed."}
        urls = []
        url = request.url
        BASE_URL = urlparse(url).scheme + "://" + urlparse(url).netloc
        PANEL_DIR = urlparse(url).path.split('/')
        url_sub = f"{BASE_URL}/{PANEL_DIR[1]}/{uuid}/all.txt"
        req = requests.get(url_sub)
        sub = None
        if req.status_code == 200:
            sub = req.text
        # c = get_common_data(uuid, mode)
        # sub = link_maker.make_v2ray_configs(**c)  # render_template('all_configs.txt', **c, base64=do_base_64)
        if not sub:
            return {"error": "we cant find sub."}
        try:
            with open("nodes.json", 'r') as f:
                urls = json.load(f)
        except Exception as e:
            return {"error": "we cant open file."}
        
        if urls:
            sub += "\n"
            for url in urls:
                BASE_URL = urlparse(url).scheme + "://" + urlparse(url).netloc
                PANEL_DIR = urlparse(url).path.split('/')
                url_sub = f"{BASE_URL}/{PANEL_DIR[1]}/{uuid}/all.txt"
                req = requests.get(url_sub)
                if req.status_code == 200:
                    configs = re.findall(r'(vless:\/\/[^\n]+)|(vmess:\/\/[^\n]+)|(trojan:\/\/[^\n]+)', req.text)
                    for config in configs:
                        if config[0]:
                            sub += config[0]+"\n"
                        elif config[1]:
                            sub += config[1]+"\n"
                        elif config[2]:
                            trojan_sni = re.search(r'sni=([^&]+)', config[2])
                            if trojan_sni:
                                if trojan_sni.group(1) == "fake_ip_for_sub_link":
                                    continue
                            sub += config[2]+"\n"
        if base64.lower() == "true":
            sub = do_base_64(sub)
        resp = Response(sub)
        resp.mimetype = "text/plain"
        return resp
        # return add_headers(sub, c)
    def post(self):
        list_url = request.get_json()
        with open("nodes.json", 'w') as f:
            json.dump(list_url, f)
       
        return jsonify({'status': 200, 'msg': 'Nodes was saved successfully'})


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
