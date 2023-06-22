# pyinfra module to deploy our backup solution

This module deploys [borgbackup](https://www.borgbackup.org/),
sets up a backup.sh script,
and a cron job which executes it nightly.
Admins need to generate a passphrase
and store it in our [pass repository](https://git.0x90.space/delta/pass).

## Usage

First you need to generate a passphrase for the borg repository
with `pass generate -n delta/{host}/backup.env`.
This creates an alphanumeric passphrase for the repository.

Then we need to extend this pass entry.
Use `pass edit delta/{host}/backup.env` to edit the entry.
You should leave the generated password intact,
but write `export BORG_PASSPHRASE=` in front of it.
Then you should add some additional variables,
so that it looks similar to this in the end:

```bash
export BORG_PASSPHRASE=g3n3r4t3dp455phr4s3
export BORG_RSH='ssh -F /root/.ssh/config -o "StrictHostKeyChecking=no"'
export DEST1='hetzner-backup/backups/{host}'
export HALT_SERVICES='unattended-upgrades docker libvirtd postfix dovecot nginx'
export HALT_CONTAINERS='mailadm app mailcow_dockerized-dovecot_1 mailcow_dockerized-postfix_1'
export EXCLUDES='-e "*.cache/"'
export SKIP_CHECK='false'
```

Then you can add this module to your pyinfra deploy.py script like this:

```python
from pyinfra_borgbackup import deploy_borgbackup

deploy_borgbackup(host="host")
```

After it has been deployed,
you should login to your host via SSH
and run the script manually at least once,
to create an initial backup
and directly spot possible mistakes.

<!--
It can also be used to deploy borgbackup with an ad-hoc command like this:
```
pyinfra --ssh-user root -- hostname pyinfra_borgbackup.deploy_borgbackup
```
-->
