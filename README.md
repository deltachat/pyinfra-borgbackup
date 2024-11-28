# pyinfra module to deploy our backup solution

This module deploys [borgbackup](https://www.borgbackup.org/),
sets up a backup.sh script,
and a cron job which executes it nightly.
Admins need to generate a passphrase
and store it in our [pass repository](https://git.0x90.space/delta/pass).

## Usage

To backup a host
(called `{host}` in the rest of this guide)
to our backup server [`hetzner-backup`](https://github.com/deltachat/sysadmin/tree/master/backup),
you first need to create an SSH key,
and add the public key to the backup server's
`/home/tech/.ssh/authorized_keys` file.
To do this, run the following commands
(replace `{host}` with the name of your host):

```
export HOST={host}                                      # enter the name of the host you want to backup here
ssh-keygen -q -t ed25519 -f /tmp/$HOST-backup -C $HOST-backup -N ""
scp hetzner-backup:.ssh/authorized_keys /tmp/hetzner-backup_authorized_keys
echo 'command="borg serve --restrict-to-path /home/backups/'$HOST'/",restrict' $(cat /tmp/$HOST-backup.pub) >> /tmp/hetzner-backup_authorized_keys
scp /tmp/hetzner-backup_authorized_keys hetzner-backup:.ssh/authorized_keys
```

Now you need to generate a passphrase for the borg repository
with `pass generate -n delta/{host}/borg-passphrase`.
This creates an alphanumeric passphrase for the repository.

Then you can add this module to your pyinfra deploy.py script like this:

```python
from pyinfra import host
from pyinfra.facts.files import File
from pyinfra_borgbackup import deploy_borgbackup

host_name = "host"
borg_repo = f"hetzner-backup:backups/{host_name}"
borg_passphrase = "s3cr3t"
borg_initialized = host.get_fact(File, "/root/.ssh/backupkey")
deploy_borgbackup(host_name, borg_passphrase, borg_repo, borg_initialized)
```

After it has been deployed,
you should login to your host via SSH
and run `/root/backup.sh` manually at least once,
to create an initial backup
and directly spot possible mistakes.

### Use Your Own Backup Server

If you are not part of the deltachat admin team,
you can not use the default backup server of this module.
In this case, you need to upload the `/root/.ssh/config` file separately,
e.g. in your deploy.py file.

You can take a look at our [`/root/.ssh/config`](https://github.com/deltachat/pyinfra-borgbackup/blob/main/pyinfra_borgbackup/dot_ssh/config) file
and adjust it to your needs.
To upload it during your deploy.py execution,
add somewhere *above* the `deploy_borgbackup()` function call
in your deploy.py file:

```
files.put(
    name="create SSH config",
    src="path/to/the/local/ssh/config",
    dest="/root/.ssh/config",
    user="root",
    group="root",
    mode="600",
)
```

### Stop Services During the Backup

During backup,
it is recommended to halt services
which write data to disk,
so the backups don't get inconsistent.
To stop systemd services
or docker containers
during the `borg create` step
of the `backup.sh` script,
you can create a custom python script.

The `backup.sh` script will try to run `/root/backup-pre.py`,
if the file exists;
it calls it with the argument `stop` before `borg create`
and with the argument `start` in the end
(also if the backup fails for some reason).

You can use the `backup-pre.py` script from this repository
as a template to adjust it for the specific server.
You need to upload the script to `/root/backup-pre.py`
in your deploy.py script,
e.g. directly before the `deploy_borgbackup()` call:

```
from pyinfra import host
from pyinfra.facts.files import File
from pyinfra_borgbackup import deploy_borgbackup

borg_initialized = host.get_fact(File, "/root/.ssh/backupkey")
files.rsync(
    name="Upload backup-pre.py",
    src="files/root/backup-pre.py",
    dest="/root/",
)
deploy_borgbackup("bomba", borg_initialized)
```


<!--
It can also be used to deploy borgbackup with an ad-hoc command like this:
```
pyinfra --ssh-user root -- hostname pyinfra_borgbackup.deploy_borgbackup
```
-->
