#! /usr/bin/python3.6
""" Simple test program  to use the DAOS Fio runner to launcgh a test"""
import sys
from daos_runner import DaosFioRunner

def main():
    """daos_env file, client config file, numjobs/processes, totalIO/(job/proc), SCM Pool size,
       NVMe poolsize, aggregation mode"""

    fiotest = DaosFioRunner("test_files/env-daos-vish", "test_files/daos.yml", 32, "12G", "120G",
                            "500G", "disabled")

    fiotest.start_agent()
    if fiotest.create_pool() is -1:
        sys.exit(-1)

    # Using all defaults for  cont_uuid, fstype, cont_chunk, cont_sys
    fiotest.create_container(None, None, None, None)
    # Create FIO config file at runtime config file output,
    # Transfer-size/blocksize, numjobs, chunksize, operation
    fiotest.setup_fio_config("daos-config-rw.fio", 4096, 16, 1048576, "randwrite")
    fiotest.setup_fio_config("daos-config-rr.fio", 4096, 16, 1048576, "randread")
    # Run fio - config-file, output-dir, output-file"""
    fiotest.run_fio_test("daos-config-rw.fio", "sample", "randwrite-test")
    fiotest.run_fio_test("daos-config-rr.fio", "sample", "randread-test")
    #destroy pool -- encompasses destroying container.
    fiotest.destroy_pool()
    fiotest.stop_agent()

if __name__ == "__main__":
    main()
