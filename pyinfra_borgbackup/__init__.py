import importlib.resources
import passpy
import pyinfra

from pyinfra.operations import apt, files, server


def parse_variable_from_env(env: str, var: str) -> str:
    for line in env.splitlines():
        if var in line.lower():
            return line.strip("export ").strip(var.upper()).strip("=").strip("'").strip('"')


def deploy_borgbackup(host: str):
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
    # :todo create SSH key
    files.put(
        name="create SSH config",
        src=importlib.resources.files(__package__).joinpath("dot_ssh", "config").open("rb"),
        dest="/root/.ssh/config",
        user="root",
        group="root",
        mode="600",
    )
    # :todo add public key to backup-server's authorized_keys file
        # how to run command on hetzner-backup from this pyinfra task?
        # how to get public key from the host? 
            # e.g. generate it on the local machine and copy it there
            # but take care the step is skipped if the SSH key already exists on the host

    apt.packages(
        name="Install borgbackup",
        packages=["borgbackup"],
    )
    # :todo consider requiring a specific borg version?

    borg_passphrase = parse_variable_from_env(env, "BORG_PASSPHRASE")
    borg_repo = parse_variable_from_env(env, "DEST1")
    # :todo borg init
        # how to pass borg_passphrase to borg init? environment variable? pipe? CLI option?
        # ensure that script doesn't break if borg repository already exists

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
        src=importlib.resources.files(__package__).joinpath("backup.sh").open("rb"),
        dest="/root/backup.env",
        user="root",
        group="root",
        mode="700",
    )

    files.template(
        name="Create cron job for backup script",
        src=importlib.resources.files(__package__).joinpath("borgbackup.cron").open("rb"),
        dest="/etc/cron.d/borgbackup",
        user="root",
        group="root",
        mode="644",
        minute=str(random.randint(0, 60)),
        hour=str(random.randint(0, 4)),
    )

