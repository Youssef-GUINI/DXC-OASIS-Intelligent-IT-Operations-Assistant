"""
app/mcp/storage/tools/repair.py

Réparation de la configuration d'un job de sauvegarde, via SSH.

Jusqu'ici OASIS savait relancer un job en échec, pas corriger ce qui le faisait
échouer. Sur un job dont le dépôt restic est introuvable, relancer ne pouvait
que reproduire la même erreur : l'ingénieur voyait un diagnostic juste suivi
d'une remédiation vouée à rater.

Cet outil traite la cause la plus fréquente et la plus mécanique : un job dont
`RESTIC_REPOSITORY` désigne un chemin qui n'est pas un dépôt, alors que les
autres jobs de sauvegarde de la machine en partagent un qui fonctionne. La
réparation consiste à faire adopter au job en panne le fichier d'environnement
de ses voisins en bonne santé, par un drop-in systemd.

Trois principes tiennent l'outil :

  - Il ne devine rien. Le dépôt de remplacement n'est pas fourni par le modèle
    mais lu sur la machine, et seuls les jobs dont la dernière exécution a
    réussi font office de référence.
  - Il ne touche pas au fichier d'unité. Un drop-in s'annule d'un
    `systemctl revert`, ce que la réécriture d'une unité ne permet pas.
  - Il refuse plutôt que d'approximer. Dépôt déjà valide, voisins en désaccord,
    configuration illisible : dans tous ces cas il explique et s'arrête.

Action modifiant la configuration du système : `confirm=True` requis, comme
pour restore_from_backup. Le seul chemin qui l'accorde reste le bouton
« Confirm » du frontend, via /storage/actions/{id}/confirm.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from app.mcp.storage.ssh import StorageVMError, quote, run, run_many

# Nom du drop-in. Le préfixe numérique fixe l'ordre de lecture par systemd, et
# le nom dit qui l'a écrit : un administrateur qui tombe dessus six mois plus
# tard doit savoir d'où il sort sans avoir à chercher.
DROP_IN_NAME = "50-oasis-repair.conf"

_BACKUP_NAME_PATTERNS = ("backup", "sauvegarde", "restic", "borg", "borgmatic")

# Repertoires des units livrees par les paquets : ce que l'administrateur a
# ecrit lui-meme vit dans /etc/systemd/system. Meme distinction que backup.py.
_VENDOR_UNIT_DIRECTORIES = ("/usr/lib/systemd/", "/lib/systemd/")

# `systemctl show -p Environment` rend « Environment=A=1 B=2 », les valeurs
# contenant un espace étant quotées. shlex serait excessif ici : les variables
# qui nous intéressent sont des chemins.
_ENV_ENTRY = re.compile(r"(\w+)=((?:\"[^\"]*\")|(?:\S*))")

# Messages de restic. « pas de dépôt ici » et « mauvais mot de passe » se
# ressemblent pour un humain pressé et ne veulent pas dire la même chose : le
# premier est réparable par cet outil, le second non.
_MISSING_REPOSITORY = ("no such file or directory", "does not exist", "unable to open config file")
_WRONG_PASSWORD = ("wrong password", "no key found")


def _service_for(target: str) -> str:
    """Un job est désigné par son timer ; la configuration vit sur le service."""
    base = target.rsplit(".", 1)[0] if target.endswith((".timer", ".service")) else target
    return f"{base}.service"


def _parse_environment(raw: str) -> dict[str, str]:
    """Extrait les variables d'une ligne `Environment=…` de systemctl show."""
    _, _, value = raw.partition("=")
    return {
        key: val.strip('"')
        for key, val in _ENV_ENTRY.findall(value.strip())
    }


def _parse_environment_files(raw: str) -> list[str]:
    """
    Extrait les chemins d'une ligne `EnvironmentFiles=/x/y.env (ignore_errors=no)`.

    Le contenu de ces fichiers n'est pas lisible depuis le compte SSH -- ils
    portent des mots de passe et sont en 600 root. C'est voulu, et c'est
    précisément pourquoi la réparation adopte le fichier au lieu de recopier
    les valeurs qu'il contient.
    """
    _, _, value = raw.partition("=")
    return [
        part.split(" ")[0]
        for part in value.strip().split("\n")
        if part.strip() and part.startswith("/")
    ]


