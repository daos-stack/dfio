# (C) Copyright 2020 Intel Corporation.
#
# GOVERNMENT LICENSE RIGHTS-OPEN SOURCE SOFTWARE
# The Government's rights to use, modify, reproduce, release, perform, display,
# or disclose this software are subject to the terms of the Apache License as
# provided in Contract No. B609815.
# Any reproduction of computer software, computer software documentation, or
# portions thereof marked with this legend must also reproduce the markings.

# Modify FIO_DIR and DAOS_DIR to the root path of fio and daos, respectively
SRC := daos_fio.c
BIN := daos_fio
SRC2 := daos_fio_async.c
BIN2 := daos_fio_async

CC := gcc
FLAGS := -rdynamic -Wl,-z,nodelete -fPIC
LDFLAGS := -shared -L${CART_DIR}/lib -L${DAOS_DIR}/lib64 -ldl -ldaos -ldfs -ldaos_common -lgurt -luuid
INCLUDES := -I${FIO_DIR} -include ${FIO_DIR}/config-host.h -I${DAOS_DIR}/include -I${CART_DIR}/include -I${DAOS_SRC}/src/include/ 
DEFINES := -D_GNU_SOURCE

all:
	${CC} -c ${FLAGS} ${INCLUDES} ${DEFINES} ${SRC} -o ${BIN}.o
	${CC} ${BIN}.o ${LDFLAGS} -o ${BIN}
	${CC} -c ${FLAGS} ${INCLUDES} ${DEFINES} ${SRC2} -o ${BIN2}.o
	${CC} ${BIN2}.o ${LDFLAGS} -o ${BIN2}

clean:
	rm -rf ${BIN} ${BIN2}
	rm -rf ${BIN}.o ${BIN2}.o

