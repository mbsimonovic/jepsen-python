'''
@see https://github.com/jepsen-io/jepsen/blob/master/rabbitmq/src/jepsen/rabbitmq.clj
'''
# !/usr/bin/env python
import pika
import sys
import time
import exceptions
import threading
import logging

RABBIT_PORT = 5672


class RabbitmqClient():
    '''
    Is Pika thread safe?

    Pika does not have any notion of threading in the code. If you want to use Pika with threading,
    make sure you have a Pika connection per thread, created in that thread. It is not safe to
    share one Pika connection across threads.
    '''

    def __init__(self, rabbit_host, rabbit_port):
        logging.info('rabbitmq client at %s:%i', rabbit_host, rabbit_port)
        self.rabbit_host = rabbit_host
        self.rabbit_hole = rabbit_port
        self.sent = []
        self.failed = []
        self.dig()

    def dig(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=self.rabbit_host, port=self.rabbit_hole))
        self.channel = self.connection.channel()
        # for publish:
        # jepsen uses confirmation trackings:   (lco/select ch) ; Use confirmation tracking
        # is this the way to enable this in python:

        # http://www.rabbitmq.com/extensions.html#confirms
        self.channel.confirm_delivery()  # Turn on RabbitMQ-proprietary Confirm mode in the channel; Enabled delivery confirmations

        # https://github.com/jepsen-io/jepsen/blob/master/rabbitmq/src/jepsen/rabbitmq.clj#L132
        self.channel.queue_declare(queue='jepsen.queue', durable=True, auto_delete=False, exclusive=False)

    def enqueue(self, message):
        logging.debug('sending %s', message)
        # see http://pika.readthedocs.io/en/0.10.0/examples/blocking_delivery_confirmations.html
        res = self.channel.basic_publish(exchange='',
                                         routing_key='jepsen.queue',
                                         body=message,
                                         properties=pika.BasicProperties(
                                             delivery_mode=2,  # make message persistent
                                             ## in jepsen:     :content-type  "application/edn"
                                             # content_type='text/plain'
                                         ),
                                         mandatory=True)
        if not res:
            raise Exception('Message could not be confirmed')
            # TODO 5sec timeout
            # (if (lco/wait-for-confirms ch 5000)     # ; Block until message acknowledged

    def dequeue(self):
        """Given a channel and an operation, dequeues a value and returns the
        corresponding operation.
          ; auto-ack dynamics mean that even if we issue a dequeue req then crash,
          ; the message should be re-delivered and we can count this as a failure.
        """
        self.channel.basic_qos(prefetch_count=1)
        # see http://pika.readthedocs.io/en/0.10.0/modules/adapters/blocking.html#pika.adapters.blocking_connection.BlockingChannel.basic_get
        method, header, body = self.channel.basic_get(queue='jepsen.queue', no_ack=False)
        if method:
            self.channel.basic_ack(delivery_tag=method.delivery_tag, multiple=False)
        return body

        # TODO timeout

    def close(self):
        try:
            self.connection.close()
        except:
            logging.warning('failed to close the connection')


class JepsenProducer(RabbitmqClient):
    def __init__(self, rabbit_host, rabbit_port, messages_to_send, max_send_attempts, max_reconnect_attempts):
        RabbitmqClient.__init__(self, rabbit_host, rabbit_port)
        self.messages_to_send = messages_to_send
        self.max_send_attempts = max_send_attempts
        self.max_reconnect_attempts = max_reconnect_attempts
        self.thread = threading.Thread(name='rabbit %i' % rabbit_port, target=self._test)
        # to stop producer as soon as the main thread exists:
        self.thread.setDaemon(True)

    def test(self):
        logging.info('starting producer')
        self.thread.start()

    def _test(self):
        self._produce()
        self.report()
        self.close()

    def wait_for_test_to_complete(self, timeout=None):
        self.thread.join(timeout)
        logging.info('producer finished work')

    # (timeout 5000 (assoc op :type :fail :value :timeout)
    #           (let [[meta payload] (lb/get ch queue)
    #                 value          (codec/decode payload)]
    #             (if (nil? meta)
    #               (assoc op :type :fail :value :exhausted)
    #               (assoc op :type :ok :value value)))))
    # timeout = 5
    # def on_timeout():
    #    global connection
    #    connection.close()
    # connection.add_timeout(timeout, on_timeout)
    # if basic_get returns than clear the timeout
    def _produce(self):
        logging.info('sending messages')
        for i in range(self.messages_to_send):
            msg = i + self.messages_to_send * (self.rabbit_hole - RABBIT_PORT)
            for publish_attempt in range(self.max_send_attempts):
                try:
                    self.enqueue(str(msg))
                    self.sent.append(msg)
                    time.sleep(0.1)
                    break
                    # (320, "CONNECTION_FORCED - broker forced connection closure with reason 'shutdown'")
                except pika.exceptions.ConnectionClosed as c:
                    for conn_attempt in range(self.max_reconnect_attempts):
                        try:
                            logging.debug('trying to re-open connection')
                            self.dig()
                            break
                        except:
                            time.sleep(conn_attempt)
                            # time.sleep(1)
                    else:  # failed to re-open
                        self.failed.append(i)
                        logging.error('failed to send %i, cannot connect to rabbit, stopping the test' % msg, c)
                        return
                except exceptions.KeyboardInterrupt as ke:
                    logging.warning('keyboard exception, stopping msg publishing')
                    # failed.append(msg)
                    return
                # except Exception as e:
                except:
                    e = sys.exc_info()[0]
                    if publish_attempt == self.max_send_attempts - 1:
                        logging.exception('failed to send %i' % msg)
                        self.failed.append(i)
                    else:
                        logging.exception('bumpy road', )
                        time.sleep(1)

    def report(self):
        logging.info('failed: %s', self.failed)
        logging.info('sent: %i, failed: %i, total: %i', len(self.sent), len(self.failed), self.messages_to_send)


class JepsenConsumer(RabbitmqClient):
    def __init__(self, rabbit_host, rabbit_port, all_sent, all_failed):
        RabbitmqClient.__init__(self, rabbit_host, rabbit_port)
        self.failed = all_failed
        self.sent = all_sent
        self.lost = set()
        self.unexpected = []

    def wrapup(self):
        # i = raw_input('press ENTER to drain the queue')

        try:
            self._drain()
            logging.warning('RECEIVED: %i, unexpected: %i. %s, LOST MESSAGES %i, %s',
                            len(self.received), len(self.unexpected), self.unexpected, len(self.lost),
                            sorted(list(self.lost)))
        except:
            logging.exception('failed to drain')
        finally:
            self.close()

    def _drain(self):
        # i = raw_input('press ENTER to drain the queue')

        self.received = set()
        # new connection and channel?
        self.dig()

        while True:
            r = self.dequeue()
            if not r or len(r) == 0:
                break
            i = int(r)
            if i in self.received:
                self.unexpected.append(i)
            self.received.add(i)

        self.lost.update(set(self.sent).difference(self.received))
