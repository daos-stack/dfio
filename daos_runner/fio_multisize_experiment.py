#! /usr/bin/python3.6
""" Simple test program  to use the DAOS Fio runner to launcgh a test"""
import sys
import math
from daos_runner import DaosFioRunner

def main():
    """daos_env file, client config file, numjobs/processes, totalIO/(job/proc), SCM Pool size,
       NVMe poolsize, aggregation mode"""
    fiotest = DaosFioRunner("test_files/env-daos-vish", "test_files/daos.yml", 16, None, "450G",
                            "900G", "disabled")

    fiotest.start_agent()
    if fiotest.create_pool() is -1:
        sys.exit(-1)

    # Using all defaults for  cont_uuid, fstype, cont_chunk, cont_sys
#    test_inputs = ["1G", "2G", "4G", "8G", "16G", "20G"]
    test_inputs = ["1G", "2G"]
    for i in test_inputs:
         fiotest.set_iosize(i)

         fnamew = "daos-conf-rw" + i + ".fio"
         fnamer = "daos-conf-rr" + i + ".fio"

         fiotest.create_container(None, None, None, None)
         fiotest.setup_fio_config(fnamew, 4096, 16, 1048576, "randwrite")
         fiotest.setup_fio_config(fnamer, 4096, 16, 1048576, "randread")
         fiotest.run_fio_test(fnamew, "results-multisize", "randwrite-" + i)
         fiotest.run_fio_test(fnamer, "results-multisize", "randread-" + i)
         fiotest.destroy_container()

    fiotest.destroy_pool()
    fiotest.stop_agent()

if __name__ == "__main__":
    main()
