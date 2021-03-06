#!/usr/bin/env python
import sys
import time
import logging
import httplib
from base64 import b64encode

from client import JepsenConsumer, JepsenProducer
from blockade.errors import BlockadeError
from nemesis import Nemesis

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] (%(threadName)-10s) %(message)s', )

RABBIT_HOST = '192.168.54.136'
RABBIT_PORT = 5672
TOTAL_MSGS = 5000
MAX_RECONN_ATTEMPTS = 50
MAX_PUBLISH_ATTEMPTS = 10
NUM_NETWORK_PROBLEMS = 5

num_rabbits = int(sys.argv[1]) if len(sys.argv) > 1 else 5

majority = num_rabbits // 2 + 1

exactly_policy = '{"pattern":"^jepsen\.", "definition":{"ha-mode":"exactly", ' \
             '"ha-params":%i,"ha-sync-mode":"automatic"}}' % majority


def node_names(start_id, end_id):
    return ['n%i' % (n + 1) for n in range(start_id, end_id)]


def add_policy(policy, username='guest', password='guest'):
    # we need to base 64 encode it
    # and then decode it to acsii as python 3 stores it as a byte string
    userAndPass = b64encode(b"%s:%s" % (username, password)).decode("ascii")
    headers = {
        'Authorization': 'Basic %s' % userAndPass,
        'Content-Type': 'application/json'
    }

    connection = httplib.HTTPConnection(RABBIT_HOST, 15672)
    policy_url = '/api/policies/%2f/jepsen-policy'
    try:
        connection.request('DELETE', policy_url, headers=headers)
        result = connection.getresponse()
        result.read() # need this for the following requests to work
        if result.status < 300:
            logging.debug('policy deleted')
    except:
        pass
    connection.request('PUT', policy_url, policy, headers=headers)
    result = connection.getresponse()
    result.read()
    try:
        connection.close()
    except:
        pass
    if result.status >= 300:
        raise Exception('failed to add policy: %i, %s'(result.status, result.reason))


def same_majority_partition_strategy(nodes, nemesis):
    num_nodes = len(nodes)
    majority = num_nodes // 2 + 1
    partitions = [','.join(nodes[0:majority]), ','.join(nodes[majority:num_nodes])]
    try:
        nemesis.partition(partitions)
        nemesis.status()
    except BlockadeError as e:
        logging.error('failed to create partition for %s', str(nodes))
        logging.exception(e)

def heal_strategy(nemesis):
    nemesis.heal()
    nemesis.status()

def start_producers(num_rabbits):
    logging.info('starting producers')
    rabbits = []
    for r in range(num_rabbits):
        rabbits.append(
            JepsenProducer(RABBIT_HOST, RABBIT_PORT + r, TOTAL_MSGS, MAX_PUBLISH_ATTEMPTS, MAX_RECONN_ATTEMPTS))
    for r in rabbits:
        r.test()
    time.sleep(2)
    return rabbits


def collect_results(rabbits):
    all_sent = []
    all_failed = []
    for r in rabbits:
        all_sent.extend(r.sent)
        all_failed.extend(r.failed)
    logging.info('%i messages sent, %i failed', len(all_sent), len(all_failed))
    logging.info('draining the queue')
    c = JepsenConsumer(RABBIT_HOST, RABBIT_PORT, all_sent, all_failed)
    c.wrapup()
    logging.info('test is finished')


def wait_for_producers(rabbits):
    logging.info('waiting for producers to finish')
    for r in rabbits:
        r.wait_for_test_to_complete()
    logging.info('producers done')
    time.sleep(60)


def run_nemesis(nodes, partition_strategy, heal_strategy):
    logging.info('releasing nemesis')
    nemesis = Nemesis(nodes)
    for p in range(NUM_NETWORK_PROBLEMS):
        partition_strategy(nodes, nemesis)
        time.sleep(60)
        heal_strategy(nemesis)
        time.sleep(60)
    logging.info('chaining nemesis')
    nemesis.heal()

def test(partition_strategy=same_majority_partition_strategy, policy = exactly_policy, heal_strategy=heal_strategy):
    nodes = node_names(0, num_rabbits)
    add_policy(policy)
    rabbits = start_producers(num_rabbits)
    run_nemesis(nodes, partition_strategy, heal_strategy)
    wait_for_producers(rabbits)
    collect_results(rabbits)


if __name__ == '__main__':
    test()
