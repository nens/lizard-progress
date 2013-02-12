'''
Created on Aug 3, 2012

@author: ouayed
'''
import logging

class hdsrLogger():
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    def __init__(self,name,filename):
        logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    filename=filename + ".log",
                    filemode='w')
        self.logger = logging.getLogger(name)
