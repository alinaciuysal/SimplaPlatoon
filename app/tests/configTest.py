import unittest
import app.Config as cfg

from app.dataproviders.__init__ import createInstance
from app.changeproviders.__init__ import init_change_provider

class ConfigTest(unittest.TestCase):

    def test_kafka_dp(self):
        self.assertTrue(cfg.kafkaHost)
        self.assertTrue(cfg.kafkaPlatoonConfigTopic)
        dp = dict(
            type="kafka_consumer",
            kafka_uri=cfg.kafkaHost,
            topic=cfg.kafkaPlatoonConfigTopic,
            serializer="JSON"
        )
        createInstance(wf=None, dp=dp)
        self.assertTrue(dp["instance"])

    def test_kafka_cp(self):
        self.assertTrue(cfg.kafkaHost)
        self.assertTrue(cfg.kafkaPlatoonConfigTopic)
        wf = dict(
            change_provider=dict(
                type="kafka_producer",
                kafka_uri=cfg.kafkaHost,
                topic=cfg.kafkaPlatoonConfigTopic,
                serializer="JSON"
            )
        )
        init_change_provider(wf=wf)
        self.assertTrue(wf["change_provider"]["instance"])

if __name__ == '__main__':
    unittest.main()
    exit(1)