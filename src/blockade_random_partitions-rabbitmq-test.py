'''
simulates blockade's --random partitioning.
@see http://blockade.readthedocs.io/en/latest/commands.html#partition
'''

from rabbitmq_test import test
import random


def random_partition(containers):
    '''
    taken from https://github.com/dcm-oss/blockade/blob/master/blockade/core.py#L411
    :param containers:
    :return:
    @see https://github.com/dcm-oss/blockade/blob/master/blockade/core.py#L411
    '''
    if not containers:
        return []

    num_containers = len(containers)
    num_partitions = random.randint(2, num_containers)

    pick = lambda: containers.pop(random.randint(0, len(containers) - 1))

    # pick at least one container for each partition
    partitions = [[pick()] for _ in xrange(num_partitions)]

    # distribute the rest of the containers among the partitions
    for _ in xrange(len(containers)):
        random_partition = random.randint(0, num_partitions - 1)
        partitions[random_partition].append(pick())

    return partitions


def blockade_random_partition_strategy(nodes):
    for num_att in range(5):
        partitions = [','.join(p) for p in random_partition(nodes[:])]
        if len(partitions) > 0:
            return partitions
    raise Exception("failed to create a partition for %s" % str(nodes))


if __name__ == '__main__':
    test(blockade_random_partition_strategy)
