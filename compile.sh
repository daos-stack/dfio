#!/bin/sh

function help() {
	echo 'usage: ./compile.sh [options]'
        echo 'required options:'
        echo '  --fio-path=<path>: fio-source directory'
        echo '  --cart-path=<path>: cart install directory'
        echo '  --daos-path=<path>: daos install directory'
        echo '  --daos-src=<path>: daos src  directory'
        echo '  --clean		 : clean the repo'
        echo '  --help           : Print this menu'
        echo '  --dist-clean     : Clear cache'
        exit 0
}



function build() {
	source $PWD/.cache_vars
	if [ ! -z "$FIO_DIR" ] && [ ! -z "$CART_DIR" ] && [ ! -z "$DAOS_DIR" ]; then
		make clean
		make
	fi
	exit 0
}	

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
    --daos-src=*)
        daossrc=`echo $arg | sed 's/--daos-src=//'`
        ;;
    --clean)
	make clean
        exit
        ;;
    --dist-clean)
	rm $PWD/.cache_vars
        exit
        ;;
    --help)
	help
	;;
   esac
done


if [ -f .cache_vars ]; then
	echo "Using cached vars"
	build
fi


#check for input vars if building from scratch
if [ "$#" -ne 4 ]; then
	help
	exit -1
fi

echo "export FIO_DIR=${fiopath}" >> .cache_vars
echo "export CART_DIR=${cartpath}" >> .cache_vars
echo "export DAOS_DIR=${daospath}" >> .cache_vars
echo "export DAOS_SRC=${daossrc}" >> .cache_vars
build
