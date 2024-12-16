# Description: Hiddify API Expanded Edition
import user_agents
import datetime
import random
import re

from flask import render_template, request, Response, g
from apiflask import abort
from flask_classful import FlaskView, route
from flask_babel import gettext as _


from hiddifypanel.auth import login_required
from hiddifypanel.database import db
from hiddifypanel.panel import hiddify
from hiddifypanel.models import *
from hiddifypanel import hutils

import requests
import json

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

file_handler = logging.FileHandler('api-expanded.log')
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(name)s : %(message)s')
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

class UserView(FlaskView):

    def index(self):
        return self.auto_sub()

    @route('/ua')
    def user_agent(self):
        ua= str(g.user_agent)+"\n"+str(request.user_agent)
        print(ua)
        return ua

    def auto_sub(self):
        if g.user_agent['is_browser']:
            return self.new()
        return self.get_proper_config() or self.links_imp(base64=True)

    # former /sub/ or /sub (it was auto actually but we named it as /sub/)
    @route('/auto/')
    @route('/auto')
    @login_required(roles={Role.user})
    def force_sub(self):
        return self.get_proper_config() or self.links_imp(base64=False)

    # region new endpoints
    @route("/sub/")
    @route("/sub")
    @login_required(roles={Role.user})
    def sub(self):
        '''Returns proxy links (not base64 encoded)'''
        return self.links_imp(base64=False)

    @route("/sub64/")
    @route("/sub64")
    @login_required(roles={Role.user})
    def sub64(self):
        '''Returns proxy links (base64 encoded)'''
        return self.links_imp(base64=True)

    
    
    @route("/xray/")
    @route("/xray")
    @login_required(roles={Role.user})
    def xray(self):
        '''Returns Xray JSON proxy config'''
        # if not hconfig(ConfigEnum.sub_full_xray_json_enable):
        #     return 'The Full Xray subscription is disabled'
        c = get_common_data(g.account.uuid, mode="new")
        configs = hutils.proxy.xrayjson.configs_as_json(c['domains'], c['user'], c['expire_days'], c['profile_title'])
        bot_configs = None
        username = False
        try:
            with open("hidybotconfigs.json", 'r') as f:
                bot_configs = json.load(f)
        except Exception as e:
            logger.exception(f"Error in loading hidybotconfigs.json {e}")
        if bot_configs:
            username = bot_configs.get("username", False)
        if username:
            try:
                configs_list_for_name = json.loads(configs)
                encoded_name = f" 👤:{c['user'].name}"
                configs_list_for_name[0]['remarks'] = configs_list_for_name[0]['remarks'] + encoded_name
                configs = json.dumps(configs_list_for_name)
            except Exception as e:
                logger.exception(f"Error in cheanging name {e}")
        try:
            with open("nodes.json", 'r') as f:
                urls = json.load(f)
        except Exception as e:
            logger.exception(f"Error in loading nodes.json {e}")
        
        if urls:
            configs_list = json.loads(configs)
            for url in urls:
                try:
                    url_sub = f"{url}/{g.account.uuid}/xray2/"
                    req = requests.get(url_sub,timeout=10)
                    if req.status_code == 200:
                        nodes_configs = req.text
                        node_configs_list = json.loads(nodes_configs)
                        if node_configs_list:
                            configs_list.extend(node_configs_list)
                except Exception as e:
                    logger.exception(f"Error in loading {url} configs {e}")
            configs = json.dumps(configs_list, indent=2, cls=hutils.proxy.ProxyJsonEncoder)
        return add_headers(configs, c, 'application/json')
    
    @route("/xray2/")
    @route("/xray2")
    @login_required(roles={Role.user})
    def xray2(self):
        '''Returns Xray JSON proxy config'''
        # if not hconfig(ConfigEnum.sub_full_xray_json_enable):
        #     return 'The Full Xray subscription is disabled'
        urls = None
        c = get_common_data(g.account.uuid, mode="new")
        configs = hutils.proxy.xrayjson.configs_as_json(c['domains'], c['user'], c['expire_days'], c['profile_title'])
        return add_headers(configs, c, 'application/json')
    

    @route("/singbox/")
    @route("/singbox")
    @login_required(roles={Role.user})
    def singbox_full(self):
        '''Returns singbox client JSON config'''
        return self.full_singbox_imp()

    @route("/singbox-ssh/")
    @route("/singbox-ssh")
    @login_required(roles={Role.user})
    def singbox_ssh(self):
        '''Returns singbox client JSON config (ssh)'''
        return self.singbox_ssh_imp()

    @route("/wireguard/")
    @route("/wireguard")
    @login_required(roles={Role.user})
    def wireguard(self):
        '''Returns wireguard client config'''
        c = get_common_data(g.account.uuid, 'new')
        wireguards = []
        servers = set()
        for pinfo in hutils.proxy.get_valid_proxies(c['domains']):
            if pinfo['proto'] != ProxyProto.wireguard:
                continue
            wireguards.append(pinfo)

            

        if not len(wireguards):
            abort(404)
        resp =""
        for wg in wireguards:
            resp +=f'#========={wg["extra_info"]} {wg["name"]}================\n'
            resp+=hutils.proxy.wireguard.generate_wireguard_config(wg)
            resp+="\n\n"
        return add_headers(resp, c)

        # return self.singbox_ssh_imp()

    @route("/clash/")
    @route("/clash")
    @login_required(roles={Role.user})
    def clash(self):
        '''Returns clash client config'''
        return self.clash_config_imp(meta_or_normal="normal")

    @route("/clashmeta/")
    @route("/clashmeta")
    @login_required(roles={Role.user})
    def clashmeta(self):
        '''Returns clash meta client config'''
        return self.clash_config_imp(meta_or_normal="meta")
    # endregion

    @ route('/new/')
    @ route('/new')
    @login_required(roles={Role.user})
    def new(self):
        conf = self.get_proper_config()
        if conf:
            return conf

        c = get_common_data(g.account.uuid, mode="new")
        user_agent = user_agents.parse(request.user_agent.string)
        # return render_template('home/multi.html', **c, ua=user_agent)
        return render_template('new.html', **c, ua=user_agent)

    def get_proper_config(self):
        '''Returns proper config based on user agent'''
        if g.user_agent['is_browser']:
            return None

        ua = request.user_agent.string
        if g.user_agent['is_singbox'] or re.match('^(HiddifyNext|Dart|SFI|SFA)', ua, re.IGNORECASE):
            return self.full_singbox_imp()

        if re.match('^(Clash-verge|Clash-?Meta|Stash|NekoBox|NekoRay|Pharos|hiddify-desktop)', ua, re.IGNORECASE):
            return self.clash_config_imp(meta_or_normal="meta")
        if re.match('^(Clash|Stash)', ua, re.IGNORECASE):
            return self.clash_config_imp(meta_or_normal="normal")

        if hconfig(ConfigEnum.sub_full_xray_json_enable):
            # return the old "Subscription link b64" sub if the "Full Xray" sub is disabled (wanted by user)
            if g.user_agent.get('is_v2rayng') and hutils.flask.is_client_version(hutils.flask.ClientVersion.v2ryang, 1, 8, 17):
                return self.xray()
            elif g.user_agent.get('is_streisand'):
                return self.xray()

        if re.match('^(Hiddify|FoXray|Fair|v2rayNG|SagerNet|Shadowrocket|V2Box|Loon|Liberty|Streisand)', ua, re.IGNORECASE):
            return self.links_imp(base64=True)

    @route('/clash/<meta_or_normal>/proxies.yml')
    @route('/clash/proxies.yml')
    @login_required(roles={Role.user})
    def clash_proxies(self, meta_or_normal="normal"):
        mode = request.args.get("mode")
        domain = request.args.get("domain", None)

        c = get_common_data(g.account.uuid, mode, filter_domain=domain)
        resp = Response(render_template('clash_proxies.yml',
                        meta_or_normal=meta_or_normal, **c))
        resp.mimetype = "text/plain"

        return resp

    # @ route('/report', methods=["POST"])
    # @login_required(roles={Role.user})
    # def report(self):

    #     # THE REPORT MODEL IS NOT COMPLETED YET.

    #     data = request.get_json()
    #     user_ip = hutils.network.auto_ip_selector.get_real_user_ip()
    #     report = Report()
    #     report.asn_id = hutils.network.auto_ip_selector.get_asn_id(user_ip)
    #     report.country = hutils.network.auto_ip_selector.get_country(user_ip)

    #     city_info = hutils.network.auto_ip_selector.get_city(user_ip)
    #     report.city = city_info['name']
    #     report.latitude = city_info['latitude']
    #     report.longitude = city_info['longitude']
    #     report.accuracy_radius = city_info['accuracy_radius']

    #     report.date = datetime.datetime.now()
    #     sub_update_time = data['sub_update_time']
    #     sub_url = data['sub_url']

    #     db.session.add(report)
    #     db.session.commit()
    #     proxy_map = {p.name: p.id for p in Proxy.query.all()}

    #     for name, ping in data['pings']:
    #         detail = ReportDetail()
    #         detail.report_id = report.id
    #         detail.proxy_id = proxy_map.get(name, -1)
    #         del proxy_map[name]
    #         if detail.proxy_id < 0:
    #             print("Error. Proxy not found!")
    #             continue
    #         detail.ping = ping
    #         db.session.add(detail)
    #     db.session.commit()

    @ route('/clash/<typ>.yml', methods=["GET", "HEAD"])
    @ route('/clash/<meta_or_normal>/<typ>.yml', methods=["GET", "HEAD"])
    @login_required(roles={Role.user})
    def clash_config_imp(self, meta_or_normal="normal", typ="all.yml"):
        mode = request.args.get("mode")
        if meta_or_normal == 'meta' and not hconfig(ConfigEnum.sub_full_clash_meta_enable):
            return 'The Clash meta subscription is disabled'
        elif meta_or_normal == 'normal' and not hconfig(ConfigEnum.sub_full_clash_enable):
            return 'The Clash subscription is disabled'

        c = get_common_data(g.account.uuid, mode)

        hash_rnd = random.randint(0, 1000000)  # hash(f'{c}')
        if request.method == 'HEAD':
            resp = ""
        else:
            resp = render_template(
                'clash_config.yml', typ=typ, meta_or_normal=meta_or_normal, **c, hash=hash_rnd)

        return add_headers(resp, c)

    @ route('/full-singbox.json', methods=["GET", "HEAD"])
    @login_required(roles={Role.user})
    def full_singbox_imp(self):
        # if not hconfig(ConfigEnum.sub_full_singbox_enable):
        #     return 'The Full Singbox subscription is disabled'

        mode = "new"  # request.args.get("mode")
        c = get_common_data(g.account.uuid, mode)
        # response.content_type = 'text/plain';
        if request.method == 'HEAD':
            resp = ""
        else:
            resp = hutils.proxy.singbox.configs_as_json(**c)

        return add_headers(resp, c, 'application/json')

    @ route('/singbox.json', methods=["GET", "HEAD"])
    @login_required(roles={Role.user})
    def singbox_ssh_imp(self):
        if not hconfig(ConfigEnum.ssh_server_enable):
            return "The SSH server is disabled"
        # elif not hconfig(ConfigEnum.sub_singbox_ssh_enable):
        #     return "The Singbox: SSH subscription is disabled"

        mode = "new"  # request.args.get("mode")
        c = get_common_data(g.account.uuid, mode)
        # response.content_type = 'text/plain';
        if request.method == 'HEAD':
            resp = ""
        else:
            resp = render_template('singbox_config.json', **c, host_keys=hutils.proxy.get_ssh_hostkeys(get_hconfigs(),True),
                                   ssh_client_version=hiddify.get_ssh_client_version(user), ssh_ip=hutils.network.get_direct_host_or_ip(4), base64=False)

        return add_headers(resp, c)

    @route('/all.txt', methods=["GET", "HEAD"])
    @login_required(roles={Role.user})
    def links_imp(self, base64=False):
        '''Returns subscription links (base64 or not)'''
        mode = "new"  # request.args.get("mode")
        base64 = base64 or request.args.get("base64", "").lower() == "true"
        bot_configs = None
        username = False
        randomize = False
        randomize_mode = "servers"
        try:
            with open("hidybotconfigs.json", 'r') as f:
                bot_configs = json.load(f)
        except Exception as e:
            logger.exception(f"Error in loading hidybotconfigs.json {e}")
        if bot_configs:
            username = bot_configs.get("username", False)
            randomize = bot_configs.get("randomize", False)
            randomize_mode = bot_configs.get("randomize_mode", "servers")
        # if base64 and not hconfig(ConfigEnum.sub_full_links_b64_enable):
        #     return 'The Subscription link b64 is disabled'
        # if not base64 and not hconfig(ConfigEnum.sub_full_links_enable):
        #     return 'The Subscription link is disabled'

        c = get_common_data(g.account.uuid, mode)
        urls = None
        resp = None
        # response.content_type = 'text/plain';
        if request.method == 'HEAD':
            resp = ""
        else:
            # render_template('all_configs.txt', **c, base64=hutils.encode.do_base_64)
            resp = hutils.proxy.xray.make_v2ray_configs(c['domains'], c['user'], c['expire_days'], c['ip_debug'])
            
        if username:
            # شامل اینتر اخر نمیشود
            trojan_pattern = r'^trojan:\/\/.*\bsni=fake_ip_for_sub_link\b.*[^\n]'
            trojan_urls = re.findall(trojan_pattern, resp)
            if trojan_urls:
                fake_config = trojan_urls[0]
                encoded_name = f" 👤:{c['user'].name}"
                new_fake_config = fake_config + encoded_name
                resp = resp.replace(fake_config, new_fake_config)
        if randomize:
            if randomize_mode == "servers":
                fake_config = ""
                configs_list = []
                # configs = re.findall(r'(vless:\/\/[^\n]+)|(vmess:\/\/[^\n]+)|(trojan:\/\/[^\n]+)|tuic:\/\/[^\n]+)|(hysteria2:\/\/[^\n]+)|(hysteria:\/\/[^\n]+)', resp)
                #شامل اینتر اخر می شود
                trojan_pattern = r'^trojan:\/\/.*\bsni=fake_ip_for_sub_link\b.*\n'
                trojan_urls = re.findall(trojan_pattern, resp)
                if trojan_urls:
                    fake_config = trojan_urls[0] 
                    resp = resp.replace(fake_config, "")
                    fake_config += '\n'
                configs_list.append(resp)
                # configs_list = resp.split("\n")
                try:
                    with open("nodes.json", 'r') as f:
                        urls = json.load(f)
                except Exception as e:
                    logger.exception(f"Error in loading nodes.json {e}")
                
                if urls:
                    for url in urls:
                        try:
                            url_sub = f"{url}/{g.account.uuid}/all2.txt"
                            req = requests.get(url_sub,timeout=10)
                            if req.status_code == 200:
                                nodes_configs = req.text
                                trojan_pattern = r'^trojan:\/\/.*\bsni=fake_ip_for_sub_link\b.*\n'
                                trojan_urls = re.findall(trojan_pattern, nodes_configs)
                                if trojan_urls:
                                    node_fake_config = trojan_urls[0]
                                    nodes_configs = nodes_configs.replace(node_fake_config, "")
                                # configs_list.append("\n")
                                configs_list.append(nodes_configs)
                                # configs_list += nodes_configs.split("\n")
                        except Exception as e:
                            logger.exception(f"Error in loading {url} configs {e}")
                if configs_list:
                    random.shuffle(configs_list)
                    resp = fake_config + '\n'.join(configs_list)
            elif randomize_mode == "configs":
                try:
                    with open("nodes.json", 'r') as f:
                        urls = json.load(f)
                except Exception as e:
                    logger.exception(f"Error in loading nodes.json {e}")
                
                if urls:
                    for url in urls:
                        resp += "\n"
                        try:
                            url_sub = f"{url}/{g.account.uuid}/all2.txt"
                            req = requests.get(url_sub,timeout=10)
                            if req.status_code == 200:
                                nodes_configs = req.text
                                trojan_pattern = r'^trojan:\/\/.*\bsni=fake_ip_for_sub_link\b.*\n'
                                trojan_urls = re.findall(trojan_pattern, nodes_configs)
                                if trojan_urls:
                                    node_fake_config = trojan_urls[0]
                                    nodes_configs = nodes_configs.replace(node_fake_config, "")
                                resp += nodes_configs
                        except Exception as e:
                            logger.exception(f"Error in loading {url} configs {e}")
                configs = [line for line in resp.split('\n') if line.strip() != '']
                if len(configs) > 2:
                    first_configs = configs[0:1]
                    rest_configs = configs[1:]
                    random.shuffle(rest_configs)
                    configs = first_configs + rest_configs
                resp = '\n'.join(configs)
        else:
            try:
                with open("nodes.json", 'r') as f:
                    urls = json.load(f)
            except Exception as e:
                logger.exception(f"Error in loading nodes.json {e}")
            
            if urls:
                for url in urls:
                    resp += "\n"
                    try:
                        url_sub = f"{url}/{g.account.uuid}/all2.txt"
                        req = requests.get(url_sub,timeout=10)
                        if req.status_code == 200:
                            nodes_configs = req.text
                            trojan_pattern = r'^trojan:\/\/.*\bsni=fake_ip_for_sub_link\b.*\n'
                            trojan_urls = re.findall(trojan_pattern, nodes_configs)
                            if trojan_urls:
                                node_fake_config = trojan_urls[0]
                                nodes_configs = nodes_configs.replace(node_fake_config, "")
                            resp += nodes_configs
                    except Exception as e:
                        logger.exception(f"Error in loading {url} configs {e}")
        if base64:
            resp = hutils.encode.do_base_64(resp)
        return add_headers(resp, c)
    
    @route('/all2.txt', methods=["GET", "HEAD"])
    @login_required(roles={Role.user})
    def all_configs2(self, base64=False):
        mode = "new"  # request.args.get("mode")
        base64 = base64 or request.args.get("base64", "").lower() == "true"
        c = get_common_data(g.account.uuid, mode)
        # response.content_type = 'text/plain';
        if request.method == 'HEAD':
            resp = ""
        else:
            # render_template('all_configs.txt', **c, base64=hutils.encode.do_base_64)
            resp = hutils.proxy.xray.make_v2ray_configs(c['domains'], c['user'], c['expire_days'], c['ip_debug'])

        if base64:
            resp = hutils.encode.do_base_64(resp)
        return add_headers(resp, c)
    
    @ route('/hidybot.txt', methods=["GET", "HEAD"])
    def hidybot_configs(self, base64=False):
        mode = "new"  # request.args.get("mode")
        base64 = base64 or request.args.get("base64", "").lower() == "true"
        bot_configs = None
        username = False
        randomize = False
        randomize_mode = "servers"
        try:
            with open("hidybotconfigs.json", 'r') as f:
                bot_configs = json.load(f)
        except Exception as e:
            logger.exception(f"Error in loading hidybotconfigs.json {e}")
        if bot_configs:
            username = bot_configs.get("username", False)
            randomize = bot_configs.get("randomize", False)
            randomize_mode = bot_configs.get("randomize_mode", "servers")
            # limit = limit or request.args.get("limit", "")
            # if limit:
            #     try:
            #         limit = int(limit)
            #     except Exception as e:
            #         limit = None
        c = get_common_data(g.account.uuid, mode)
        # response.content_type = 'text/plain';
        urls = None
        resp = None
        if request.method == 'HEAD':
            resp = ""
        else:
            # render_template('all_configs.txt', **c, base64=hutils.encode.do_base_64)
            resp = hutils.proxy.xray.make_v2ray_configs(c['domains'], c['user'], c['expire_days'], c['ip_debug'])
        if username:
            # شامل اینتر اخر نمیشود
            trojan_pattern = r'^trojan:\/\/.*\bsni=fake_ip_for_sub_link\b.*[^\n]'
            trojan_urls = re.findall(trojan_pattern, resp)
            if trojan_urls:
                fake_config = trojan_urls[0]
                encoded_name = f" 👤:{c['user'].name}"
                new_fake_config = fake_config + encoded_name
                resp = resp.replace(fake_config, new_fake_config)
        if randomize:
            if randomize_mode == "servers":
                fake_config = ""
                configs_list = []
                # configs = re.findall(r'(vless:\/\/[^\n]+)|(vmess:\/\/[^\n]+)|(trojan:\/\/[^\n]+)|tuic:\/\/[^\n]+)|(hysteria2:\/\/[^\n]+)|(hysteria:\/\/[^\n]+)', resp)
                #شامل اینتر اخر می شود
                trojan_pattern = r'^trojan:\/\/.*\bsni=fake_ip_for_sub_link\b.*\n'
                trojan_urls = re.findall(trojan_pattern, resp)
                if trojan_urls:
                    fake_config = trojan_urls[0] 
                    resp = resp.replace(fake_config, "")
                    fake_config += '\n'
                    configs_list.append(resp)
                # configs_list = resp.split("\n")
                try:
                    with open("nodes.json", 'r') as f:
                        urls = json.load(f)
                except Exception as e:
                    logger.exception(f"Error in loading nodes.json {e}")
                
                if urls:
                    for url in urls:
                        try:
                            url_sub = f"{url}/{g.account.uuid}/all2.txt"
                            req = requests.get(url_sub,timeout=10)
                            if req.status_code == 200:
                                nodes_configs = req.text
                                trojan_pattern = r'^trojan:\/\/.*\bsni=fake_ip_for_sub_link\b.*\n'
                                trojan_urls = re.findall(trojan_pattern, nodes_configs)
                                if trojan_urls:
                                    node_fake_config = trojan_urls[0]
                                    nodes_configs = nodes_configs.replace(node_fake_config, "")
                                # configs_list.append("\n")
                                configs_list.append(nodes_configs)
                                # configs_list += nodes_configs.split("\n")
                        except Exception as e:
                            logger.exception(f"Error in loading {url} configs {e}")
                if configs_list:
                    random.shuffle(configs_list)
                    resp = fake_config + '\n'.join(configs_list)
            elif randomize_mode == "configs":
                try:
                    with open("nodes.json", 'r') as f:
                        urls = json.load(f)
                except Exception as e:
                    logger.exception(f"Error in loading nodes.json {e}")
                
                if urls:
                    for url in urls:
                        resp += "\n"
                        try:
                            url_sub = f"{url}/{g.account.uuid}/all2.txt"
                            req = requests.get(url_sub,timeout=10)
                            if req.status_code == 200:
                                nodes_configs = req.text
                                trojan_pattern = r'^trojan:\/\/.*\bsni=fake_ip_for_sub_link\b.*\n'
                                trojan_urls = re.findall(trojan_pattern, nodes_configs)
                                if trojan_urls:
                                    node_fake_config = trojan_urls[0]
                                    nodes_configs = nodes_configs.replace(node_fake_config, "")
                                resp += nodes_configs
                        except Exception as e:
                            logger.exception(f"Error in loading {url} configs {e}")
                configs = [line for line in resp.split('\n') if line.strip() != '']
                if len(configs) > 2:
                    first_configs = configs[0:1]
                    rest_configs = configs[1:]
                    random.shuffle(rest_configs)
                    configs = first_configs + rest_configs
                resp = '\n'.join(configs)
        else:
            try:
                with open("nodes.json", 'r') as f:
                    urls = json.load(f)
            except Exception as e:
                logger.exception(f"Error in loading nodes.json {e}")
            
            if urls:
                for url in urls:
                    resp += "\n"
                    try:
                        url_sub = f"{url}/{g.account.uuid}/all2.txt"
                        req = requests.get(url_sub,timeout=10)
                        if req.status_code == 200:
                            nodes_configs = req.text
                            trojan_pattern = r'^trojan:\/\/.*\bsni=fake_ip_for_sub_link\b.*\n'
                            trojan_urls = re.findall(trojan_pattern, nodes_configs)
                            if trojan_urls:
                                node_fake_config = trojan_urls[0]
                                nodes_configs = nodes_configs.replace(node_fake_config, "")
                            resp += nodes_configs
                    except Exception as e:
                        logger.exception(f"Error in loading {url} configs {e}")
        if base64:
            resp = hutils.encode.do_base_64(resp)
        return add_headers(resp, c)
    
    @ route('/fragment/', methods=["GET", "HEAD"])
    def fragment_configs(self):
        bot_configs = None
        try:
            with open("hidybotconfigs.json", 'r') as f:
                bot_configs = json.load(f)
        except Exception as e:
           logger.exception(f"Error in loading hidybotconfigs.json {e}")
        if bot_configs:
            fragment_configs = bot_configs.get("fragment", None)
        if fragment_configs:
            c = get_common_data(g.account.uuid, "new")
            # response.content_type = 'text/plain';
            urls = None
            resp = None
            if request.method == 'HEAD':
                resp = ""
            else:
                resp = hutils.proxy.xray.make_v2ray_configs(**c)
                try:
                    with open("nodes.json", 'r') as f:
                        urls = json.load(f)
                except Exception as e:
                    logger.exception(f"Error in loading nodes.json {e}")
                if urls:
                    resp += "\n"
                    for url in urls:
                        try:
                            # BASE_URL = urlparse(url).scheme + "://" + urlparse(url).netloc
                            # PANEL_DIR = urlparse(url).path.split('/')
                            url_sub = f"{url}/{g.account.uuid}/all.txt"
                            req = requests.get(url_sub,timeout=10)
                            if req.status_code == 200:
                                resp += req.text + "\n"
                        except Exception as e:
                            logger.exception(f"Error in loading {url} configs {e}")

                configs = re.findall(r'(vless:\/\/[^\n]+)|(vmess:\/\/[^\n]+)|(trojan:\/\/[^\n]+)', resp)
                for config in configs:
                    if config[0]:
                        if fragment_configs in config[0]:
                            try:
                                url = urlparse(config[0])
                                search_params = parse_qs(url.query)
                                id = config[0].split('://')[1].split('@')[0]
                                address = config[0].split('@')[1].split(':')[0]
                                port = int(config[0].split('@')[1].split(':')[1].split('?')[0])

                                output = {
                                    "dns": {
                                        "hosts": {
                                            "domain:googleapis.cn": "googleapis.com"
                                        },
                                        "servers": ["1.1.1.1"]
                                    },
                                    "inbounds": [
                                        {
                                            "listen": "127.0.0.1",
                                            "port": 10808,
                                            "protocol": "socks",
                                            "settings": {
                                                "auth": "noauth",
                                                "udp": True,
                                                "userLevel": 8
                                            },
                                            "sniffing": {
                                                "destOverride": ["http", "tls"],
                                                "enabled": True
                                            },
                                            "tag": "socks"
                                        },
                                        {
                                            "listen": "127.0.0.1",
                                            "port": 10809,
                                            "protocol": "http",
                                            "settings": {
                                                "userLevel": 8
                                            },
                                            "tag": "http"
                                        }
                                    ],
                                    "log": {
                                        "loglevel": "warning"
                                    },
                                    "outbounds": [
                                        {
                                            "mux": {
                                                "concurrency": 8,
                                                "enabled": False
                                            },
                                            "protocol": "vless",
                                            "settings": {
                                                "vnext": [
                                                    {
                                                        "address": address,
                                                        "port": port,
                                                        "users": [
                                                            {
                                                                "encryption": search_params.get("encryption")[0],
                                                                "flow": "",
                                                                "id": id,
                                                                "level": 8,
                                                                "security": "auto"
                                                            }
                                                        ]
                                                    }
                                                ]
                                            },
                                            "streamSettings": {
                                                "network": search_params.get("type")[0],
                                                "security": search_params.get("security")[0],
                                                "tlsSettings": {
                                                    "allowInsecure": False,
                                                    "alpn": [search_params.get("alpn")[0]],
                                                    "fingerprint": search_params.get("fp")[0],
                                                    "publicKey": "",
                                                    "serverName": search_params.get("sni")[0],
                                                    "shortId": "",
                                                    "show": False,
                                                    "spiderX": ""
                                                },
                                                "wsSettings": {
                                                    "headers": {
                                                        "Host": search_params.get("host")[0]
                                                    },
                                                    "path": search_params.get("path")[0]
                                                }
                                            },
                                            "proxySettings": {
                                                "tag": "fragment",
                                                "transportLayer": True
                                            },
                                            "tag": "proxy"
                                        },
                                        {
                                            "protocol": "freedom",
                                            "settings": {},
                                            "tag": "direct"
                                        },
                                        {
                                            "protocol": "freedom",
                                            "tag": "fragment",
                                            "domainStrategy": "UseIP",
                                            "sniffing": {
                                                "enabled": True,
                                                "destOverride": ["http", "tls"]
                                            },
                                            "settings": {
                                                "fragment": {
                                                    "packets": "tlshello",
                                                    "length": "5-10",
                                                    "interval": "1-5"
                                                }
                                            },
                                            "streamSettings": {
                                                "sockopt": {
                                                    "tcpNoDelay": True,
                                                    "domainStrategy": "UseIP"
                                                }
                                            }
                                        },
                                        {
                                            "protocol": "blackhole",
                                            "settings": {
                                                "response": {
                                                    "type": "http"
                                                }
                                            },
                                            "tag": "block"
                                        }
                                    ],
                                    "routing": {
                                        "domainStrategy": "IPIfNonMatch",
                                        "rules": [
                                            {
                                                "ip": ["1.1.1.1"],
                                                "outboundTag": "proxy",
                                                "port": "53",
                                                "type": "field"
                                            }
                                        ]
                                    }
                                }
                                resp = json.dumps(output)
                                return add_headers(resp, c)
                            except Exception as e:
                                return jsonify({'status': 502, 'msg': 'error:\n{e}'})
    @ route("/offline.html")
    @login_required(roles={Role.user})
    def offline():
        return f"Not Connected <a href='{hiddify.get_account_panel_link(g.account, request.host)}'>click for reload</a>"

    # backward compatiblity
    @route("/admin/<path:path>")
    @login_required()
    def admin(self, path):
        return ""


