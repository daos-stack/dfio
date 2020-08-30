#! /usr/bin/python
import os
import sys
import yaml
import pprint
import datetime
import ast

import argparse
from os import path
from daos_runner import DaosFioRunner


dictionary = {}
def create_fio_tester_obj(env_file, client_file, agent_file, jobs, scm, nvme, agg_mode):
    """daos_env file, client config file, numjobs/processes, totalIO/(job/proc), SCM Pool size,
    NVMe poolsize, aggregation mode"""
    fiotest = DaosFioRunner(env_file, client_file, agent_file, jobs, None, scm, nvme, agg_mode) 
    return fiotest


def main():
    parser = argparse.ArgumentParser(description='DAOS fio runner')
    parser.add_argument('--fio-runner-config', metavar='/path/to/config',
                         help='Path to fio runner config file',
                         dest='fio_runner_path')

    if (len(sys.argv) < 2):
        parser.print_help()
        sys.exit(-1)

    result = parser.parse_args()
    fname  = result.fio_runner_path
    cconfig = ''
    with open(fname, 'r') as stream:
      for line in stream:
          if not line.startswith("#"):
                key, value = line.partition(":")[::2]
                if (key == "env_file_with_path"):
                    env_file = value.strip()
                elif (key == "control_config_file"):
                    client_file = value.strip()
	        elif (key == "agent_config_file"):
                    agent_file = value.strip()
                elif (key == "num_jobs"):
                    jobs = ast.literal_eval(value.strip())
                elif (key == "data_size"):
                    data_size = ast.literal_eval(value.strip())
                elif (key == "scm_size"):
                    scm = value.strip()
                elif (key == "nvme_size"):
                    nvme = value.strip()
                elif (key == "iodepth"):
                    depth = ast.literal_eval(value.strip())
                elif (key == "chunk_size"):
                    chunks = ast.literal_eval(value.strip())
                elif (key == "agg_mode"):
                    mode = ast.literal_eval(value.strip())
		elif (key == "iosizes"):
                    iosizes = ast.literal_eval(value.strip())
		elif (key == "io_operations"):
                    iop = ast.literal_eval(value.strip())
                elif (key == "custom_config"):
                    cconfig = value.strip()

    fiotest = create_fio_tester_obj(env_file, client_file, agent_file, jobs, scm,
                                    nvme, mode)
    dir_offset = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    fiotest.start_agent()
    if fiotest.create_pool() is -1:
       sys.exit(-1)

    for i in jobs:
        for j in chunks:
           for k in data_size:
              for l in depth:
                 for m in iosizes:
                    for n in iop:
                     fiotest.set_iosize(k)
                     fiotest.create_container(None, None, None, None)
                     cprefix = i + "_" + j + "_" + k + "_" + l + "_" + m
                     resultdir = "result_" + cprefix + "_" + dir_offset

                     if cconfig:
                         fiotest.run_fio_test(cconfig, resultdir, "cconfig-" + cprefix)
                     elif (n == "randwrite"):
                         fnamew = "config" + cprefix + "_rw" + ".fio"
                         fiotest.setup_fio_config(fnamew, m, l, j, i, "randwrite")
                         fiotest.run_fio_test(fnamew, resultdir, "randwrite-" + cprefix)
                     elif (n == "randread"):
                         fnamew = "config" + cprefix + "_rw" + ".fio"
                         fiotest.setup_fio_config(fnamew, m, l, j, i, "randwrite")
                         fiotest.run_fio_test(fnamew, resultdir, "randwrite-" + cprefix)
	                 fnamer = "config" + cprefix + "_rr" + ".fio"
            	  	 fiotest.setup_fio_config(fnamer, m, l, j, i, "randread")
		         fiotest.run_fio_test(fnamer, resultdir, "randread-" + cprefix)

    fiotest.destroy_pool()
    fiotest.stop_agent()

if __name__ == "__main__":
    main()

