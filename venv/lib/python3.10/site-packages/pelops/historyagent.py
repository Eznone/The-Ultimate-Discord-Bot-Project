import pelops.logging.mylogger
import collections
import threading
import json
import math
import copy
from datetime import datetime, timedelta
import time


def avg(iterable):
    if len(iterable) == 0:
        return 0
    return sum(iterable)/len(iterable)


def median(iterable):
    if len(iterable) == 0:
        return 0
    pos = int(len(iterable)/2)
    return iterable[pos]


class HistoryAgent:
    """
    Takes provided data, aggregates it and stores it locally up to the defined history length. Optionally, fetches
    old data from dataservice like archippe.

    Request json-message:
    ```
    {
        "from": "2009-11-10T22:00:00Z",
        "to": "2009-11-10T23:00:00Z",
        "group-by": 60  # optional (equal to 0)
    }
    ```

    Response json-message:
    ```
    {
        "first": "2009-11-10T22:00:01Z",
        "last": "2009-11-10T22:59:23Z",
        "len": 49,  # entries in data list
        "topic": "/test/example",
        "version": 2,  # version of the response format
        "group-by": 0,
        "data": [
            {"time": "2009-11-10T22:00:01Z", "value": 17.98},
            {"time": "2009-11-10T22:01:50Z", "value": 13.98},
            {"time": "2009-11-10T22:03:00Z", "value": 11.98},
            ...
            {"time": "2009-11-10T22:59:23Z", "value": 20.0}
        ]
    }
    ```

    additional yaml entries:
        group-by: 300  # in seconds. must be > 0.
        aggregator: avg  # aggregator for group-by. valid values: avg, min, max, median. can be omitted
                           if group-by=0.
        use-dataservice: True  # use the dataservice archippe to fill the chart with persisted data
        dataservice-request-topic-prefix: /dataservice/request
        dataservice-response-topic-prefix: /dataservice/response
    """

    _config = None  # config yaml structure
    _update_available = None  # update available event
    _mqtt_client = None  # mymqttclient instance
    _logger = None  # logger instance

    _max_length = None  # length of history deque

    history = None  # list of aggregated values. each value represents a time slot with the latest at the last pos.
    history_lock = None  # Lock - used to lock the history list whenever it is processed or updated
    _aggregation = None  # list of raw values within one time slot
    _aggregator = None  # method to aggregate the values in _aggregation. the result is added to _history
    _group_by = None  # time slot duration in seconds
    _aggregation_timestamp = None  # timestamp for the current aggregation epoch
    _add_lock = None  # lock that blocks add value
    _topic_sub = None  # topic of interest
    _register_topic_handler = None  # if True, values published to topic_sub will be added automatically.

    _use_dataservice = None  # if set to true, dataservice import is activated
    _dataservice_response_topic = None  # listen to response messages on this topic
    _dataservice_request_topic = None  # publish data requests to this topic
    _TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"  # time format string for influxdb queries
    _TIME_FORMAT2 = "%Y-%m-%dT%H:%M:%SZ"  # time format string for influxdb queries (no subseconds)
    _ACCEPTED_VERSION = 2  # message version that the importer accepts

    def __init__(self, config, max_length, topic_sub, register_topic_handler, update_available, mqtt_client, logger):
        """
        Constructor

        :param config: config yaml structure
        :param max_length: maximum number of entries that histoy keeps (older ones are removed automatically)
        :param topic_sub: topic of interest
        :param register_topic_handler: boolean - if True, values published to topic_sub will be added automatically.
        :param update_available: Event instance. provided by renderer. can be None.
        :param mqtt_client: mymqttclient instance
        :param logger: logger instance
        """

        self._config = config
        self._max_length = max_length
        self._update_available = update_available
        self._mqtt_client = mqtt_client
        self._logger = pelops.logging.mylogger.get_child(logger, __name__)
        self._logger.info("HistoryAgent.__init__")
        self._logger.debug("HistoryAgent.__init__ - config: {}.".format(self._config))

        self._group_by = int(self._config["group-by"])
        if self._group_by <= 0:
            self._logger.error("HistoryAgent.__init__ - 'group-by' must be > 0. ({})".format(self._group_by))
            raise ValueError("HistoryAgent.__init__ - 'group-by' must be > 0. ({})".format(self._group_by))

        if self._config["aggregator"] == "avg":
            self._aggregator = avg
        elif self._config["aggregator"] == "min":
            self._aggregator = min
        elif self._config["aggregator"] == "max":
            self._aggregator = max
        elif self._config["aggregator"] == "median":
            self._aggregator = median
        else:
            self._logger.error("HistoryAgent.__init__ - unknown aggregator '{}'.".format(self._aggregator))
            raise ValueError("HistoryAgent.__init__ - unknown aggregator '{}'.".format(self._aggregator))

        self._topic_sub = topic_sub
        self._register_topic_handler = register_topic_handler

        self._aggregation = []

        self.history = collections.deque(maxlen=self._max_length)
        self.history_lock = threading.Lock()
        self._add_lock = threading.Lock()

        try:
            self._use_dataservice = self._config["use-dataservice"]
        except KeyError:
            self._use_dataservice = False
        try:
            self._dataservice_request_topic = self._config["dataservice-request-topic-prefix"] + topic_sub
        except KeyError:
            pass
        try:
            self._dataservice_response_topic = self._config["dataservice-response-topic-prefix"] + topic_sub
        except KeyError:
            pass

    def start(self):
        """
        Starts the aggregation and the data import service.
        """
        self._logger.debug("HistoryAgent.start - acquiring history_lock")
        with self.history_lock:
            self._logger.debug("HistoryAgent.start - acquired history_lock")
            self.history.clear()
        self._logger.debug("HistoryAgent.start - released history_lock")

        self._aggregation.clear()
        self._aggregation_timestamp = time.time()
        if self._use_dataservice:
            self._mqtt_client.subscribe(self._dataservice_response_topic, self._topic_dataservice_response)
            self._request_dataservice_response()
        if self._register_topic_handler:
            self._mqtt_client.subscribe(self._topic_sub, self._topic_sub_handler)

    def stop(self):
        """
        Stops the aggregation and the data import service.
        """
        if self._register_topic_handler:
            self._mqtt_client.unsubscribe(self._topic_sub, self._topic_sub_handler)
        if self._use_dataservice:
            self._mqtt_client.unsubscribe(self._dataservice_response_topic, self._topic_dataservice_response)
        self._aggregation_timestamp = None

    def set_max_length(self, max_length):
        """
        Changes the length of the history. It entries from history are preserved (up to the max_length).

        :param max_length: int - length of deque
        """

        self._max_length = max_length
        temp_history = collections.deque(maxlen=self._max_length)

        for entry in self.history:
            temp_history.append(entry)

        self.history.clear()
        self.history = temp_history

    def _topic_sub_handler(self, value):
        """
        topic handler - collect all values and as soon as a new aggregation epoch starts move the list to _history
        :param value: incoming value
        """
        value = float(value)
        self._logger.info("HistoryAgent._topic_sub_handler - received value '{}'.".format(value))
        self.add_value(value)

    def add_value(self, value, timestamp=None):
        """
        Adds the provided value to the aggregation cache (which subsequently might trigger aaggreagte to history).

        :param value: float value to be added
        :param timestamp: timestamp (optional). if set to "None", the current time will be used.
        """

        if timestamp is None:
            timestamp = time.time()

        self._logger.info("HistoryAgent.add_value - value: {}, timestamp: {}.".format(value, timestamp))

        self._logger.debug("HistoryAgent.add_value - acquiering _add_lock")
        with self._add_lock:
            self._logger.debug("HistoryAgent.add_value - acquired _add_lock")
            self._add_value(value, timestamp)
        self._logger.debug("HistoryAgent.add_value - released _add_lock")
        self._request_dataservice_response()

    def _new_epoch(self, timestamp, ignore_history_lock = False):
        """
        For each incoming timestamp, it must be checked if one or more entries must be added to self.history. This
        method checks how many time aggregation_to_history should be called to move the epoch to the current time
        stamp. Multiple calls are necessary for example, if no new value has been received for a period much longer
        than group_by. After each call, aggregation time is advanced by the group_by value.

        :param timestamp: current time stamp - epoch should match this value
        :param ignore_history_lock: if True, history_lock is ignored - used during import
        """

        while self._aggregation_timestamp + self._group_by <= timestamp:
            # new epoch - add old value to history/clear aggregation
            self._aggregation_timestamp = self._aggregation_timestamp + self._group_by
            self._aggregation_to_history(self._aggregation_timestamp, ignore_history_lock)

    def _add_value(self, value, timestamp, ignore_history_lock = False):
        """
        Adds the provided value to the aggregation cache and initiates aggregate to history (via method _new_epoch)
        whenever necessary. Internal method - used by import and by add_value.

        :param value: float value to be added
        :param timestamp: timestamp for this value
        :param ignore_history_lock: if True, history_lock is ignored - used during import
        """

        self._new_epoch(timestamp, ignore_history_lock)
        self._logger.info("HistoryAgent._add_value - append value {}.".format(value))
        self._aggregation.append(value)

    def _topic_dataservice_response(self, message):
        """
        Method that is called by the pubsub_client message handler when a message has been published to the topic
         _dataservice_response_topic. Converts the message to a json struct and starts the import if
         _check_if_repsonse_message_is_valid returns true.

        :param message: message received via mqtt.
        """

        self._logger.info("HistoryAgent._topic_dataservice_response - received message with len={} on topic '{}'.".
                          format(len(message), self._dataservice_response_topic))
        if len(self.history) == self._max_length:
            self._logger.info("HistoryAgent._topic_dataservice_response - skipped message / history is fully filled.")
        else:
            response = json.loads(message.decode("utf-8"))
            self._logger.debug("HistoryAgent._topic_dataservice_response - received data: {}".format(response))

            if self._check_if_response_message_is_valid(response):
                self._dataservice_import(response)

    def _get_correct_first_timestamp(self, first_time):
        """
         get first timestamp that satisfies
            * (self._agggregation_timestamp - first) % self._group_by == 0
            * first >= prev_entry["time"]
            * first - prev_entry["time"] < self._group_by

        :param first_time: time stamp
        :return: time stamp that satisfies the above listed rules
        """

        timestamp = self._aggregation_timestamp - \
                    math.floor(
                        # round to 7 digits to avoid numeric problems
                        round((self._aggregation_timestamp - first_time)/self._group_by, 7)
                    ) * self._group_by
        return timestamp

    def _merge_import(self, response_history, history_entries):
        """
        Merge the incoming data with existing data. Add "empty" entries if the time gap between them is to large.
        The result is added to self.history.

        :param response_history: prepared data (either _direct_import or _aggregated_import)
        :param history_entries: save local data
        """

        self._logger.debug("HistoryAgent._merge_import - start")
        self._logger.debug("HistoryAgent._merge_import - merging {} old and {} new entries.".
                           format(len(history_entries), len(response_history)))

        if len(history_entries.keys()) > 0:
            history_first = min(history_entries.keys())
            history_last = max(history_entries.keys())
        else:
            history_first = None
            history_last = None

        response_last = max(response_history.keys())
        response_first = min(response_history.keys())

        self._logger.debug("HistoryAgent._merge_import - response from {} to {} / history from {} to {}.".
                           format(response_first, response_last, history_first, history_last))
        previous_new_history_len = 0

        # merge data
        new_history = []
        # add shifted values from response
        for timestamp, entry in response_history.items():
            new_entry = {"time": timestamp, "value": entry["value"]}
            new_history.append(new_entry)
            if history_first is not None and timestamp + self._group_by >= history_first:
                break

        self._logger.debug("HistoryAgent._merge_import - added {} entries from response.".
                           format(len(new_history)-previous_new_history_len))
        previous_new_history_len = len(new_history)

        # fill gap between last reponse entry to first history entry
        if history_first is None:
            gap = self._gap_in_group_by(self._aggregation_timestamp, response_last)
        else:
            gap = self._gap_in_group_by(history_first, response_last)

        timestamp += self._group_by
        for i in range(gap):
            entry = {"time": timestamp, "value": None}
            new_history.append(entry)
            timestamp += self._group_by

        self._logger.debug("HistoryAgent._merge_import - added {} gap entries.".
                           format(len(new_history)-previous_new_history_len))
        previous_new_history_len = len(new_history)

        # add existing history entries
        for key, entry in history_entries.items():
            entry = {"time": key, "value": entry["value"]}
            new_history.append(entry)

        self._logger.debug("HistoryAgent._merge_import - added {} history entries.".
                           format(len(new_history)-previous_new_history_len))

        # fill data in history (cleared in _dataservice_import)
        for entry in new_history:
            self.history.append(entry)

        self._logger.debug("HistoryAgent._merge_import - copied {} entries into history.".format(len(self.history)))
        self._logger.debug("HistoryAgent._merge_import - finished")

    def _direct_import(self, response_entries):
        """
        Import for group_by values that are equivalent the local group_by value. The received
        entries are shifted to match the local timestamps. Thus, the two neighboring values of one target time stamp
        are merged (weighted average) and added with the desired time stamp to the result.

        :param response_entries: dict of received values that should be imported
        :return: dict with values with the correct time stamps
        """

        self._logger.debug("HistoryAgent._direct_import - start")

        first_time = min(response_entries.keys())
        first_entry = response_entries[first_time]
        del response_entries[first_time]
        prev_value = first_entry["value"]
        timestamp = self._get_correct_first_timestamp(first_time)

        # normalized distance of resulting timestamp to neighboring timestamps
        shift = (timestamp - first_time) / self._group_by

        #avoid numerical problems
        if shift > 0.999999:
            shift = 1
        if shift == 1:
            shift = 0
        if shift < 0.000001:
            shift = 0

        if shift == 0:
            # advance epoche if shift is equal to zero. otherwise the last entry will be skipped.
            timestamp += self._group_by

        # merge data
        response_history = {}
        # add shifted values from response
        for key, entry in response_entries.items():
            if prev_value is not None and entry["value"] is not None:
                value = prev_value * shift + entry["value"] * (1-shift)
            else:
                value = None
            new_entry = {"time": timestamp, "value": value}
            response_history[timestamp] = new_entry
            timestamp += self._group_by
            prev_value = entry["value"]

        self._logger.debug("HistoryAgent._direct_import - added {} entries with a shift of {}.".
                           format(len(response_history), shift))

        self._logger.debug("HistoryAgent._direct_import - finished")
        return response_history

    def _aggregated_import(self, response_entries):
        """
        Import for group_by values that are at least halve or lower than the local group_by value. The received
        entries are aggregated similiarly to incoming values during normal operation.

        :param response_entries: dict of received values that should be imported
        :return: dict with aggregated values with the correct time stamps
        """

        def _move_history(response_history):
            """assign all entris from self.history to response history and clear self.history."""
            for entry in self.history:
                response_history[entry["time"]] = entry
            self.history.clear()

        self._logger.debug("HistoryAgent._aggregated_import - start")

        # save aggregation status
        stored_aggregation_timestamp = self._aggregation_timestamp
        stored_aggregation = copy.copy(self._aggregation)

        # set aggregation status to first received value and empty aggregation list
        self._aggregation_timestamp = self._get_correct_first_timestamp(min(response_entries.keys()))
        self._aggregation.clear()

        # use existing add value mechanism but bypass postprocessing
        response_history = {}
        for timestamp, entry in response_entries.items():
            self._add_value(entry["value"], timestamp=timestamp, ignore_history_lock=True)
            _move_history(response_history)

        # flush values in aggregation to history
        self._new_epoch(timestamp+self._group_by, ignore_history_lock=True)
        _move_history(response_history)

        self._logger.debug("HistoryAgent._aggregated_import - added {} entries.".format(len(response_history)))

        # restore aggregation status
        self._aggregation_timestamp = stored_aggregation_timestamp
        self._aggregation = stored_aggregation

        self._logger.debug("HistoryAgent._aggregated_import - finished")
        return response_history

    def _gap_in_group_by(self, history_first, response_last):
        """
        how many entries are missing between last response and first history entries. must be full multiples
        of group-by. and we are only interested in missing ones -> values must be >= 0. (negative values
        indicate an overlap)

        :param history_first: first time stamp of locally stored values
        :param response_last: last time stamp of recevied values
        :return: int - number of entries that are missing
        """

        if history_first is not None:
            result = max(0, math.floor((history_first - response_last) / self._group_by) -1)
        else:
            result = 0

        self._logger.debug("HistoryAgent._gap_in_group_by - history_first: {}, response_last: {}, result: {}."
                           .format(history_first, response_last, result))

        return result

    def _dataservice_import(self, response):
        """
        Main dataservice import routinge - acquires necessary locks, collects and transforms the data, merges the data
        and releases the locks.

        :param response: data structure with the received message
        """

        self._logger.info("HistoryAgent._dataservice_direct_import - start")
        self._logger.debug("HistoryAgent._dataservice_direct_import - acquiering _add_lock")
        with self._add_lock:
            self._logger.debug("HistoryAgent._dataservice_import - acquired _add_lock")
            self._logger.debug("HistoryAgent._dataservice_direct_import - acquiering history_lock")
            with self.history_lock:
                self._logger.debug("HistoryAgent._dataservice_import - acquired history_lock")
                # fetch old data and clear history
                history_entries = {}
                for entry in self.history:
                    history_entries[entry["time"]] = entry
                try:
                    history_first = min(history_entries.keys())
                except ValueError:
                    history_first = None
                self.history.clear()

                # prepare new data
                response_entries = {}
                for entry in response["data"]:
                    try:
                        ts = datetime.strptime(entry["time"], self._TIME_FORMAT).timestamp()
                    except ValueError:
                        ts = datetime.strptime(entry["time"], self._TIME_FORMAT2).timestamp()
                    response_entries[ts] = entry
                response_last = max(response_entries.keys())

                self._logger.debug("HistoryAgent._dataservice_direct_import - history: {}".format(history_entries))
                self._logger.debug("HistoryAgent._dataservice_direct_import - response: {}".format(response_entries))
                self._logger.debug("HistoryAgent._dataservice_direct_import - history_first: {}, response_last: {}, "
                                   "gap_in_group_by: {}".format(history_first, response_last,
                                                                self._gap_in_group_by(history_first, response_last)))

                if response["group-by"] == self._group_by:
                    response_history = self._direct_import(response_entries)
                else:
                    response_history = self._aggregated_import(response_entries)

                self._merge_import(response_history, history_entries)

                self._logger.debug("HistoryAgent._dataservice_direct_import - new history: {}".format(self.history))

            self._logger.debug("HistoryAgent._dataservice_direct_import - released history_lock")

        self._logger.debug("HistoryAgent.add_value - released _add_lock")

        self._logger.info("HistoryAgent._dataservice_direct_import - finished. merged history ({}) with response ({}) to "
                          "new history ({}).".format(len(history_entries), len(response_entries), len(self.history)))

    def _check_if_response_message_is_valid(self, response):
        """
        Check if the receveid data set should be imported (usually an answer from archippe after sendin a dataservice
        request message). Checks for:
          * version - currently 2
          * group_by value - either the same value as the history service (=direct import) or at least
          halve of it (=aggregated import)
          * length > 0
          * that at least some entries are older than the oldest local value

        :param response: datastruct received from archippe
        :return: boolean - True if the received data should be imported
        """
        group_by = response["group-by"]
        try:
            first = datetime.strptime(response["first"], self._TIME_FORMAT)
        except ValueError:
            first = datetime.strptime(response["first"], self._TIME_FORMAT2)
        try:
            last = datetime.strptime(response["last"], self._TIME_FORMAT)
        except ValueError:
            last = datetime.strptime(response["last"], self._TIME_FORMAT2)

        result = False

        # check if we accept the message or if we skip it
        if response["version"] != self._ACCEPTED_VERSION:
            self._logger.warning("HistoryAgent._check_if_response_message_is_valid - skipped message / expected version '{}'"
                                 " but received version '{}'.".format(self._ACCEPTED_VERSION, response["version"]))
        elif group_by != self._group_by and group_by > (self._group_by / 2):
            # we expect the result to be either exactly our group_by value or with at least double our frequency.
            # in the first case we can add the data (but only if the first timestamp matches our start timestimestamp
            # sufficiently). in the second case we use aggregation_to_history
            self._logger.info("HistoryAgent._check_if_response_message_is_valid - skipped message / expected values for "
                              "group-by are {} and < {} but received {} instead.".
                              format(self._group_by, self._group_by / 2, group_by))
        elif response["len"] == 0:
            self._logger.info("HistoryAgent._check_if_response_message_is_valid - skipped message / received empty data set")
        elif len(self.history) > 0 and first >= datetime.fromtimestamp(self.history[0]["time"]):
            self._logger.info("HistoryAgent._check_if_response_message_is_valid - skipped message / no new data available")
        else:
            self._logger.info("HistoryAgent._topic_dataservice_response - message accepted")
            result = True

        return result

    def _request_dataservice_response(self):
        """
        Send a dataservice request message (usually to archippe) to the topic _dataservice_request-topic. Only
        if use_dataservice is set.
        """

        if self._use_dataservice:
            if self._max_length > len(self.history):
                # start calculation of from-timestamp with current aggregation timestamp - guarantees harmonized
                # group_by results. make time span longer than necessary (+2) to ensure that we have sufficient data.
                first = datetime.fromtimestamp(self._aggregation_timestamp)
                first = first - timedelta(seconds=(self._max_length + 2) * self._group_by)
                message = {
                    "from": first.strftime(self._TIME_FORMAT),
                    "to": datetime.now().strftime(self._TIME_FORMAT),
                    "group-by": self._group_by
                }
                self._logger.info("HistoryAgent._request_dataservice_response - send message '{}' to topic '{}'.".
                                  format(message, self._dataservice_request_topic))
                self._mqtt_client.publish(self._dataservice_request_topic, json.dumps(message))
            else:
                self._logger.debug("HistoryAgent._request_dataservice_response - skipped / history is fully filled.")

    def _aggregation_to_history(self, timestamp, ignore_history_lock = False):
        """
        take all entries in _aggregation, apply _aggregator and add the result to _history.

        :param timestamp: timestamp for the aggregated value entry
        :param ignore_history_lock: if True, history_lock is ignored - used during import
        """

        if len(self._aggregation) > 0:
            aggregation = self._aggregator(self._aggregation)
        else:
            aggregation = None
        entry = {
            "time": timestamp,
            "value": aggregation
        }

        if ignore_history_lock:
            self._logger.debug("HistoryAgent._aggregation_to_history - ignoring history_lock")
            self.history.append(entry)
        else:
            self._logger.debug("HistoryAgent._aggregation_to_history - acquiering history_lock")
            with self.history_lock:
                self._logger.debug("HistoryAgent._aggregation_to_history - acquired history_lock")
                self.history.append(entry)
            self._logger.debug("HistoryAgent._aggregation_to_history - released history_lock")

        self._logger.info("HistoryAgent._aggregation_to_history - add value: {}, time: {}, len history: {}".
                          format(aggregation, timestamp, len(self.history)))
        self._aggregation.clear()
        self._set_update_available()

    def _set_update_available(self):
        """sets the update_available event if it is not None."""
        if self._update_available:
            self._update_available.set()