# def do_base_64(str):
#     import base64
#     resp = base64.b64encode(f'{str}'.encode("utf-8"))
#     return resp.decode()


# @cache.cache(ttl=300)
def get_domain_information(no_domain=False, filter_domain=None, alternative=None):
    domains = []
    default_asn = request.args.get("asn", '')
    if filter_domain:
        domain = filter_domain
        db_domain = Domain.query.filter(Domain.domain == domain).first() or Domain(
            domain=domain, mode=DomainType.direct, cdn_ip='', show_domains=[], child_id=0)
        domains = [db_domain]
    else:
        domain = alternative if not no_domain else None
        db_domain = Domain.query.filter(Domain.domain == domain).first()

        if not db_domain:
            parts = domain.split('.')  # TODO fix bug domain maybe null
            parts[0] = "*"
            domain_new = ".".join(parts)
            db_domain = Domain.query.filter(Domain.domain == domain_new).first()

        if not db_domain:
            db_domain = Domain(domain=domain, show_domains=[])
            hutils.flask.flash(_("This domain does not exist in the panel!" + domain))

        domains = db_domain.show_domains or Domain.query.filter(Domain.sub_link_only != True).all()

    has_auto_cdn = False
    for d in domains:
        db.session.expunge(d)
        d.has_auto_ip = False
        if d.mode == DomainType.auto_cdn_ip or d.cdn_ip:
            has_auto_cdn = True
            d.has_auto_ip = d.mode == DomainType.auto_cdn_ip or (
                d.cdn_ip and "MTN" in d.cdn_ip)
            d.cdn_ip = hutils.network.auto_ip_selector.get_clean_ip(
                d.cdn_ip, d.mode == DomainType.auto_cdn_ip, default_asn)
            # print("autocdn ip mode ", d.cdn_ip)
        if "*" in d.domain:
            d.domain = d.domain.replace("*", hutils.random.get_random_string(5, 15))

    if len(domains) == 0:
        domains = [Domain(id=0, domain=alternative, mode=DomainType.direct, cdn_ip='', show_domains=[], child_id=0)]
        domains[0].has_auto_ip = True

    return domains, db_domain, has_auto_cdn


