"""Tests for vumi.middleware.session_length."""

from twisted.internet.defer import inlineCallbacks, returnValue

from vumi.message import TransportUserMessage
from vumi.middleware.session_length import SessionLengthMiddleware
from vumi.tests.helpers import VumiTestCase, PersistenceHelper

SESSION_NEW, SESSION_CLOSE = (
    TransportUserMessage.SESSION_NEW, TransportUserMessage.SESSION_CLOSE)


class TestStaticProviderSettingMiddleware(VumiTestCase):
    def setUp(self):
        self.persistence_helper = self.add_helper(PersistenceHelper())

    @inlineCallbacks
    def mk_middleware(self, config={}):
        dummy_worker = object()
        config = self.persistence_helper.mk_config(config)
        mw = SessionLengthMiddleware(
            "static_provider_setter", config, dummy_worker)
        yield mw.setup_middleware()
        self.redis = mw.redis
        self.add_cleanup(mw.teardown_middleware)
        returnValue(mw)

    def mk_msg(self, to_addr, from_addr, session_event=SESSION_NEW):
        msg = TransportUserMessage(
            to_addr=to_addr, from_addr=from_addr,
            transport_name="dummy_connector",
            transport_type="dummy_transport_type",
            event_type=session_event)
        return msg

    @inlineCallbacks
    def test_incoming_message_session_length(self):
        mw = yield self.mk_middleware()
        msg_start = self.mk_msg('+12345', '+54231')
        msg_end = self.mk_msg('+12345', '+54231', session_event=SESSION_CLOSE)

        yield mw.handle_inbound(msg_start, "dummy_connector")
        keys = yield self.redis.keys()
        print keys
        value = yield self.redis.get('+54321:session_created')
        print value
        self.assertTrue(value is not None)
        msg = yield mw.handle_inbound(msg_end, "dummy_connector")
        self.assertTrue(isinstance(
                msg['helper_metadata']['billing']['session_length'], float))