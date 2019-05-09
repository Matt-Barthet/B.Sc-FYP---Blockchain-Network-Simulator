from Util import *
import hashlib
import numpy as np
'''
Function to generate a random number from an exponential distribution,
contained within an upper and lower bound.
'''
def generateBoundedExponential(values):
    while True:
        value = np.random.exponential(values[0])
        if values[1] < value < values[2]:
            return value

def printLine(text, filename):
    print(text)
    print(text, file=open(filename, "at"))

'''
Block (pure python) class represents a collection of on-chain transactions.
'''
class Block:
    def __init__(self, father = None, process = None, properties = None):
        """
        If the block provided is not the genesis block, create the object according to parent block.
        If the block has no father, ie: is the genesis block of the blockchain, create a preset genesis block.
        """
        if father is not None:
            self.size = properties[0]
            self.transaction_size = properties[1]
            self.transaction_count = properties[2]
            self.father = father
            self.timestamp = time.time()
            self.process = process
            self.depth = father.depth + 1
            string_to_hash = father.hash + str(self.timestamp) + process + str(properties[0]) + str(properties[1]) + str(properties[2])
            hash_object = hashlib.sha256(string_to_hash.encode('utf-8'))
            self.hash = hash_object.hexdigest()
        else:
            self.depth = 1
            self.size = 1024
            self.transaction_count = 1650
            self.transaction_size = 0.64
            self.timestamp = time.time()
            self.father = None
            hash_object = hashlib.sha256(b'genesis')
            self.hash = hash_object.hexdigest()
