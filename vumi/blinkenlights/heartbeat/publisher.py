
from twisted.internet.task import LoopingCall

from vumi.service import Publisher
from vumi.message import Message
from vumi.log import log


class HeartBeatMessage(Message):
    """
    Basically just a wrapper around a dict for now
    """

    def __init__(self, **kw):
        super(HeartBeatMessage, self).__init__(**kw)


class HeartBeatPublisher(Publisher):
    """
    A publisher which send periodic heartbeat messages to the AMQP
    heartbeat.inbound queue
    """

    HEARTBEAT_PERIOD_SECS = 10

    def __init__(self, gen_attrs_func):
        self.routing_key = "heartbeat.inbound"
        self.exchange_name = "vumi.health"
        self.durable = True
        self._task = None
        self._gen_attrs_func = gen_attrs_func

    def _beat(self):
        """
        Read various host and worker attributes and wrap them in a message
        """
        attrs = self._gen_attrs_func()
        log.msg("attrs: " % attrs)
        msg = HeartBeatMessage(**attrs)
        self.publish_message(msg)
        log.msg("Sent message: %s" % msg)

    def start(self, channel):
        super(HeartBeatPublisher, self).start(channel)
        self._start_looping_task()

    def _start_looping_task(self):
        self._task = LoopingCall(self._beat)
        done = self._task.start(HeartBeatPublisher.HEARTBEAT_PERIOD_SECS,
                                now=False)
        done.addErrback(
            lambda failure: log.err(failure,
                                    "HeartBeatPublisher task died"))

    def stop(self):
        """Stop publishing metrics."""
        if self._task:
            self._task.stop()
            self._task = None