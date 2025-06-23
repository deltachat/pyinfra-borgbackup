import importlib.resources
import pyinfra
import random
from io import StringIO

from pyinfra.operations import apt, files, server


def deploy_borgbackup(
    host: str,
    passphrase: str,
    borg_repo: str,
    borg_initialized: bool,
    skip_check: bool = False,
):
    """Deploy borgbackup.

    :param host: the name of the host which you want to backup, e.g. page.
    :param passphrase: the passphrase for the borg repository
    :param borg_repo: the address of the borg repository
    :param borg_initialized: whether borg repository was already initialized
    :param skip_check: whether to skip `borg check` during ./backup.sh runs
    """

    secrets = [
        f"BORG_PASSPHRASE={passphrase}",
        f"DEST1={borg_repo}",
        "SKIP_CHECK=true" if skip_check else "SKIP_CHECK=false",
    ]
    env = "\n".join(secrets)
    files.put(
        name="upload secrets",
        src=StringIO(env),
        dest="/root/backup.env",
        user="root",
        group="root",
        mode="700",
    )

    # Setup SSH connection for backup job
    if not borg_initialized:
        files.put(
            name=f"upload private SSH key from /tmp/{host}-backup",
            src=f"/tmp/{host}-backup",
            dest="/root/.ssh/backupkey",
            user="root",
            group="root",
            mode="600",
        )
    # Only upload SSH config if it's using the delta backup server;
    # Otherwise leave it to users to upload it before
    if borg_repo.startswith("hetzner-backup:"):
        files.put(
            name="create SSH config",
            src=importlib.resources.files(__package__)
            .joinpath("dot_ssh", "config")
            .open("rb"),
            dest="/root/.ssh/config",
            user="root",
            group="root",
            mode="600",
        )

    apt.packages(
        name="Install borgbackup",
        packages=["borgbackup"],
    )
    # :todo consider requiring a specific borg version?

    files.put(
        name="Create backup.sh script",
        src=importlib.resources.files(__package__).joinpath("backup.sh").open("rb"),
        dest="/root/backup.sh",
        user="root",
        group="root",
        mode="700",
    )

    if not borg_initialized:
        server.shell(
            name="Initialize borg repository",
            commands=[
                "export $(xargs < /root/backup.env) && export BORG_RSH='ssh -F /root/.ssh/config -o \"StrictHostKeyChecking=no\"' && borg init --encryption=repokey $DEST1"
            ],
        )

    files.template(
        name="Create cron job for backup script",
        src=importlib.resources.files(__package__).joinpath("borgbackup.cron"),
        dest="/etc/cron.d/borgbackup",
        user="root",
        group="root",
        mode="644",
        minute=str(random.randint(0, 59)),
        hour=str(random.randint(0, 4)),
    )
