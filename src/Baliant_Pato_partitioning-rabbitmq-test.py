# -*- coding: utf-8 -*-
from rabbitmq_test import test

ha_all_policy = '{"pattern":"^jepsen\.", "definition":{"ha-mode":"all", ' \
                '"ha-sync-mode":"automatic"}}'


def Baliant_Pato_partitioning_generator(nodes):
    '''
    My cluster: rabbit1, rabbit2, rabbit3 with pause_minority

    1. Publisher A connecting to rabbit1
    2. partition rabbit3 away from rabbit2 and rabbit1 (now rabbit3 is stale pretty quickly, he’s gonna be the future "stale node", >evil laughter<.)
    3. partition rabbit1 away from rabbit2 and rabbit3 (at this point the cluster is stopped, the final two minorities are in sync but dead)
    4. partition rabbit2 away from rabbit1 and rabbit3
    5. heal rabbit3 (cluster is still stopped)
    6. heal rabbit2


    equivalent blockade commands:

      sudo blockade partition n1,n2 n3
      sudo blockade status
      sleep 60;
      sudo blockade partition n1 n2 n3
      sudo blockade status
      sleep 60;
      sudo blockade partition n1 n2,n3
      sudo blockade status
      sleep 60;
      sudo blockade join
      sudo blockade status

    :param nodes:
    :return:
    '''
    t = sorted(nodes)

    # partition rabbit3 away from rabbit2 and rabbit1
    yield ['%s,%s' % (t[0], t[1]), t[2]]
    # partition rabbit1 away from rabbit2 (rabbit3 already away)
    yield t[:]
    # join rabbit3 with rabbit2:
    yield [t[0], '%s,%s' % (t[1], t[2])]
    # partition rabbit2 away rabbit3, and join rabbit1 and rabbit3:
    # yield ['%s,%s' % (t[0], t[2]), t[1]]

    # finally join (all nodes belong to the same partition)
    while True:
        yield [','.join(t)]


partitions_generator = None
def Baliant_Pato_partitioning(nodes):
    if (len(nodes) != 3):
        return ','.join(nodes)

    global partitions_generator
    if not partitions_generator:
        partitions_generator = Baliant_Pato_partitioning_generator(nodes)
    return next(partitions_generator)


if __name__ == '__main__':
    test(Baliant_Pato_partitioning, policy=ha_all_policy, heal_strategy=lambda x: None)