def _looks_like_backup(name: str) -> bool:
    lowered = name.lower()
    return any(pattern in lowered for pattern in _BACKUP_NAME_PATTERNS)


def _repository_state(repository: str) -> tuple[str, str]:
    """
    Dit si un chemin est un dépôt restic, sans en connaître le mot de passe.

    `--password-command` reçoit volontairement une valeur fausse : restic lit
    le fichier `config` du dépôt avant de vérifier la clé, donc l'absence de
    dépôt et le mauvais mot de passe produisent deux erreurs distinctes. C'est
    ce qui permet de distinguer « rien ici » de « dépôt bien présent » sans
    manipuler le moindre secret.

    Renvoie (état, message brut) avec état parmi : valid, missing, protected,
    unknown.
    """
    output = run(
        f"sudo -n restic --repo {quote(repository)} "
        f"--password-command {quote('printf x')} cat config 2>&1",
        allow_failure=True,
    )
    lowered = output.lower()

    if '"version"' in lowered:
        return "valid", output.strip()
    if any(marker in lowered for marker in _WRONG_PASSWORD):
        # Le dépôt existe : seul son mot de passe nous échappe, ce qui est
        # normal puisqu'on en a fourni un faux exprès.
        return "protected", output.strip()
    if any(marker in lowered for marker in _MISSING_REPOSITORY):
        return "missing", output.strip()
    return "unknown", output.strip()


def _healthy_donor(service: str) -> tuple[str | None, list[dict]]:
    """
    Le fichier d'environnement que les jobs de sauvegarde de la machine partagent.

    Une machine porte souvent plusieurs destinations -- un dépôt local et un
    dépôt distant, par exemple -- et choisir entre elles est une décision de
    politique de sauvegarde, pas une déduction mécanique. L'outil ne tranche
    donc que lorsque la machine a visiblement une convention :

      - le fichier doit être celui du plus grand nombre de jobs de sauvegarde,
        strictement (une égalité laisse le choix ouvert, donc on s'abstient) ;
      - au moins un job qui l'utilise doit avoir réellement tourné avec succès,
        faute de quoi rien ne prouve que cette configuration fonctionne.

    Les units livrées par la distribution sont écartées : `dpkg-db-backup`
    sauvegarde la base de paquets d'Ubuntu et n'a rien à dire sur le stockage.
    """
    listing = run(
        "systemctl list-units --type=service --all --no-pager --no-legend --plain "
        "| awk '{print $1}'",
        allow_failure=True,
    )
    candidates = [
        unit.strip()
        for unit in listing.splitlines()
        if unit.strip().endswith(".service")
        and _looks_like_backup(unit)
        and unit.strip() != service
    ]
    if not candidates:
        return None, []

    blocks = run_many({
        unit: f"systemctl show {quote(unit)} "
              f"-p EnvironmentFiles -p Result -p ExecMainStartTimestamp -p FragmentPath"
        for unit in candidates
    })

    neighbours: list[dict] = []
    for unit, block in blocks.items():
        files: list[str] = []
        result = ""
        started = ""
        fragment = ""
        for line in block.splitlines():
            if line.startswith("EnvironmentFiles="):
                files.extend(_parse_environment_files(line))
            elif line.startswith("Result="):
                result = line.partition("=")[2].strip()
            elif line.startswith("ExecMainStartTimestamp="):
                started = line.partition("=")[2].strip()
            elif line.startswith("FragmentPath="):
                fragment = line.partition("=")[2].strip()

        if fragment.startswith(_VENDOR_UNIT_DIRECTORIES):
            continue

        neighbours.append({
            "unit": unit,
            "environment_file": files[0] if files else None,
            "result": result,
            "has_run": bool(started),
        })

    groups: dict[str, list[dict]] = {}
    for neighbour in neighbours:
        if neighbour["environment_file"]:
            groups.setdefault(neighbour["environment_file"], []).append(neighbour)

    proven = {
        path: members
        for path, members in groups.items()
        if any(member["has_run"] and member["result"] == "success" for member in members)
    }
    if not proven:
        return None, neighbours

    ranked = sorted(proven.items(), key=lambda item: len(item[1]), reverse=True)
    if len(ranked) > 1 and len(ranked[0][1]) == len(ranked[1][1]):
        return None, neighbours
    return ranked[0][0], neighbours


