import importlib.resources
import random
from io import StringIO

from pyinfra.operations import apt, files, server


def deploy_borgbackup(
    host: str,
    passphrase: str,
    borg_repo: str,
    borg_initialized: bool,
    borg_args: str = "/",
    skip_check: bool = False,
    prometheus_file: str | None = None,
):
    """Deploy borgbackup.

    :param host: the name of the host which you want to backup, e.g. page.
    :param passphrase: the passphrase for the borg repository
    :param borg_repo: the address of the borg repository
    :param borg_initialized: whether borg repository was already initialized
    :param borg_args: CLI arguments passed to borg create
    :param skip_check: whether to skip `borg check` during ./backup.sh runs
    :param prometheus_file: file to write prometheus success indicators to, e.g.
        /var/lib/prometheus/node-exporter/borgbackup_finished.prom
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
        key_backup = f"/tmp/{host}-backup"
        try:
            files.put(
                name=f"upload private SSH key from {key_backup}",
                src=key_backup,
                dest="/root/.ssh/backupkey",
                user="root",
                group="root",
                mode="600",
            )
        except IOError as e:
            print(f"ERROR: Could not open SSH key backup: {e}")
            exit(1)

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

    files.template(
        name="Create backup.sh script",
        src=importlib.resources.files(__package__) / "backup.sh.j2",
        dest="/root/backup.sh",
        user="root",
        group="root",
        mode="700",
        borg_args=borg_args,
        prometheus_file=prometheus_file,
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
        minute=f"{random.randint(0, 59):02d}",
        hour=f"{random.randint(0, 4):02d}",
    )
