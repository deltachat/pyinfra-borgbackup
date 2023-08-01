#!/bin/bash
set -exuo pipefail

# setup env
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd $DIR
export $(xargs < /root/backup.env)

# check if these variables have been set
echo "$BORG_PASSPHRASE" > /dev/null
echo "$DEST1" > /dev/null
: "${SKIP_CHECK:='false'}"

export BORG_RSH='ssh -F /root/.ssh/config -o "StrictHostKeyChecking=no"'

# don't fail just because the pod is not running
set +e

# check if variable exists: https://stackoverflow.com/a/11369388
if [ "$SKIP_CHECK" = "true" ]; then
  echo "skipping borg check."
else
  borg check ${DEST1} &
  if [ -n "${DEST2-}" ]; then
    borg check ${DEST2} &
  fi
fi
wait

borg create --stats --compression lzma ${DEST1}::'backup{now:%Y-%m-%d-%H}' \
        /                            \
        --exclude *.cache/           \
        --exclude /dev               \
        --exclude /proc              \
        --exclude /sys               \
        --exclude /var/run           \
        --exclude /run               \
        --exclude /lost+found        \
        --exclude /mnt               \
        --exclude /media             \
        --exclude /var/lib/lxcfs &
if [ -n "${DEST2-}" ]; then
  # If there is a second backup destination, create a backup there.
  # Note: not yet supported by pyinfra deploy.
  borg create --stats --compression lzma ${DEST2}::'backup{now:%Y-%m-%d-%H}' \
        /                            \
        --exclude *.cache/           \
        --exclude /dev               \
        --exclude /proc              \
        --exclude /sys               \
        --exclude /var/run           \
        --exclude /run               \
        --exclude /lost+found        \
        --exclude /mnt               \
        --exclude /media             \
        --exclude /var/lib/lxcfs &
fi
wait

set -e
borg prune --keep-daily=7 --keep-weekly=4 ${DEST1}
if [ -n "${DEST2-}" ]; then
  borg prune --keep-daily=7 --keep-weekly=4 ${DEST2}
fi

