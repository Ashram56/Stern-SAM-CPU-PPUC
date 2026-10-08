#!/bin/bash
# one routing chunk: DSN in, SES out (Freerouting's DSN output comes back empty)
cd /tmp/claude-0/fr2
in=$1; out=$2; passes=$3
/usr/lib/jvm/java-25-openjdk-amd64/bin/java -Xmx1500m -jar fr.jar --gui.enabled=false --router.fanout.enabled=false --router.optimizer.enabled=false --usage_and_diagnostic_data.disable_analytics=true -de $in -do $out -mp $passes > $out.log 2>&1 < /dev/null
echo done >> $out.log
