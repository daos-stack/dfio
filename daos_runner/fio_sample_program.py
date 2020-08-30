#! /usr/bin/python3.6
""" Simple test program  to use the DAOS Fio runner to launcgh a test"""
import sys
import math
import datetime
from daos_runner import DaosFioRunner

def main():
    """daos_env file, client config file, numjobs/processes, totalIO/(job/proc), SCM Pool size,
       NVMe poolsize, aggregation mode"""
    fiotest = DaosFioRunner("test_files/env-daos-vish", "test_files/daos_control.yml", "test_files/daos_agent.yml", 32, None, "100G",
                            "500G", "disabled")

    dir_offset = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    print(dir_offset)
    resultdir = "results-multisize-" + dir_offset
    fiotest.start_agent()
    # Using all defaults for  cont_uuid, fstype, cont_chunk, cont_sys
    test_inputs = ["2G", "4G", "8G", "12G"]
    job_array = ["16"]
    chunk_size  = ["1048576"]
    iodepth = ["16"]
    iosizes = ["4096"]
    for m in job_array:
        for i in test_inputs:
            for j in chunk_size:
                for k in iodepth:
                    for l in iosizes: 
                        fiotest.set_iosize(i)
                        if fiotest.create_pool() is -1:
                           sys.exit(-1)
                        fnamew    = "daos-conf-rw-" + i + "-" + j + "-" + k + "-" + m + "-" + l + ".fio"
                        fiotest.create_container(None, None, None, None)
                        fiotest.setup_fio_config(fnamew, l, k, j, m, "randwrite")
                        fiotest.run_fio_test(fnamew, resultdir, "rw-" + i + "-" + j + "-" + k + "-" + m + "-" + l)
                        fiotest.destroy_pool()
    fiotest.stop_agent()

if __name__ == "__main__":
    main()
