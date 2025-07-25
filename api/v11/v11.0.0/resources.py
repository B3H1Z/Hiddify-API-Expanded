# Description: Hiddify API Expanded Edition
import json
import os
import re
import time
import subprocess
from urllib.parse import urlparse
from flask import jsonify, request
from apiflask import abort
from flask_restful import Resource
# from flask_simplelogin import login_required
import datetime
from hiddifypanel.models import *
from hiddifypanel.auth import login_required
from hiddifypanel.panel import hiddify
from hiddifypanel.drivers import user_driver
from hiddifypanel.database import db
from hiddifypanel import  cache, hutils

from hiddifypanel.VERSION import __version__

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

file_handler = logging.FileHandler('api-expanded.log')
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(name)s : %(message)s')
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

class UserResource(Resource):
    decorators = [login_required({Role.super_admin})]

    def get(self):
        uuid = request.args.get('uuid')
        actoin = request.args.get('action')
        if uuid and not actoin:
            user = User.by_uuid(uuid) or abort(404, "user not found")
            return jsonify(user.to_dict())
        if uuid and actoin == 'delete':
            user = User.by_uuid(uuid) or abort(404, "user not found")
            try:
                # db.session.delete(user)
                # db.session.commit()
                # user_driver.remove_client(user)
                user.remove()
                hiddify.quick_apply_users()
                
                return jsonify({'status': 200, 'msg': 'ok user deleted'})
    
            except Exception as e:
                return jsonify({'status': 502, 'msg': 'user not deleted','error':str(e),'line':str(e.__traceback__.tb_lineno)})
        users = User.query.all() or abort(502, "WTF!")
        return jsonify([user.to_dict() for user in users])  # type: ignore

    def post(self):
        data = request.json
        uuid = data.get('uuid') or abort(422, "Parameter issue: 'uuid'")
        User.add_or_update(**data)  # type: ignore
        user = User.by_uuid(uuid) or abort(502, "unknown issue! user is not added")
        user_driver.add_client(user)
        hiddify.quick_apply_users()
        return jsonify({'status': 200, 'msg': 'ok'})

    def delete(self):
        uuid = request.args.get('uuid') or abort(422, "Parameter issue: 'uuid'")
        user = User.by_uuid(uuid) or abort(404, "user not found")
        user.remove()
        hiddify.quick_apply_users()
        return jsonify({'status': 200, 'msg': 'ok'})

        # start aliz dev
    # desc : it is better to have a delete method to manage users more programatically :)
    def delete(self, uuid=None):
        uuid = request.args['uuid'] if 'uuid' in request.args else None
        if uuid:
            user = User.query.filter(User.uuid == uuid).first() or abort(204)
            if user is not None:
                User.remove_user(uuid)
                # user_driver.remove_client(uuid)
                hiddify.quick_apply_users()
                return jsonify({'status': 200, 'msg': 'ok'})
            else:
                return jsonify({'status': 204, 'msg': 'user not found'})
        else:
            return jsonify({'status': 204, 'msg': 'uuid not found'})
    # end aliz dev

