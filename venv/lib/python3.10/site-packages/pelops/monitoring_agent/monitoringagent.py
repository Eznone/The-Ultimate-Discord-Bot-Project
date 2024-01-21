import datetime
import hashlib
import json
import os
import socket
import time
import uuid
from threading import Event

import pelops.myconfigtools
import pelops.logging.mylogger
import psutil

import pelops.monitoring_agent.states.state_machine
from pelops.monitoring_agent.states.event_ids import event_ids
from pelops.monitoring_agent.states.state_ids import state_ids
from pelops.logging.mqtthandler import MQTTHandler
from pelops.logging.mqtthandler import MQTTFilter
from pelops.myconfigtools import mask_entries


_RESTART_TERMINATED = 30  # time to be waited in state terminated until next onboarding attemt is started. (seconds)


class MonitoringAgent:
    _config = None
    _mqtt_client = None
    _service = None

    _logger = None
    _hander_logger = None
    _handler_filter = None
    _mqtt_logger_handler = None

    _protcol_version = 1

    _uuid = None

    _process_children_warning = None

    _onboarding_topic_prefix = None
    _topic_send_onboarding_request = None
    _location = None
    _room = None
    _device = None
    _description = None
    _name = None
    _gid = None
    _session = None
    timings = None

    _TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"  # time format string for influxdb queries

    _topic_send_ping = None
    _topic_send_runtime = None
    _topic_send_config = None
    _topic_send_end = None
    _topic_send_logger = None

    _topic_recv_cmd_end_on_request = None
    _topic_recv_cmd_reonboarding = None
    _topic_recv_cmd_ping_on_request = None
    _topic_recv_cmd_config_on_request = None
    _topic_recv_cmd_runtime_on_request = None
    _topic_recv_heartbeat = None

    _topic_recv_onboarding_response = None

    _state_machine = None
    state_history = None
    _sigint = None

    _start_process_time = None
    _start_time = None

    def __init__(self, config, service, mqtt_client, logger):
        """
        service must fulfill the following API:
          * _config - json structure with the config of the service
          * _version - string representing the version of the implementation
          * runtime_information - dict containing arbitrary runtime information to be sent to monitoring service
          * config_information - dict containing arbitrary config information to be sent to monitoring service

        :param config: json structure with the required config
        :param service: pointer to the service that should be monitored
        :param mqtt_client: instance of paho.mqtt client
        :param logger: logger instance to be used by the monitorings agent
        :param logfilter: if not none add this filte to the mqttlogginghandler
        :param loggerroot: if not none attach handler to this logger (otherwise attach it to logger)
        """
        self._start_time = time.time()
        self._start_process_time = time.process_time()

        self._config = config
        self._mqtt_client = mqtt_client

        self._logger = pelops.logging.mylogger.get_child(logger, self.__class__.__name__)
        self._logger.info("__init__ - start")

        self._hander_logger = logger
        self._handler_filter = MQTTFilter(mqtt_logger_name=self._mqtt_client._logger.name,
                                          min_log_level="WARNING")

        self._process_children_warning = False

        self._service = service

        self._onboarding_topic_prefix = self._config["response-prefix"]
        self._topic_send_onboarding_request = self._config["onboarding-topic"]
        self._location = self._config["location"]
        self._room = self._config["room"]
        self._device = self._config["device"]
        try:
            self._gid = self._config["gid"]
        except KeyError:
            self._gid = None
        self._name = self._config["name"]
        self._description = self._config["description"]
        self.timings = {
            "restart-onboarding": self._config["restart-onboarding"],
            "restart-terminated": _RESTART_TERMINATED,
            "send-ping": 0,
            "send-runtime": 0,
            "send-config": 0,
            "expect-heartbeat": 0,
        }
        self._init_state_machine()
        self._logger.info("__init__ - finish")

    def _init_state_machine(self):
        self._sigint = Event()
        self._state_machine, self._states, self.state_history = pelops.monitoring_agent.states.state_machine\
            .create(self._sigint, self.timings["restart-onboarding"], self.timings["restart-terminated"],
                    self._logger)

        self._states[state_ids.UNINITIALIZED].update_uuid = self.update_uuid
        self._states[state_ids.UNINITIALIZED].decativate_last_will = self.deactivate_last_will
        self._states[state_ids.UNINITIALIZED].deactivate_onboarding_response = self.deactivate_onboarding_response

        self._states[state_ids.INITIALIZED].activate_onboarding_response = self.activate_onboarding_response

        self._states[state_ids.ONBOARDING].send_onboarding_request = self.send_onboarding_request

        self._states[state_ids.ONBOARDED].send_config = self.send_config
        self._states[state_ids.ONBOARDED].deactivate_onboarding_response = self.deactivate_onboarding_response
        self._states[state_ids.ONBOARDED].activate_last_will = self.activate_last_will

        self._states[state_ids.ACTIVE].send_config = self.send_config
        self._states[state_ids.ACTIVE].send_ping = self.send_ping
        self._states[state_ids.ACTIVE].send_runtime = self.send_runtime

        self._states[state_ids.ACTIVE].activate_config_on_request = self.activate_config_on_request
        self._states[state_ids.ACTIVE].deactivate_config_on_request = self.deactivate_config_on_request
        self._states[state_ids.ACTIVE].activate_end_on_request = self.activate_end_on_request
        self._states[state_ids.ACTIVE].deactivate_end_on_request = self.deactivate_end_on_request
        self._states[state_ids.ACTIVE].activate_ping_on_request = self.activate_ping_on_request
        self._states[state_ids.ACTIVE].deactivate_ping_on_request = self.deactivate_ping_on_request
        self._states[state_ids.ACTIVE].activate_runtime_on_request = self.activate_runtime_on_request
        self._states[state_ids.ACTIVE].deactivate_runtime_on_request = self.deactivate_runtime_on_request
        self._states[state_ids.ACTIVE].activate_reonboarding_request = self.activate_reonboarding_request
        self._states[state_ids.ACTIVE].deactivate_reonboarding_request = self.deactivate_reonboarding_request
        self._states[state_ids.ACTIVE].activate_forward_logger = self.activate_forward_logger
        self._states[state_ids.ACTIVE].deactivate_forward_logger = self.deactivate_forward_logger
        self._states[state_ids.ACTIVE].activate_receive_heartbeat = self.activate_receive_heartbeat
        self._states[state_ids.ACTIVE].deactivate_receive_heartbeat = self.deactivate_receive_heartbeat

        self._states[state_ids.TERMINATING].send_offboarding_message = self.send_end_message

        self._update_timings()

    def _update_timings(self):
        self._logger.info("_update_timings {}".format(self.timings))
        self._states[state_ids.ACTIVE].send_config_interval = self.timings["send-config"]
        self._states[state_ids.ACTIVE].send_ping_interval = self.timings["send-ping"]
        self._states[state_ids.ACTIVE].send_runtime_interval = self.timings["send-runtime"]
        self._state_machine.updatetimeoutevent(state_ids.ACTIVE, event_ids.TIMEOUT, self.timings["expect-heartbeat"])

    def start(self):
        self._state_machine.start()

    def stop(self):
        self._sigint.set()
        self._logger.debug("stop - operate(SIGINT)")
        self._state_machine.operate(event_ids.SIGINT)
        self._state_machine.stop()

    def get_gid(self):
        return self._gid

    def get_session(self):
        return self._session

    def current_state(self):
        return self._state_machine.get_active_state()

    def restart(self):
        self._logger.debug("restart - asyncoperate(SIGINT)")
        self._state_machine.asyncoperate(event_ids.SIGINT)

    def activate_forward_logger(self):
        if self._config["publish-log-level"].upper() == "DISABLED":
            self._logger.info("activate_forward_logger - forwarding mechanism is disabled")
        else:
            self._mqtt_logger_handler = MQTTHandler(self._topic_send_logger, self._config["publish-log-level"], self._gid,
                                                    self._mqtt_client, self._hander_logger, self._handler_filter)
            self._mqtt_logger_handler.start()

    def deactivate_forward_logger(self):
        if self._mqtt_logger_handler is not None:
            self._mqtt_logger_handler.stop()

    def activate_receive_heartbeat(self):
        self._logger.debug("activate_receive_heartbeat: {}".format(self._topic_recv_heartbeat))
        self._mqtt_client.subscribe(self._topic_recv_heartbeat, self.handler_receive_heartbeat,
                                    ignore_duplicate=True)

    def deactivate_receive_heartbeat(self):
        self._logger.debug("deactivate_receive_heartbeat: {}".format(self._topic_recv_heartbeat))
        self._mqtt_client.unsubscribe(self._topic_recv_heartbeat, self.handler_receive_heartbeat,
                                      ignore_not_found=True)

    def handler_receive_heartbeat(self, message):
        """
        {
            "heartbeat": "heartbeat",
            "timestamp": "1985-04-12T23:20:50.520Z"
        }
        """
        message = json.loads(message.decode("utf8"))
        self._logger.info("received heartbeat message")
        self._logger.debug("handler_receive_heartbeat - {}".format(message))
        if message["heartbeat"] != "heartbeat":
            self._logger.error("received heartbeat message with wrong content: '{}'".format(message))
        self._state_machine.restarttimeoutevent()

    def activate_reonboarding_request(self):
        self._logger.debug("activate_reonboarding_request: {}".format(self._topic_recv_cmd_reonboarding))
        self._mqtt_client.subscribe(self._topic_recv_cmd_reonboarding, self.handler_reonboarding_request,
                                    ignore_duplicate=True)

    def deactivate_reonboarding_request(self):
        self._logger.debug("deactivate_reonboarding_request: {}".format(self._topic_recv_cmd_reonboarding))
        self._mqtt_client.unsubscribe(self._topic_recv_cmd_reonboarding, self.handler_reonboarding_request,
                                      ignore_not_found=True)

    def handler_reonboarding_request(self, message):
        """
        {
            "request": "reonboarding",
            "gid": 1
        }
        """
        message = json.loads(message.decode("utf8"))
        if message["request"] != "reonboarding":
            self._logger.error("monitoringagent.handler_reonboarding_request - field request should contain 'onboarding' "
                               "but contained '{}' instead", format(message["request"]))
        elif "gid" in message and message["gid"] != self._gid:
            self._logger.debug("received reonboarding request with different gid (incoming '{}', self '{})".
                               format(message["gid"], self._gid))
        else:
            self._logger.warning("received reonboarding request")
            self._logger.debug("handler_reonboarding_request - {}".format(message))
            self._state_machine.asyncoperate(event_ids.REONBOARDING_REQUEST)

    def activate_onboarding_response(self):
        self._logger.debug("activate_onboarding_response: {}".format(self._topic_recv_onboarding_response))
        try:
            self._mqtt_client.subscribe(self._topic_recv_onboarding_response, self.handler_onboarding_response,
                                    ignore_duplicate=False)
        except ValueError as e:
            self._logger.debug("activate_onboarding_response: already added handler for {}"
                               .format(self._topic_recv_onboarding_response))

    def deactivate_onboarding_response(self):
        self._logger.debug("deactivate_onboarding_response: {}".format(self._topic_recv_onboarding_response))
        self._mqtt_client.unsubscribe(self._topic_recv_onboarding_response, self.handler_onboarding_response,
                                      ignore_not_found=True)

    def handler_onboarding_response(self, message):
        """
        {
          "uuid": "550e8400-e29b-11d4-a716-446655440000",
          "gid": 1,
          "session": 1,
          "topics-activity": {
            "ping": "/hippodamia/commands",
            "runtime": "/hippodamia/commands",
            "config": "/hippodamia/commands",
            "end": "/hippodamia/commands",
            "logger": "/hippodamia/commands"
          },
          "topics-commands": {
            "end": "/hippodamia/commands",
            "reonboarding": "/hippodamia/commands",
            "ping_on_request": "/hippodamia/commands",
            "config_on_request": "/hippodamia/commands",
            "runtime_on_request": "/hippodamia/commands",
            "heartbeat": "/hippodamia/commands"
          },
          "timings": {
            "send-ping": 60,
            "send-runtime": 500,
            "send-config": 3600,
            "expect-heartbeat": 120
          }
        }
        """
        message = json.loads(message.decode("utf8"))
        if str(message["uuid"]) != str(self._uuid):
            self._logger.error("received onboarding response with wrong uuid - expected '{}', received '{}'"
                               .format(self._uuid, message["uuid"]))
        else:
            self._logger.warning("received onboarding response with gid '{}'".format(message["gid"]))
            self._logger.debug("onboarding response: {}".format(message))

            self._gid = message["gid"]
            self._session = message["session"]

            self._topic_send_ping = message["topics-activity"]["ping"]
            self._logger.info("_topic_send_ping='{}'".format(self._topic_send_ping))
            self._topic_send_runtime = message["topics-activity"]["runtime"]
            self._logger.info("_topic_send_runtime='{}'".format(self._topic_send_runtime))
            self._topic_send_config = message["topics-activity"]["config"]
            self._logger.info("_topic_send_config='{}'".format(self._topic_send_config))
            self._topic_send_end = message["topics-activity"]["end"]
            self._logger.info("_topic_send_end='{}'".format(self._topic_send_end))
            self._topic_send_logger = message["topics-activity"]["logger"]
            self._logger.info("_topic_send_logger='{}'".format(self._topic_send_logger))

            self._topic_recv_cmd_end_on_request = message["topics-commands"]["end"]
            self._logger.info("_topic_recv_cmd_sigint='{}'".format(self._topic_recv_cmd_end_on_request))
            self._topic_recv_cmd_reonboarding = message["topics-commands"]["reonboarding"]
            self._logger.info("_topic_recv_cmd_reonboarding='{}'".format(self._topic_recv_cmd_reonboarding))
            self._topic_recv_cmd_ping_on_request = message["topics-commands"]["ping_on_request"]
            self._logger.info("_topic_recv_cmd_ping_on_request='{}'".format(self._topic_recv_cmd_ping_on_request))
            self._topic_recv_cmd_config_on_request = message["topics-commands"]["config_on_request"]
            self._logger.info("_topic_recv_cmd_config_on_request='{}'".format(self._topic_recv_cmd_config_on_request))
            self._topic_recv_cmd_runtime_on_request = message["topics-commands"]["runtime_on_request"]
            self._logger.info("_topic_recv_cmd_runtime_on_request='{}'".format(self._topic_recv_cmd_runtime_on_request))
            self._topic_recv_heartbeat = message["topics-commands"]["heartbeat"]
            self._logger.info("_topic_recv_heartbeat='{}'".format(self._topic_recv_heartbeat))

            self.timings["send-ping"] = message["timings"]["send-ping"]
            self._logger.info("timing send-ping='{}'".format(self.timings["send-ping"]))
            self.timings["send-runtime"] = message["timings"]["send-runtime"]
            self._logger.info("timing send-runtime='{}'".format(self.timings["send-runtime"]))
            self.timings["send-config"] = message["timings"]["send-config"]
            self._logger.info("timing send-config='{}'".format(self.timings["send-config"]))
            self.timings["expect-heartbeat"] = message["timings"]["expect-heartbeat"]
            self._logger.info("timing expect-heartbeat='{}'".format(self.timings["expect-heartbeat"]))

            self._update_timings()

            self._logger.debug("handler_onboarding_reponse - asnycoperate(ONBOARDING_RESPONSE)")
            self._state_machine.asyncoperate(event_ids.ONBOARDING_RESPONSE)

    def activate_ping_on_request(self):
        self._logger.debug("activate_ping_on_request: {}".format(self._topic_recv_cmd_ping_on_request))
        self._mqtt_client.subscribe(self._topic_recv_cmd_ping_on_request, self.handler_ping_on_request,
                                    ignore_duplicate=True)

    def deactivate_ping_on_request(self):
        self._logger.debug("deactivate_ping_on_request: {}".format(self._topic_recv_cmd_ping_on_request))
        self._mqtt_client.unsubscribe(self._topic_recv_cmd_ping_on_request, self.handler_ping_on_request,
                                      ignore_not_found=True)

    def handler_ping_on_request(self, message):
        """
        {
            "request": "ping",
            "gid": 1
        }
        """
        message = json.loads(message.decode("utf8"))
        if message["request"] != "ping":
            self._logger.error("handler_ping_on_request - field request should contain 'ping' "
                               "but contained '{}' instead", format(message["request"]))
        elif "gid" in message and message["gid"] != self._gid:
            self._logger.debug("received ping_on_request with different gid (incoming '{}', self '{})".
                               format(message["gid"], self._gid))
        else:
            self._logger.info("handler_ping_on_request")
            self._logger.debug("handler_ping_on_request - {}".format(message))
            self.send_ping()

    def activate_runtime_on_request(self):
        self._logger.debug("activate_runtime_on_request: {}".format(self._topic_recv_cmd_runtime_on_request))
        self._mqtt_client.subscribe(self._topic_recv_cmd_runtime_on_request, self.handler_runtime_on_request,
                                    ignore_duplicate=True)

    def deactivate_runtime_on_request(self):
        self._logger.debug("deactivate_runtime_on_request: {}".format(self._topic_recv_cmd_runtime_on_request))
        self._mqtt_client.unsubscribe(self._topic_recv_cmd_runtime_on_request, self.handler_runtime_on_request,
                                      ignore_not_found=True)

    def handler_runtime_on_request(self, message):
        """
        {
            "request": "runtime",
            "gid": 1
        }
        """
        message = json.loads(message.decode("utf8"))
        if message["request"] != "runtime":
            self._logger.error("handler_runtime_on_request - field request should contain 'runtime' "
                               "but contained '{}' instead", format(message["request"]))
        elif "gid" in message and message["gid"] != self._gid:
            self._logger.debug("received runtime_on_request with different gid (incoming '{}', self '{})".
                               format(message["gid"], self._gid))
        else:
            self._logger.info("handler_runtime_on_request")
            self._logger.debug("handler_runtime_on_request - {}".format(message))
            self.send_runtime()

    def activate_config_on_request(self):
        self._logger.debug("activate_config_on_request: {}".format(self._topic_recv_cmd_config_on_request))
        self._mqtt_client.subscribe(self._topic_recv_cmd_config_on_request, self.handler_config_on_request,
                                    ignore_duplicate=True)

    def deactivate_config_on_request(self):
        self._logger.debug("deactivate_config_on_request: {}".format(self._topic_recv_cmd_config_on_request))
        self._mqtt_client.unsubscribe(self._topic_recv_cmd_config_on_request, self.handler_config_on_request,
                                      ignore_not_found=True)

    def handler_config_on_request(self, message):
        """
        {
            "request": "config",
            "gid": 1
        }
        """
        message = json.loads(message.decode("utf8"))
        if message["request"] != "config":
            self._logger.error("handler_config_on_request - field request should contain 'config' "
                               "but contained '{}' instead", format(message["request"]))
        elif "gid" in message and message["gid"] != self._gid:
            self._logger.debug("received config_on_request with different gid (incoming '{}', self '{})".
                               format(message["gid"], self._gid))
        else:
            self._logger.info("handler_config_on_request")
            self._logger.debug("handler_config_on_request - {}".format(message))
            self.send_config()

    def send_onboarding_request(self):
        self._logger.warning("send onboarding request with uuid '{}'".format(self._uuid))
        message = self.generate_on_boarding_request_message(self._uuid)
        self._logger.debug("topic: {}, message: {}".format(self._topic_send_onboarding_request, message))
        self._mqtt_client.publish(self._topic_send_onboarding_request, message)

    def send_ping(self):
        self._logger.info("send ping")
        message = self.generate_ping_message()
        self._logger.debug("topic: {}, message: {}".format(self._topic_send_ping, message))
        self._mqtt_client.publish(self._topic_send_ping, message)

    def send_runtime(self):
        self._logger.info("send runtime")
        message = self.generate_runtime_message()
        self._logger.debug("topic: {}, message: {}".format(self._topic_send_runtime, message))
        self._mqtt_client.publish(self._topic_send_runtime, message)

    def send_config(self):
        self._logger.info("send config")
        message = self.generate_config_message()
        self._logger.debug("topic: {}, message: {}".format(self._topic_send_config, message))
        self._mqtt_client.publish(self._topic_send_config, message)

    def send_end_message(self):
        self._logger.warning("send end message")
        message = self.generate_end_message()
        self._logger.debug("topic: {}, message: {}".format(self._topic_send_end, message))
        if self._topic_send_end is None:
            self._logger.info("send_end_message - _topic_send_end not set. skipping send.")
        else:
            self._mqtt_client.publish(self._topic_send_end, message)

    def activate_end_on_request(self):
        self._logger.debug("activate_end_on_request: {}".format(self._topic_recv_cmd_end_on_request))
        self._mqtt_client.subscribe(self._topic_recv_cmd_end_on_request, self.handler_end_on_request,
                                    ignore_duplicate=True)

    def deactivate_end_on_request(self):
        self._logger.debug("deactivate_end_on_request: {}".format(self._topic_recv_cmd_end_on_request))
        self._mqtt_client.unsubscribe(self._topic_recv_cmd_end_on_request, self.handler_end_on_request,
                                      ignore_not_found=True)

    def handler_end_on_request(self, message):
        """
        {
            "request": "end",
            "gid": 1
        }
        """
        message = json.loads(message.decode("utf8"))
        if message["request"] != "end":
            self._logger.error("handler_end_on_request - field request should contain 'ping' "
                               "but contained '{}' instead", format(message["request"]))
        elif "gid" in message and message["gid"] != self._gid:
            self._logger.debug("received end_on_request with different gid (incoming '{}', self '{})".
                               format(message["gid"], self._gid))
        else:
            self._logger.info("handler_end_on_request")
            self._logger.debug("handler_end_on_request - {}".format(message))
            self._logger.debug("handler_end_on_request - asyncoperate(SIGINT)")
            self._state_machine.asyncoperate(event_ids.SIGINT)
            
    def activate_last_will(self):
        if self._topic_send_end is None:
            self._logger.debug("activate_last_will - last will not set, topic is None")
        else:
            self._logger.debug("activate_last_will: {}: {}".format(self._topic_send_end,
                                                                   self.generate_end_message(last_will=True)))
            self._mqtt_client.set_will(self._topic_send_end, self.generate_end_message(last_will=True))

    def deactivate_last_will(self):
        if self._topic_send_end is None:
            self._logger.debug("deactivate_last_will - last will not reset, topic is None")
        else:
            self._logger.debug("deactivate_last_will - {}".format(self._topic_send_end))
            self._mqtt_client.set_will(self._topic_send_end, "")

    def update_uuid(self):
        self._uuid = uuid.uuid4()
        self._topic_recv_onboarding_response = self._onboarding_topic_prefix + str(self._uuid)
        self._logger.debug("update_uuid - new uuid: '{}'.".format(self._uuid))
        self._logger.info("update_uuid - resulting onboarding response topic: '{}'"
                          .format(self._topic_recv_onboarding_response))

    @staticmethod
    def _get_local_ip(remote_ip, remote_port):
        rips = [remote_ip]
        if remote_ip == "127.0.0.1":
            rips.append("::1")  # add ipv6 localhost name
        connections = psutil.net_connections()
        remote_port_connections = []
        for pconn in connections:
            try:
                if pconn.raddr[1] == remote_port:
                    remote_port_connections.append(pconn)
            except IndexError:
                pass
        laddr = None
        if len(remote_port_connections) == 0:
            raise KeyError("No outgoing connection found for port {}.".format(remote_port))
        elif len(remote_port_connections) == 1:
            laddr = remote_port_connections[0].laddr[0]
        else:
            for pconn in remote_port_connections:
                if pconn.raddr[0] in rips:
                    laddr = pconn.laddr[0]
                    break
        if laddr is None:
            raise KeyError("No matching ip address found for ip '{}': {}".format(remote_ip, remote_port_connections))
        return laddr

    @staticmethod
    def _get_local_ips(skip_lo=True):
        laddrs = set()
        nics = psutil.net_if_addrs()
        if skip_lo:
            try:
                nics.pop("lo")
            except KeyError:
                pass
        for nic_id, nic_entries in nics.items():
            for snicaddr in nic_entries:
                if snicaddr.family == socket.AF_INET or snicaddr.family == socket.AF_INET6:
                    laddrs.add(snicaddr.address)
        return sorted(list(laddrs))

    @staticmethod
    def _get_mac_addresses(skip_lo=True):
        mac_adresses = []
        nics = psutil.net_if_addrs()
        if skip_lo:
            try:
                nics.pop("lo")
            except KeyError:
                pass
        for nic_id, nic_entries in nics.items():
            for snicaddr in nic_entries:
                if snicaddr.family == psutil.AF_LINK:
                    mac_adresses.append(snicaddr.address)
        return mac_adresses

    @staticmethod
    def _get_mac_from_uuid():
        return '-'.join('%02X' % ((uuid.getnode() >> 8*i) & 0xff) for i in reversed(range(6)))

    def _get_mac_address(self, interface):
        mac_adresses = []
        nics = psutil.net_if_addrs()
        for snicaddr in nics[interface]:
            if snicaddr.family == psutil.AF_LINK:
                mac_adresses.append(snicaddr.address)
        mac = None
        if len(mac_adresses) == 0:
            self._logger.info("_get_mac_address - No mac address found for interface '{}'.".format(interface))
            mac = MonitoringAgent._get_mac_from_uuid()  # use getnode from uuid instead
        elif len(mac_adresses) > 1:
            # unclear if this can actually happen. theoretically, the result from net_if_addrs would support such a case
            self._logger.info("_get_mac_address - More than one mac address ({}) found for interface '{}'.".format(mac_adresses, interface))
            mac = MonitoringAgent._get_mac_from_uuid()  # use getnode from uuid instead
        else:
            mac = mac_adresses[0]
        return mac

    @staticmethod
    def _get_interface_from_ip(ip):
        interfaces = []
        nics = psutil.net_if_addrs()
        for nic_id, nic_entry in nics.items():
            for snicaddr in nic_entry:
                if (snicaddr.family == socket.AF_INET or snicaddr.family == socket.AF_INET6) and snicaddr.address == ip:
                    interfaces.append(nic_id)
        if len(interfaces) == 0:
            raise KeyError("No interface found for ip '{}'".format(ip))
        elif len(interfaces) > 1:
            raise KeyError("More than one interface ({}) found for ip '{}'".format(interfaces, ip))
        return interfaces[0]

    def generate_on_boarding_request_message(self, temp_uuid):
        """
        {
          "uuid": "550e8400-e29b-11d4-a716-446655440000",
          "onboarding-topic": "/hippodamia/550e8400-e29b-11d4-a716-446655440000",
          "protocol-version": 1,
          "timestamp": "1985-04-12T23:20:50.520Z",
          "identifier": {
            "last-gid": "copreus-1",
            "last-session": 2,
            "type": "copreus",
            "version": "0.3.1",
            "name": "display-driver",
            "location": "flat",
            "room": "living room",
            "device": "thermostat",
            "decription": "lorem ipsum",
            "host-name": "rpi",
            "node-id": "00-07-E9-AB-CD-EF",
            "ips": [
              "192.168.0.1",
              "10.0.1.2",
              "2001:0db8:85a3:08d3:1319:8a2e:0370:7344"
            ],
            "config-hash": "cf23df2207d99a74fbe169e3eba035e633b65d94"
          }
        }
        """
        hashinstance = hashlib.sha256()
        hashinstance.update(json.dumps(self._service._config).encode())
        config_hash = hashinstance.hexdigest()

        target_ip = socket.gethostbyname(self._mqtt_client._config["mqtt-address"])
        target_port = self._mqtt_client._config["mqtt-port"]


        try:
            local_ip = MonitoringAgent._get_local_ip(target_ip, target_port)
        except KeyError:
            local_ip = ""
            self._logger.warning("get local ip failed (target ip: {}, target port: {})".format(target_ip, target_port))
        except OSError as e:
            local_ip = ""
            self._logger.error(e)

        try:
            interface = MonitoringAgent._get_interface_from_ip(local_ip)
        except KeyError:
            interface = ""
            self._logger.warning("get interface from ip failed (local ip: {})".format(local_ip))
        except OSError as e:
            interface = ""
            self._logger.error(e)

        try:
            mac_address = self._get_mac_address(interface)
        except KeyError:
            mac_address = ""
            self._logger.warning("get mac address failed (interface: {})".format(interface))
        except OSError:
            mac_address = ""
            self._logger.error(e)

        local_ips = MonitoringAgent._get_local_ips(skip_lo=False)
        mac_addresses = MonitoringAgent._get_mac_addresses(skip_lo=True)

        message = {
            "uuid": str(temp_uuid),
            "onboarding-topic": self._onboarding_topic_prefix + str(temp_uuid),
            "protocol-version": self._protcol_version,
            "timestamp": datetime.datetime.now().strftime(self._TIME_FORMAT),
            "identifier": {
                "last-gid": self._gid,
                "last-session": self._session,
                "type": type(self._service).__qualname__,
                "module": self._service.__module__,
                "version": self._service._version,
                "name": self._name,
                "location": self._location,
                "room": self._room,
                "device": self._device,
                "description": self._description,
                "host-name": socket.gethostname(),
                "node-id": mac_address,
                "mqtt-client-local-ip": local_ip,
                "ips": local_ips,
                "mac-addresses": mac_addresses,
                "config-hash": config_hash
            }
        }

        return json.dumps(message)

    def generate_ping_message(self):
        """
        {
          "gid": 1,
          "session": 2,
          "timestamp": "1985-04-12T23:20:50.520Z",
          "service-uptime": 12345.67
        }
        :return:
        """
        return json.dumps({
            "gid": self._gid,
            "session": self._session,
            "timestamp": datetime.datetime.now().strftime(self._TIME_FORMAT),
            "service-uptime": time.time() - self._start_time
        })

    def generate_runtime_message(self):
        """
        {
          "gid": 1,
          "session": 2,
          "timestamp": "1985-04-12T23:20:50.520Z",
          "service-uptime": 12345.67,
          "process-time": 12345.67,
          "system-uptime": 12345.67,
          "cpu_percent": 0,
          "free-memory": 0,
          "service-memory": 0,
          "disk-usage": 0,
          "messages-received-total": 0,
          "messages-sent-total": 0,
          "topics": [
            {
              "messages-received": 0,
              "messages-sent": 0,
              "topic": "/hippodamia/commands"
            }
          ]
          "service": {}
        }
        :return:
        """

        process = psutil.Process(os.getpid())

        if len(process.children()) > 0 and self._process_children_warning:
            self._process_children_warning = True
            self._logger.info("process has children (not threads) -> cpu_percent_process and mem_percent_process "
                                 "do not include the values from the children.")

        process_memory_info = process.memory_info()
        total_memory_info = psutil.virtual_memory()
        recv, sent = self._mqtt_client.stats.get_totals()

        message = {
            "gid": self._gid,
            "session": self._session,
            "timestamp": datetime.datetime.now().strftime(self._TIME_FORMAT),
            "service-uptime": time.time() - self._start_time,
            "process-time": time.process_time() - self._start_process_time,
            "system-uptime": time.time() - psutil.boot_time(),
            "cpu_percent_total": round(psutil.cpu_percent(), 1),
            "cpu_percent_process": round(process.cpu_percent() / psutil.cpu_count(), 1),
            "mem_percent_total": round(total_memory_info.percent, 1),
            "mem_percent_process": round(process.memory_percent(), 2),
            "service-memory": round((process_memory_info.rss + process_memory_info.vms) / (1024*1024), 2),
            "disk-free": round(psutil.disk_usage("/").free / (1024*1024), 2),
            "messages-received-total": recv,
            "messages-sent-total": sent,
            "topics": [],
            "service": self._service.runtime_information()
        }

        for topic, stats in self._mqtt_client.stats.stats.items():
            entry = {
                "messages-received": stats.received_messages,
                "messages-sent": stats.sent_messages,
                "topic": topic
            }
            message["topics"].append(entry)

        return json.dumps(message)

    def generate_config_message(self):
        """
        {
          "gid": 1,
          "session": 2,
          "timestamp": "1985-04-12T23:20:50.520Z",
          "service-uptime": 12345.67,
          "config": {}
        }
        :return:
        """
        config_clone = pelops.myconfigtools.dict_deepcopy_lowercase(self._config)
        mask_entries(config_clone)
        service_config_clone = pelops.myconfigtools.dict_deepcopy_lowercase(self._service._config)
        mask_entries(service_config_clone)

        return json.dumps({
            "gid": self._gid,
            "session": self._session,
            "timestamp": datetime.datetime.now().strftime(self._TIME_FORMAT),
            "service-uptime": time.time() - self._start_time,
            "config": config_clone,
            "service-information": self._service.config_information(),
            "service-config": service_config_clone
        })

    def generate_end_message(self, last_will=False):
        """
        {
          "gid": 1,
          "session": 2,
          "reason": last_will  # ["last_will", "agent"]
        }
        :return:
        """
        message = {
            "gid": self._gid,
            "session": self._session,
            "reason": "agent"
        }

        if last_will:
            message["reason"] = "last_will"

        return json.dumps(message)
