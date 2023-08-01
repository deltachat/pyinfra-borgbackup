import importlib.resources
import passpy
import pyinfra
import random
from io import StringIO

from pyinfra.operations import apt, files, server


def parse_variable_from_env(env: str, var: str) -> str:
    for line in env.splitlines():
        if var in line.lower():
            return line.strip(var.upper()).strip("=").strip("'").strip('"')


def deploy_borgbackup(host: str, borg_initialized: bool):
    """Deploy borgbackup.

    :param host: the name of the host which you want to backup, e.g. page.
    """

    # get pass secret, else skip deployment
    pass_path = f"delta/{host}/backup.env"
    try:
        store = passpy.Store()
        env = store.get_key(pass_path)
    except KeyError:
        readme_url = "https://github.com/deltachat/sysadmin-pyinfra/tree/master/lib/pyinfra_borgbackup/README.md"
        pyinfra.warn(f"Please add the secrets to {pass_path}, see {readme_url} on how to do it.")
        return 

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
    files.put(
        name="create SSH config",
        src=importlib.resources.files(__package__).joinpath("dot_ssh", "config").open("rb"),
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

    files.put(
        name="Deploy .env secrets",
        src=StringIO(env),
        dest="/root/backup.env",
        user="root",
        group="root",
        mode="700",
    )

    borg_passphrase = parse_variable_from_env(env, "BORG_PASSPHRASE")
    borg_repo = parse_variable_from_env(env, "DEST1")
    if not borg_initialized:
        server.shell(
            name="Initialize borg repository",
            commands=["export $(xargs < /root/backup.env) && export BORG_RSH='ssh -F /root/.ssh/config -o \"StrictHostKeyChecking=no\"' && borg init --encryption=repokey $DEST1"],
        )

    files.template(
        name="Create cron job for backup script",
        src=importlib.resources.files(__package__).joinpath("borgbackup.cron"),
        dest="/etc/cron.d/borgbackup",
        user="root",
        group="root",
        mode="644",
        minute=str(random.randint(0, 60)),
        hour=str(random.randint(0, 4)),
    )

