#!/bin/bash
# one routing chunk: DSN in, SES out, passes, extra args
cd /tmp/claude-0/fr2
in=$1; out=$2; passes=$3; shift 3
java -Xmx3000m -jar fr.jar --gui.enabled=false --router.fanout.enabled=false --router.optimizer.enabled=false --usage_and_diagnostic_data.disable_analytics=true "$@" -de $in -do $out -mp $passes > $out.log 2>&1 < /dev/null
echo done >> $out.log
