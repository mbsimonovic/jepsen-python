from random import shuffle
from rabbitmq_test import test,same_majority_partition_strategy


def random_majority_partition_strategy(nodes):
    copynames = nodes[:]
    shuffle(copynames)
    return same_majority_partition_strategy(copynames)


if __name__ == '__main__':
    test(random_majority_partition_strategy)