class bulkUsers(Resource):
    decorators = [login_required({Role.super_admin})]

    def get(self):
        try:
            uuid_list  = request.json
            users = User.query.filter(User.uuid.in_(uuid_list)).all()
            return jsonify([user.to_dict() for user in users])
        except Exception as e:
            logger.exception(f"Error in get bulk users {e}")
            return jsonify({'status': 250, 'msg': f"error{e}"})

    # def get(self):
    #     return jsonify({'status': 200, 'msg': 'Hello Hidi-bot'})
        
    def post(self):
        start_time = time.time()
        lock_key = "lock-update-local-usage"
        LOCK_EXPIRE = 60   # Lock is valid for 1 minute
        MAX_WAIT = 180     # Max time to wait for lock
        WAIT_INTERVAL = 1  # Seconds between each check

        try:
            waited = 0
            while not cache.redis_client.set(lock_key, "locked", nx=True, ex=LOCK_EXPIRE):
                if waited >= MAX_WAIT:
                    return jsonify({
                        'status': 500,
                        'msg': f'Another usage update is still running after waiting {MAX_WAIT} seconds.'
                    })
                time.sleep(WAIT_INTERVAL)
                waited += WAIT_INTERVAL

            update = request.args.get('update') or False
            users = request.json

            if update:
                try:
                    update_start_time = time.time()
                    
                    bulk_update_users(users)
                    hiddify.quick_apply_users()
                    
                    update_end_time = time.time()
                    total_time = update_end_time - start_time
                    update_duration = update_end_time - update_start_time

                    return jsonify({
                        'status': 200,
                        'msg': f'All users updated by new method successfully. Total: {total_time:.2f}s, Update: {update_duration:.2f}s'
                    })
                except Exception as e:
                    logger.exception(f"Error in post bulk users for update {e}")
                    return jsonify({'status': 250, 'msg': f"error: {e}"})
            else:
                try:
                    process_start_time = time.time()
                    
                    User.bulk_register(users)
                    for newuser in users:
                        user = User.by_uuid(newuser['uuid']) or abort(202, f"Cannot find user {newuser['uuid']}")
                        user_driver.add_client(user)
                    hiddify.quick_apply_users()

                    process_end_time = time.time()
                    total_time = process_end_time - start_time
                    process_duration = process_end_time - process_start_time

                    return jsonify({
                        'status': 200,
                        'msg': f'All users updated successfully. Total: {total_time:.2f}s, Process: {process_duration:.2f}s'
                    })
                except Exception as e:
                    logger.exception(f"Error in registering bulk users {e}")
                    return jsonify({'status': 250, 'msg': f"error: {e}"})
        
        except Exception as e:
            logger.exception(f"Error acquiring lock: {e}")
            return jsonify({'status': 250, 'msg': f"error acquiring lock: {e}"})

        finally:
            try:
                cache.redis_client.delete(lock_key)
            except Exception as e:
                logger.warning(f"Failed to release Redis lock: {e}")


    
    def delete(self):
        try:
            users = request.json
            bulk_delete_users(users)
            hiddify.quick_apply_users()
            return jsonify({'status': 200, 'msg': 'All users  deleted successfully'})
        except Exception as e:
                logger.exception(f"Error in delete bulk users {e}")
                return jsonify({'status': 250, 'msg': f"error{e}"})
            
class Sub(Resource):
    decorators = [login_required({Role.super_admin})]

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
            logger.exception(f"Error in post nodes.json {e}")
            return jsonify({'status': 502, 'msg': 'Nodes File not created\n{e}'})
        
class hidybot_configs(Resource):
    decorators = [login_required({Role.super_admin})]

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
            logger.exception(f"Error in post hidybotconfigs.json {e}")
            return jsonify({'status': 502, 'msg': 'configs File not created\n{e}'})



