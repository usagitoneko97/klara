#!/bin/bash

set -o errexit -o pipefail -o noclobber -o nounset

show_help () {
  echo "<performance-regression> -f <py_file> --ref <commit> [--from <commit>] --min-percentage <perc> --min-runtime <run>s"
}

log () {
  echo "$1" >& 2
}

run () {
    start_time="$(date -u +%s.%N)"
    cmd="python -m klara.py_check $1"
    $cmd
    end_time="$(date -u +%s.%N)"
    elapsed="$(bc <<<"$end_time-$start_time")"
    echo "$elapsed"
}


run_all () {
    runTime=()
    for ((n=0;n<iteration;n++))
    do
        tm=$(run $1)
        log "n$((n+1)) iteration uses $tm second..."
        runTime+=( "$tm" )
    done

    total=0
    for t in "${runTime[@]}"; do
        total=$(bc <<< "$total + $t")
    done
    av=$(bc <<< "scale=3; $total / $iteration")
    echo "$av"
}

compare_runtime () {
  t1=$1 expected_t=$2 commit=$3
    if [ "$(bc <<< "$t1 > $expected_t")" == 1 ]; then
      echo "ERROR! Run time for branch: $commit : $t1 execeed the specified runtime: $expected_t"
      exit 1
    else
      echo "on $commit, run time: $t1 is faster than expected run time: $expected_t"
    fi

}

check_git_status () {
  if [ -n "`git status --porcelain`" ]; then
    echo 'ERROR: the working directory is not clean; commit or stash changes';
    exit 1;
  fi
}

cleanup () {
  rm -rf "${fileArg}.tmp"
  echo "restoring git to: $head"
  git checkout $head
}

trap cleanup EXIT
# -allow a command to fail with !’s side effect on errexit
# -use return value from ${PIPESTATUS[0]}, because ! hosed $?
! getopt --test > /dev/null
if [[ ${PIPESTATUS[0]} -ne 4 ]]; then
    show_help
    exit 1
fi

OPTIONS=f:r:m:p:t:i:
LONGOPTS=file:,ref:,from:,min-percentage:,min-runtime:,iteration:

# -regarding ! and PIPESTATUS see above
# -temporarily store output to be able to check for errors
# -activate quoting/enhanced mode (e.g. by writing out “--options”)
# -pass arguments only via   -- "$@"   to separate them correctly
! PARSED=$(getopt --options=$OPTIONS --longoptions=$LONGOPTS --name "$0" -- "$@")
if [[ ${PIPESTATUS[0]} -ne 0 ]]; then
    # e.g. return value is 1
    #  then getopt has complained about wrong arguments to stdout
    show_help
    exit 2
fi
# read getopt’s output this way to handle the quoting right:
eval set -- "$PARSED"

fileArg=- refArg=- fromArg=- min_percentageArg=- min_runtimeArg=- iterationArg=-
# now enjoy the options in order and nicely split until we see --
while true; do
    case "$1" in
        -f|--file)
            fileArg="$2"
            shift 2
            ;;
        -r|--ref)
            refArg="$2"
            shift 2
            ;;
        -m|--from)
            fromArg="$2"
            shift 2
            ;;
        -p|--min-percentage)
            min_percentageArg="$2"
            shift 2
            ;;
        -t|--min-runtime)
            min_runtimeArg="$2"
            shift 2
            ;;
        -i|--iteration)
            iterationArg="$2"
            shift 2
            ;;
        --)
            shift
            break
            ;;
        *)
            echo "Programming error"
            break
            ;;
    esac
done

if [[ $fileArg == "-" ]]; then
    echo "ERROR in arg."
    show_help
    exit 4
else
  cp -f "$fileArg" "${fileArg}.tmp"
  fileArg="${fileArg}.tmp"
fi

if [[ $refArg == "-" ]]; then
  head=$(git rev-parse --abbrev-ref HEAD)
else
  head=$refArg
fi

if [[ $iterationArg == "-" ]]; then
  iteration=5
else
  iteration=$iterationArg
fi

# handle non-option arguments
if [[ $fromArg == "-" ]]; then
  # only run on current head
  echo "running on single ref..."
  echo "git checking out $head ..."
  git checkout "$head" >/dev/null 2>&1
  echo "running $iteration iterations..."
  t1=$(run_all "$fileArg" "$iteration")
  if [[ $min_percentageArg != "-" ]]; then
    echo "ERROR! please specify --from <commit> to be able to calculate percentage difference"
    show_help
    exit 4
  fi
  if [[ $min_runtimeArg != "-" ]]; then
    compare_runtime $t1 $min_runtimeArg $head
  else
    echo "ERROR! please specify --min_runtime <runtime seconds>! "
    show_help
    exit 4
  fi
else
  echo "running on multiple ref..."
  check_git_status
  echo "git checking out $head ..."
  git checkout "$head" >/dev/null 2>&1
  t1=$(run_all "$fileArg" "$iteration")
  echo "First iteration of $head has average run time of $t1"
  echo ""

  echo "git checking out $fromArg ..."
  git checkout "$fromArg" >/dev/null 2>&1
  t2=$(run_all "$fileArg" "$iteration")
  echo "Second iteration of $fromArg has average run time of $t2"
  if [[ $min_runtimeArg != "-" ]]; then
    compare_runtime $t1 $min_runtimeArg $head
    compare_runtime $t2 $min_runtimeArg $fromArg
  fi
  if [[ $min_percentageArg != "-" ]]; then
    total_perc=$(bc <<< "scale=3; (($t2 - $t1) / $t2) * 100")
    if [ "$(bc <<< "$total_perc >= $min_percentageArg")" == 1 ]; then
      echo "ERROR: Percentage calculated: $total_perc exceed $min_percentageArg"
      exit 1
    else
      if [ "$(bc <<< "$total_perc < 0")" == 1 ]; then
        echo "OH NOOOO"
        echo "first is slower than second by : $(bc <<< "$total_perc * -1")%"
      else
        echo "Congratulation!!"
        echo "first is faster than second by : ${total_perc}%"
      fi
    fi
  fi
fi
exit 0