def get_common_data(user_uuid, mode, no_domain=False, filter_domain=None):
    '''Usable for user account'''
    # uuid_secret=str(uuid.UUID(user_secret))
    domains, db_domain, has_auto_cdn = get_domain_information(no_domain, filter_domain, request.host)

    domain = db_domain.domain
    user: User = g.account if g.account.uuid == user_uuid else User.by_uuid(f'{user_uuid}')
    if user is None:
        abort(401, "Invalid User")

    package_mode_dic = {
        UserMode.daily: 1,
        UserMode.weekly: 7,
        UserMode.monthly: 30

    }

    expire_days = user.remaining_days
    reset_days = user.days_to_reset()
    if reset_days >= expire_days:
        reset_days = 1000

    expire_s = int((datetime.date.today() + datetime.timedelta(days=expire_days) - datetime.date(1970, 1, 1)).total_seconds())

    user_ip = hutils.network.auto_ip_selector.get_real_user_ip()
    asn = hutils.network.auto_ip_selector.get_asn_short_name(user_ip)
    profile_title = f'{db_domain.alias or db_domain.domain} {user.name}'
    profile_url = hiddify.get_account_panel_link(user, request.host)
    if has_auto_cdn and asn != 'unknown':
        profile_title += f" {asn}"

    return {
        # 'direct_host':direct_host,
        'profile_title': profile_title,
        'user': user,
        'user_activate': user.is_active,
        'domain': domain,
        'mode': mode,
        'fake_ip_for_sub_link': datetime.datetime.now().strftime(f"%H.%M--%Y.%m.%d.time:%H%M"),
        'usage_limit_b': int(user.usage_limit_GB * 1024 * 1024 * 1024),
        'usage_current_b': int(user.current_usage_GB * 1024 * 1024 * 1024),
        'expire_s': expire_s,
        'expire_days': expire_days,
        'expire_rel': hutils.convert.format_timedelta(datetime.timedelta(days=expire_days)),
        'reset_day': reset_days,
        'hconfigs': get_hconfigs(),
        'hdomains': Domain.modes_and_domains(),
        'ConfigEnum': ConfigEnum,
        'link_maker': hutils.proxy,
        'domains': domains,
        "bot": g.get('bot', None),
        "db_domain": db_domain,
        "telegram_enable": hiddify.is_telegram_proxy_enable(domains),
        "ip": user_ip,
        "ip_debug": hutils.network.auto_ip_selector.get_real_user_ip_debug(user_ip),
        "asn": asn,
        "country": hutils.network.auto_ip_selector.get_country(user_ip),
        'has_auto_cdn': has_auto_cdn,
        'profile_url': profile_url
    }


def add_headers(res, c, mimetype="text/plain"):
    resp = Response(res)
    resp.mimetype = mimetype
    resp.headers['Subscription-Userinfo'] = f"upload=0;download={c['usage_current_b']};total={c['usage_limit_b']};expire={c['expire_s']}"
    resp.headers['profile-web-page-url'] = request.base_url.rsplit('/', 1)[0].replace("http://", "https://") + "/"
    # resp.headers['test-url'] = f"http://127.0.0.1:90/{hconfig(ConfigEnum.proxy_path_client)}/generate_204"
    # resp.headers['test-url'] = f"http://{request.host}/{hconfig(ConfigEnum.proxy_path_client)}/generate_204"
    # resp.headers['test-url'] = "http://connectivitycheck.gstatic.com/generate_204"

    if hconfig(ConfigEnum.branding_site):
        resp.headers['support-url'] = hconfig(ConfigEnum.branding_site)
    resp.headers['profile-update-interval'] = 1
    # resp.headers['content-disposition']=f'attachment; filename="{c["db_domain"].alias or c["db_domain"].domain} {c["user"].name}"'

    resp.headers['profile-title'] = 'base64:' + hutils.encode.do_base_64(c['profile_title'])

    return resp