class UpdateUsage(Resource):
    decorators = [login_required({Role.super_admin})]

    def get(self):
        lock_key = "lock-update-local-usage"
        LOCK_EXPIRE = 60  # قفل 5 دقیقه معتبره
        MAX_WAIT = 180     # حداکثر زمان انتظار
        WAIT_INTERVAL = 1  # فاصله بررسی

        waited = 0
        while not cache.redis_client.set(lock_key, "locked", nx=True, ex=LOCK_EXPIRE):
            if waited >= MAX_WAIT:
                return jsonify({
                    'status': 500,
                    'msg': 'Another usage update is still running after waiting {} seconds.'.format(MAX_WAIT)
                })
            time.sleep(WAIT_INTERVAL)
            waited += WAIT_INTERVAL
            
        # if not cache.redis_client.set(lock_key, "locked", nx=True, ex=LOCK_EXPIRE):
        #     return jsonify({
        #         'status': 500,
        #         'msg': 'Another usage update is running. Please try again in a few minutes.'
        #     })

        try:
            result = None

            try:
                subprocess.run(['pgrep', '-f', 'update-usage'], check=True)
            except subprocess.CalledProcessError:
                try:
                    result = subprocess.run(["python3", "-m", "hiddifypanel", "update-usage"], capture_output=True, text=True, check=True)
                except Exception as e:
                    return jsonify({'status': 502, 'msg': f'error\n{e}','code':str(e.__traceback__.tb_lineno)})

            if not result:
                return jsonify({'status': 502, 'msg': 'error\nresult is None','code':str(e.__traceback__.tb_lineno)})

            # if result.stderr:
            #     return jsonify({'status': 502, 'msg': f'error\n{result.stderr}','code':str(e.__traceback__.tb_lineno)})

            if result.stdout:
                return jsonify({'status': 200, 'msg': 'ok', 'output': result.stdout})
            else:
                return jsonify({'status': 502, 'msg': 'error\nresult.stdout is None','code':str(e.__traceback__.tb_lineno)})
        except Exception as e:
            return jsonify({'status': 502, 'msg': f'error\n{e}','code':str(e.__traceback__.tb_lineno)})
        
        
class Status(Resource):
    decorators = [login_required({Role.super_admin})]
    def get(self):
        config_file = '/usr/local/bin/hiddify-api-expanded/version.json'
        # cron_file = '/etc/cron.d/hiddify_usage_update'
        try:
            if os.path.isfile(config_file):
                with open(config_file, 'r') as f:
                    version = json.load(f)
                # with open(cron_file, 'r') as f:
                    # cron = f.read()
                # cron = re.sub(r'\s+', ' ', cron).strip()
                # if cron == '':
                    # cron = False
                # return jsonify({'status': 200, 'msg': 'ok', 'data': {'version': version, 'cron': cron, 'panel_version':__version__}})
                return jsonify({'status': 200, 'msg': 'ok', 'data': {'version': version, 'panel_version':__version__}})
            
            else:
                return jsonify({'status': 502, 'msg': 'error\nversion file not found'})
        except Exception as e:
            return jsonify({'status': 502, 'msg': f'error\n{e}','code':str(e.__traceback__.tb_lineno)})    
class AdminUserResource(Resource):
    decorators = [login_required({Role.super_admin})]

    def get(self, uuid=None):
        uuid = request.args.get('uuid')
        if uuid:
            admin = AdminUser.by_uuid(uuid) or abort(404, "user not found")
            return jsonify(admin.to_dict())

        admins = AdminUser.query.all() or abort(502, "WTF!")
        return jsonify([admin.to_dict() for admin in admins])

    def post(self):
        data = request.json
        uuid = data.get('uuid') or abort(422, "Parameter issue: 'uuid'")
        AdminUser.add_or_update(**data)  # type: ignore

        return jsonify({'status': 200, 'msg': 'ok'})

    def delete(self):
        uuid = request.args.get('uuid') or abort(422, "Parameter issue: 'uuid'")
        admin = AdminUser.by_uuid(uuid) or abort(404, "admin not found")
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

def bulk_update_users(users=[]):
    for u in users:
        bot_update_user(**u)
    db.session.commit()

def bot_update_user(**user):
    # if not is_valid():return
    try:
        dbuser = User.query.filter_by(uuid=user['uuid']).first()
        if user.get('start_date', ''):
            dbuser.start_date = hutils.convert.json_to_date(user['start_date'])
        dbuser.current_usage_GB = user['current_usage_GB']
        dbuser.last_online = hutils.convert.json_to_time(user.get('last_online')) or datetime.datetime.min
    except Exception as e:
            pass

def bulk_delete_users(users=[], commit=True):
    for u in users:
        user = User.by_uuid(u['uuid'])
        db.session.delete(user)
        user_driver.remove_client(user)
    db.session.commit()

def remove_lock(lock_file_path):
    try:
        os.remove(lock_file_path)
    except FileNotFoundError:
        pass