def _drop_in_body(service: str, previous: str, donor: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return (
        f"# Written by OASIS on {stamp} (repair_backup_repository).\n"
        f"# {service} pointed at {previous}, which is not a restic repository.\n"
        f"# It now reads the environment shared by this host's healthy backup jobs.\n"
        f"# Undo with: sudo systemctl revert {service}\n"
        f"[Service]\n"
        f"EnvironmentFile={donor}\n"
    )


def _drop_in_path(service: str) -> tuple[str, str]:
    directory = f"/etc/systemd/system/{service}.d"
    return directory, f"{directory}/{DROP_IN_NAME}"


def _write_commands(service: str, body: str) -> tuple[str, str]:
    """
    Les deux commandes privilégiées qu'exige le dépôt d'un drop-in.

    Elles sont construites au même endroit pour la vérification de droits et
    pour l'exécution : sonder une commande puis en lancer une autre laisserait
    l'outil annoncer qu'il peut agir avant d'échouer.
    """
    directory, path = _drop_in_path(service)
    return (
        f"sudo -n /usr/bin/install -d -m 755 {quote(directory)}",
        f"printf %s {quote(body)} | sudo -n /usr/bin/tee {quote(path)} > /dev/null",
    )


def _write_drop_in(service: str, body: str) -> None:
    """
    Dépose le drop-in, puis recharge systemd.

    `systemctl edit` ne convient pas : sur systemd 255 il ouvre un éditeur et
    n'accepte pas encore `--stdin` (arrivé en 256). On écrit donc le fichier
    directement, ce qui suppose que le compte SSH ait le droit d'écrire dans
    /etc/systemd/system -- voir le message d'erreur de repair_backup_repository
    quand ce n'est pas le cas.

    `systemctl` est appelé sans sudo, comme partout ailleurs dans ces tools :
    la VM porte une enveloppe /usr/local/bin/systemctl qui ajoute le sudo -n
    elle-même. La préfixer une seconde fois viserait un chemin absent de
    l'allowlist et redemanderait un mot de passe.
    """
    create, write = _write_commands(service, body)
    run(create)
    run(write)
    run("systemctl daemon-reload")


# Ce que sudo répond quand la commande est permise mais exige un mot de passe.
# Le compte appartient au groupe sudo, donc tout lui est « autorisé » : seule
# la liste NOPASSWD est utilisable depuis une session non interactive. Sonder
# avec `sudo -l` avant d'agir donnait donc un faux positif -- on laisse la
# vraie commande échouer, et on traduit son message.
_NEEDS_PASSWORD = ("password is required", "a terminal is required", "askpass")


def _missing_privilege(error: str, service: str, donor: str) -> str | None:
    """Traduit un refus de sudo en consigne exploitable, ou None si autre chose."""
    if not any(marker in error.lower() for marker in _NEEDS_PASSWORD):
        return None
    _, path = _drop_in_path(service)
    return (
        f"This account may not write {path} without a password, so nothing was "
        f"changed. Either grant it — a sudoers rule allowing /usr/bin/install and "
        f"/usr/bin/tee on /etc/systemd/system/*.d/{DROP_IN_NAME} — or apply the "
        f"same change by hand: add `EnvironmentFile={donor}` to {service} and run "
        f"`systemctl daemon-reload`."
    )


def repair_backup_repository(target: str, confirm: bool = False) -> dict:
    """
    Repair a backup job whose restic repository cannot be opened.

    Use this when a backup job fails because its RESTIC_REPOSITORY points at a
    path that is not a restic repository -- the journal shows `unable to open
    config file`. The job is repointed at the repository that this host's
    healthy backup jobs already use, through a systemd drop-in.

    This does not create a new repository and does not touch any backup data.
    It reports what it found and changed. It refuses when the configured
    repository already works, when no healthy neighbour job can be used as a
    reference, or when the neighbours disagree.

    `target` is the job id, for instance `backup-app-critical.timer`.
    """
    service = _service_for(target)

    try:
        block = run(
            f"systemctl show {quote(service)} -p Environment -p EnvironmentFiles -p FragmentPath",
            allow_failure=True,
        )
    except StorageVMError as error:
        return {"action": "repair_failed", "target": target, "error": str(error)}

    environment: dict[str, str] = {}
    current_files: list[str] = []
    fragment = ""
    for line in block.splitlines():
        if line.startswith("Environment="):
            environment.update(_parse_environment(line))
        elif line.startswith("EnvironmentFiles="):
            current_files.extend(_parse_environment_files(line))
        elif line.startswith("FragmentPath="):
            fragment = line.partition("=")[2].strip()

    if not fragment:
        return {
            "action": "repair_failed",
            "target": target,
            "error": f"No systemd unit named {service} on the VM.",
        }

    repository = environment.get("RESTIC_REPOSITORY")
    if not repository:
        return {
            "action": "no_repair_possible",
            "target": target,
            "changed": False,
            "reason": (
                f"{service} does not set RESTIC_REPOSITORY directly; its configuration "
                f"comes from {', '.join(current_files) or 'an environment file'}, which "
                f"this account cannot read. Repair it by hand."
            ),
        }

    try:
        state, detail = _repository_state(repository)
    except StorageVMError as error:
        return {"action": "repair_failed", "target": target, "error": str(error)}

    if state in ("valid", "protected"):
        return {
            "action": "no_repair_needed",
            "target": target,
            "changed": False,
            "repository": repository,
            "reason": (
                f"{repository} is a restic repository. The job fails for another reason — "
                f"read its journal with get_backup_logs."
            ),
        }
    if state == "unknown":
        return {
            "action": "no_repair_possible",
            "target": target,
            "changed": False,
            "repository": repository,
            "reason": f"Could not tell whether {repository} is a repository: {detail}",
        }

    try:
        donor, neighbours = _healthy_donor(service)
    except StorageVMError as error:
        return {"action": "repair_failed", "target": target, "error": str(error)}

    if donor is None:
        return {
            "action": "no_repair_possible",
            "target": target,
            "changed": False,
            "repository": repository,
            "reason": (
                "No healthy backup job on this host shares a single environment file to "
                "copy from, so there is no safe repository to point at."
            ),
            "neighbours": neighbours,
        }

    if not confirm:
        return {
            "action": "repair_requires_confirmation",
            "target": target,
            "service": service,
            "current_repository": repository,
            "adopt_environment_file": donor,
            "plan": (
                f"{repository} is not a restic repository. Add a systemd drop-in to "
                f"{service} so it reads {donor}, the environment shared by this host's "
                f"healthy backup jobs. The unit file itself is left untouched and the "
                f"change is undone with `systemctl revert {service}`."
            ),
        }

    body = _drop_in_body(service, repository, donor)

    try:
        _write_drop_in(service, body)
        after = run(
            f"systemctl show {quote(service)} -p EnvironmentFiles", allow_failure=True
        )
    except StorageVMError as error:
        # Le refus de sudo est le cas courant et il a une suite d'actions
        # precise : on la donne, plutot que de renvoyer la sortie brute.
        return {
            "action": "repair_failed",
            "target": target,
            "service": service,
            "changed": False,
            "error": _missing_privilege(str(error), service, donor) or str(error),
        }

    applied = donor in _parse_environment_files(after.strip() or "EnvironmentFiles=")
    return {
        "action": "repository_repaired" if applied else "repair_failed",
        "target": target,
        "service": service,
        "changed": applied,
        "previous_repository": repository,
        "environment_file": donor,
        "drop_in": f"/etc/systemd/system/{service}.d/{DROP_IN_NAME}",
        "note": (
            "The job now reads the shared backup environment. Re-run it with run_backup "
            "to confirm the fix; undo with `systemctl revert " + service + "`."
        ) if applied else "systemd did not pick up the drop-in.",
        "error": None if applied else "The drop-in was written but systemd still ignores it.",
    }
