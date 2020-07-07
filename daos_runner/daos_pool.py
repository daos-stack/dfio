#! /usr/bin/python3
""" Module for Simplify and wrap all  DAOS pool related operations """
import os
import sys
import subprocess
import shlex
from daos_env import DaosBashEnv

class DaosPool(DaosBashEnv):
    """ Class handling DAOS pool operations at DAOS client side
        attibutes - nvme pool size, scm pool size and aggregation modes
        methods to create pool and destroy pool
        Will add more methods to query status and additional pool operations
    """
    def __init__(self, env, client_config_file, scm_size, nvme_size, agg_mode):
        """ Use the DAOS bash env to create a pool and destroy the pool by
	    default. Currently doesn't support other shell environments yet"""
        DaosBashEnv.__init__(self, env)
        self.client_config = os.getcwd() + "/" + client_config_file
        self.scm_size = scm_size
        self.nvme_size = nvme_size
        self.agg_mode = agg_mode
        self.pool_uuid = None
        self.replicas = None

    def set_reclaim_mode(self):
        """ Set aggregation mode for reclaiming space """
        print("***** Setting aggregation mode to %s******" % self.agg_mode)
        print("UUID: "+ self.pool_uuid +" replicas: "+ str(self.replicas))
        cmd = self.dmg +" -o " + self.client_config
        cmd += " pool set-prop --pool=" + self.pool_uuid
        cmd += " -n=reclaim -v=" + self.agg_mode
        args = shlex.split(cmd)
        try:
            subprocess.check_output(args)
        except subprocess.CalledProcessError as error:
            print("Could not create pool -- failure", error)
            sys.exit(1)

    def create_pool(self):
        """ Wrapper for dmg pool create function """
        print("\n****Creating Pool for this object")
        cmd = self.dmg +" -o " + self.client_config
        cmd += " pool create -s="+ self.scm_size + " -n="
        cmd += self.nvme_size
        args = shlex.split(cmd)
        try:
            res = subprocess.check_output(args)
        except subprocess.CalledProcessError as error:
            print("Could not create pool -- failure", error)
            sys.exit(1)

        columns = res.decode(sys.stdout.encoding).strip().split()
        for column in columns:
            index = columns.index(column) + 1
            if column.upper() == "UUID:":
                self.pool_uuid = columns[index].rstrip(',')
            if column.lower() == "replicas:":
                self.replicas = columns[index].rstrip(',')
        print("****SUCCESS: Pool created")
        self.set_reclaim_mode()

    def destroy_pool(self):
        """ wrapper for  dmg pool  destroy """
        try:
            print("\n****Destroy pool " + self.pool_uuid)
        except AttributeError:
            print("ERROR: No pool created for this object\n")
            return

        cmd = self.dmg +" -o " + self.client_config
        cmd = cmd + " pool destroy --pool="+ self.pool_uuid

        stream = os.popen(cmd)
        pool_output = stream.read()
        print(pool_output)

    def pool_query(self):
        """ print the pool status """
        try:
            print("\n****Pool query for " + self.pool_uuid)
        except AttributeError:
            print("ERROR: No pool to print status\n")
            return

        cmd = self.dmg +" -o " + self.client_config
        cmd = cmd + " pool query --pool="+ self.pool_uuid

    def get_pool_uuid(self):
        """ return pool uuid for this object """
        try:
            print(self.pool_uuid)
        except AttributeError:
            print("ERROR: No Pool created")
            return None

        return self.pool_uuid

    def get_replicas(self):
        """ return number of replicas for this pool object """
        try:
            print(self.replicas)
        except AttributeError:
            print("ERROR: No pool created")
            return None

        return self.replicas
