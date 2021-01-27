#!/bin/sh

function help() {
	echo 'usage: ./gen_makefile [options]'
        echo 'required options:'
        echo '  --fio-path=<path>: fio-source directory'
        echo '  --cart-path=<path>: cart install directory'
        echo '  --daos-path=<path>: daos install directory'
        exit 0
}



function build() {
	source .cache_vars
	if [ ! -z "$FIO_DIR" ] && [ ! -z "$CART_DIR" ] && [ ! -z "$DAOS_DIR" ]; then
		make clean
		make
	fi
	exit 0
}	

if [ -f .cache_vars ]; then
	echo "Using cached vars"
	build
fi


#check for input vars if building from scratch
if [ "$#" -ne 3 ]; then
	help
	exit -1
fi

for arg in "$@"; do
    case "$arg" in
    --fio-path=*)
        fiopath=`echo $arg | sed 's/--fio-path=//'`
        ;;
    --cart-path=*)
        cartpath=`echo $arg | sed 's/--cart-path=//'`
        ;;
    --daos-path=*)
        daospath=`echo $arg | sed 's/--daos-path=//'`
        ;;
    --help)
	help
	;;
   esac
done

#delete old cache file
rm .cache_vars

echo "export FIO_DIR=${fiopath}" >> .cache_vars
echo "export CART_DIR=${cartpath}" >> .cache_vars
echo "export DAOS_DIR=${daospath}" >> .cache_vars
build
