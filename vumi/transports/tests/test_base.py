from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.trial import unittest

from vumi.tests.fake_amqp import FakeAMQPBroker
from vumi.tests.utils import get_stubbed_worker, UTCNearNow, RegexMatcher
from vumi.message import TransportUserMessage, TransportEvent
from vumi.transports.base import Transport


class TransportTestCase(unittest.TestCase):
    """
    This is a base class for testing transports.

    Not to be confused with BaseTransportTestCase below.
    """

    transport_name = "sphex"
    transport_type = None
    transport_class = None

    def setUp(self):
        self._workers = []
        self._amqp = FakeAMQPBroker()

    def tearDown(self):
        for worker in self._workers:
            worker.stopWorker()

    @inlineCallbacks
    def get_transport(self, config, cls=None, start=True):
        """
        Get an instance of a transport class.

        :param config: Config dict.
        :param cls: The transport class to instantiate.
                    Defaults to :attr:`transport_class`
        :param start: True to start the transport (default), False otherwise.

        Some default config values are helpfully provided in the
        interests of reducing boilerplate:

        * ``transport_name`` defaults to :attr:`self.transport_name`
        """

        if cls is None:
            cls = self.transport_class
        config.setdefault('transport_name', self.transport_name)
        worker = get_stubbed_worker(cls, config, self._amqp)
        self._workers.append(worker)
        if start:
            yield worker.startWorker()
        returnValue(worker)

    def assert_rkey_attr(self, rkey_suffix, obj, tr_name=None):
        if tr_name is None:
            tr_name = self.transport_name
        self.assertEqual("%s.%s" % (tr_name, rkey_suffix), obj.routing_key)

    def assert_basic_rkeys(self, transport):
        self.assert_rkey_attr('event', transport.event_publisher)
        self.assert_rkey_attr('inbound', transport.message_publisher)
        self.assert_rkey_attr('failures', transport.failure_publisher)
        self.assert_rkey_attr('outbound', transport.message_consumer)

    def mkmsg_ack(self, user_message_id='1', sent_message_id='abc',
                  transport_metadata=None):
        if transport_metadata is None:
            transport_metadata = {}
        return TransportEvent(
            event_id=RegexMatcher(r'^[0-9a-fA-F]{32}$'),
            event_type='ack',
            user_message_id=user_message_id,
            sent_message_id=sent_message_id,
            timestamp=UTCNearNow(),
            transport_name=self.transport_name,
            transport_metadata=transport_metadata,
            )

    def mkmsg_delivery(self, status='delivered', user_message_id='abc',
                       transport_metadata=None):
        if transport_metadata is None:
            transport_metadata = {}
        return TransportEvent(
            event_id=RegexMatcher(r'^[0-9a-fA-F]{32}$'),
            event_type='delivery_report',
            transport_name=self.transport_name,
            user_message_id=user_message_id,
            delivery_status=status,
            to_addr='+41791234567',
            timestamp=UTCNearNow(),
            transport_metadata=transport_metadata,
            )

    def mkmsg_in(self, content='hello world', message_id='abc',
                 transport_type=None, transport_metadata=None):
        if transport_type is None:
            transport_type = self.transport_type
        if transport_metadata is None:
            transport_metadata = {}
        return TransportUserMessage(
            from_addr='+41791234567',
            to_addr='9292',
            message_id=message_id,
            transport_name=self.transport_name,
            transport_type=transport_type,
            transport_metadata=transport_metadata,
            content=content,
            timestamp=UTCNearNow(),
            )

    def mkmsg_out(self, content='hello world', message_id='1',
                  in_reply_to=None, transport_type=None,
                  transport_metadata=None, stubs=False):
        if transport_type is None:
            transport_type = self.transport_type
        if transport_metadata is None:
            transport_metadata = {}
        params = dict(
            to_addr='+41791234567',
            from_addr='9292',
            message_id=message_id,
            transport_name=self.transport_name,
            transport_type=transport_type,
            transport_metadata=transport_metadata,
            content=content,
            in_reply_to=in_reply_to,
            )
        if stubs:
            params['timestamp'] = UTCNearNow()
        return TransportUserMessage(**params)


class BaseTransportTestCase(TransportTestCase):
    """
    This is a test for the base Transport class.

    Not to be confused with TransportTestCase above.
    """

    transport_name = 'carrier_pigeon'
    transport_class = Transport

    @inlineCallbacks
    def test_start_transport(self):
        tr = yield self.get_transport({})
        self.assertEqual(self.transport_name, tr.transport_name)
        self.assert_basic_rkeys(tr)
