"""
app/mcp/storage/tools/backup.py

Lit les vrais jobs de sauvegarde de la VM Storage : timers systemd et l'état
des units qu'ils déclenchent, via SSH.

Aucune donnée simulée. Tant qu'aucun timer de sauvegarde n'existe sur la VM,
`list_backups()` renvoie une liste vide accompagnée de `configured: False` —
l'interface l'affiche honnêtement au lieu d'inventer des jobs.

Un timer est reconnu comme sauvegarde si son nom contient l'un des motifs de
`_BACKUP_NAME_PATTERNS`. Nommer un timer `backup-*.timer` suffit donc à le
faire apparaître ici — à condition qu'il vienne de l'administrateur et non
d'un paquet de la distribution (voir `_is_storage_backup`).

L'état d'exécution d'un service (`ExecMainStartTimestamp`, `Result`) vit en
mémoire : systemd le remet à zéro à chaque redémarrage de la VM. Lu seul, il
faisait passer tous les jobs en « planifié / jamais exécuté » après un reboot.
Deux sources qui survivent au redémarrage prennent le relais : `LastTriggerUSec`
du timer (adossé à `/var/lib/systemd/timers/stamp-*`) pour la date du dernier
déclenchement, et le journal pour son issue.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from app.mcp.storage.ssh import StorageVMError, quote, run

_BACKUP_NAME_PATTERNS = ("backup", "sauvegarde", "restic", "borg", "borgmatic", "rsnapshot", "duplicity")

# Motifs qui désignent un vrai outil de sauvegarde, par opposition aux motifs
# génériques ci-dessus. Sert à trancher pour les units fournies par la
# distribution : `dpkg-db-backup.timer` (sauvegarde de la base dpkg d'Ubuntu)
# contient "backup" sans être un job de sauvegarde de données.
_BACKUP_TOOL_PATTERNS = ("restic", "borg", "borgmatic", "rsnapshot", "duplicity", "bacula", "amanda", "veeam")

# Répertoires des units livrées par les paquets. Ce que l'administrateur a
# écrit lui-même vit dans /etc/systemd/system ou /run/systemd/system.
_VENDOR_UNIT_DIRECTORIES = ("/usr/lib/systemd/", "/lib/systemd/")

# Sépare les blocs de propriétés quand toutes les units sont lues d une traite.
_UNIT_MARKER = "###OASIS-UNIT="

# Sépare la section des dates de déclenchement, lues pour toutes les units
# d'un coup à la fin de la commande.
_TRIGGER_MARKER = "###OASIS-TRIGGERS"

# Sépare la section des cadences, elle aussi lue pour toutes les units d'un
# bloc (voir `_period_command`).
_PERIOD_MARKER = "###OASIS-PERIODS"

# Occurrences futures demandées à `systemd-analyze calendar` : trois écarts
# consécutifs, de quoi mesurer la cadence d'un calendrier irrégulier
# (`OnCalendar=Mon,Thu`) sans rapatrier tout un calendrier.
_CALENDAR_ITERATIONS = 4

# Propriété de synthèse : date de dernier déclenchement du timer, ramenée en
# epoch sur la VM (voir `_trigger_command`).
_LAST_TRIGGER_PROPERTY = "OasisLastTrigger"

# Messages systemd qui closent une exécution. systemd ne les traduit pas, quelle
# que soit la locale de la VM.
_JOURNAL_FAILURE = "Failed with result"
_JOURNAL_SUCCESS = ("Deactivated successfully", "Finished ")
_JOURNAL_PATTERN = "Failed with result|Deactivated successfully|Finished "

# De quoi retrouver la dernière fin d'exécution sans rapatrier tout le journal.
_JOURNAL_LINES = 6

# `systemctl list-timers` : NEXT LEFT LAST PASSED UNIT ACTIVATES
_LAST_COLUMN = re.compile(r"^(?P<rest>.*?)\s+(?P<unit>\S+\.timer)\s+(?P<service>\S+)\s*$")


def _looks_like_backup(name: str) -> bool:
    lowered = name.lower()
    return any(pattern in lowered for pattern in _BACKUP_NAME_PATTERNS)


def _parse_timer_units(output: str) -> list[str]:
    """Extrait les noms de units .timer d'une sortie `systemctl list-timers`."""
    units = []
    for line in output.splitlines():
        match = _LAST_COLUMN.match(line.strip())
        if match and _looks_like_backup(match.group("unit")):
            units.append(match.group("unit"))
    return units


def _service_for(timer_unit: str) -> str:
    return timer_unit.rsplit(".", 1)[0] + ".service"


def _is_storage_backup(timer_unit: str, properties: dict[str, str]) -> bool:
    """
    Écarte les timers système que le filtre par nom attrape au passage.

    Une unit écrite par l'administrateur est prise telle quelle : la nommer
    `backup-*` suffit à la déclarer comme job. Une unit livrée par un paquet
    n'est retenue que si elle nomme un outil de sauvegarde réel — sinon
    `dpkg-db-backup.timer`, qui sauvegarde la base de paquets d'Ubuntu,
    apparaîtrait comme un job de sauvegarde de données.
    """
    fragment_path = properties.get("FragmentPath", "")
    if not fragment_path.startswith(_VENDOR_UNIT_DIRECTORIES):
        return True

    lowered = timer_unit.lower()
    return any(pattern in lowered for pattern in _BACKUP_TOOL_PATTERNS)


def _unit_commands(timer_unit: str) -> str:
    """État du service déclenché par un timer, précédé de son marqueur."""
    return (
        f"echo {quote(_UNIT_MARKER + timer_unit)}; "
        f"systemctl show --timestamp=unix {quote(_service_for(timer_unit))} -p {_SHOW_PROPERTIES}"
    )


def _trigger_command(timer_units: list[str]) -> str:
    """
    Dates de dernier déclenchement de tous les timers, en une seule commande.

    `systemctl show` coûte environ 250 ms sur la VM : une invocation par timer
    doublait le temps de réponse du dashboard. Les units sont donc lues d'un
    bloc, et les dates ressortent dans l'ordre des arguments — un timer jamais
    déclenché rend une valeur vide, que le `sed` remplace par `@0` pour ne pas
    décaler les suivantes.

    `--timestamp=unix` ne s'applique pas à LastTriggerUSec, que systemd rend
    toujours en texte localisé : `date` la ramène en epoch sur la VM, seul
    endroit où le fuseau et la locale qui l'ont produite sont connus.
    """
    units = " ".join(quote(unit) for unit in timer_units)
    trim = "s/^LastTriggerUSec=$/@0/p; s/^LastTriggerUSec=//p"
    return (
        f"echo {quote(_TRIGGER_MARKER)}; "
        f"systemctl show {units} -p LastTriggerUSec | sed -n {quote(trim)} "
        f"| date -f - +@%s 2>/dev/null"
    )


# Reconstitue, pour chaque unit, ses expressions `OnCalendar`. `systemctl show`
# rend `Id=` *après* les `TimersCalendar=` de la même unit : les expressions
# sont donc accumulées puis attribuées quand le nom de l'unit arrive. Les
# apparier par position serait faux — une unit peut n'avoir aucun calendrier
# (timer monotone) comme en porter plusieurs.
_PERIOD_AWK = (
    "/^TimersCalendar=/ { "
    "s = $0; "
    'sub(/^TimersCalendar={ *OnCalendar=/, "", s); '
    'sub(/ ; next_elapse=.*/, "", s); '
    "specs[n++] = s; next } "
    "/^Id=/ { "
    "unit = substr($0, 4); "
    'for (i = 0; i < n; i++) print unit " " specs[i]; '
    "n = 0 }"
)

# Ne garde que les dates des occurrences, amputées de leur nom de jour :
# `Mon 2026-08-24 04:30:00 UTC` devient `2026-08-24 04:30:00 UTC`, que `date`
# lit quelle que soit la langue de la VM.
_ELAPSE_SED = "s/^ *Next elapse: [^ ]* //p; s/^ *Iteration #[0-9]*: [^ ]* //p"


def _period_command(timer_units: list[str]) -> str:
    """
    Cadence attendue de chaque timer, calculée sur la VM en une seule commande.

    La périodicité ne se déduit pas de l'historique : `backup-restore-test`,
    hebdomadaire, a été relancé à la main un mercredi — l'écart entre son
    dernier passage et le suivant ne vaut alors pas une semaine. Elle est donc
    demandée au calendrier lui-même : `systemd-analyze` déroule les prochaines
    occurrences de l'expression `OnCalendar`, et leurs écarts donnent la
    cadence, indépendamment de ce qui s'est passé jusqu'ici.

    Un `systemctl show` unique couvre toutes les units (~250 ms) ; chaque
    `systemd-analyze` qui suit coûte une vingtaine de millisecondes. Un timer
    monotone (`OnUnitActiveSec`), sans expression de calendrier, ne produit
    aucune ligne : sa cadence reste inconnue, et les seuils retombent sur leur
    valeur par défaut.
    """
    units = " ".join(quote(unit) for unit in timer_units)
    analyze = (
        f"systemd-analyze calendar --iterations={_CALENDAR_ITERATIONS} \"$spec\" 2>/dev/null "
        f"| sed -n {quote(_ELAPSE_SED)} | date -f - +@%s 2>/dev/null | tr '\\n' ' '"
    )
    return (
        f"echo {quote(_PERIOD_MARKER)}; "
        f"systemctl show {units} -p Id -p TimersCalendar "
        f"| awk {quote(_PERIOD_AWK)} "
        f"| while read -r unit spec; do echo \"$unit $({analyze})\"; done"
    )


def _parse_periods(lines: list[str]) -> dict[str, int]:
    """
    Heures entre deux exécutions attendues, par unit.

    On retient le plus grand écart entre occurrences : `OnCalendar=Mon,Thu`
    alterne trois et quatre jours, et c'est le plus long qui dit à partir de
    quand un job est réellement en retard. À l'inverse, deux expressions sur
    la même unit se cumulent — la plus fréquente l'emporte.
    """
    periods: dict[str, int] = {}

    for line in lines:
        unit, _, rest = line.strip().partition(" ")
        moments = [_moment(field) for field in rest.split()]
        if not unit or any(moment is None for moment in moments) or len(moments) < 2:
            continue

        gaps = [
            (later - earlier).total_seconds()
            for earlier, later in zip(moments, moments[1:])
        ]
        hours = int(max(gaps) // 3600)
        if hours <= 0:
            continue
        periods[unit] = min(periods.get(unit, hours), hours)

    return periods


def _split_blocks(output: str) -> tuple[dict[str, list[str]], list[str], list[str]]:
    """Découpe une sortie balisée en blocs par unit et en sections globales."""
    blocks: dict[str, list[str]] = {}
    triggers: list[str] = []
    periods: list[str] = []
    current: list[str] | None = None

    for line in output.splitlines():
        if line.startswith(_UNIT_MARKER):
            current = []
            blocks[line[len(_UNIT_MARKER):].strip()] = current
        elif line.strip() == _TRIGGER_MARKER:
            current = triggers
        elif line.strip() == _PERIOD_MARKER:
            current = periods
        elif current is not None:
            current.append(line)

    return blocks, triggers, periods


def _show_units(timer_units: list[str]) -> tuple[dict[str, dict[str, str]], dict[str, int]]:
    """
    Lit l'état des services déclenchés par les timers, et la cadence attendue
    de chacun, en une seule commande.

    Une exécution par unit coûtait un canal SSH chacune : sur six timers,
    list_backups mettait près de quatre secondes, et le dashboard se figeait
    d'autant à chaque navigation. Les blocs sont séparés par un marqueur, ce
    qui permet de tout obtenir en un seul aller-retour — la cadence comprise,
    pour environ 350 ms de plus sur un relevé qui vaut ensuite une minute.
    """
    commands = [_unit_commands(unit) for unit in timer_units]
    commands.append(_period_command(timer_units))
    blocks, _, periods = _split_blocks(run("; ".join(commands), allow_failure=True))
    units = {unit: _parse_show("\n".join(properties)) for unit, properties in blocks.items()}
    return units, _parse_periods(periods)


def _state_was_lost(properties: dict[str, str]) -> bool:
    """
    Vrai quand l'état du service ne dit rien de sa dernière exécution.

    Deux cas mènent là : le job n'a jamais tourné, ou la VM a redémarré depuis
    son dernier passage — systemd ne conserve `ExecMainStartTimestamp` et
    `Result` que jusqu'au prochain boot. Ils se distinguent en interrogeant le
    timer et le journal, ce que fait `_complete_units`.
    """
    if properties.get("ActiveState") == "activating" or properties.get("SubState") == "running":
        return False
    return not properties.get("ExecMainStartTimestamp")


def _complete_units(units: dict[str, dict[str, str]], timer_units: list[str]) -> dict[str, list[str]]:
    """
    Va chercher ce qui survit au redémarrage, pour les units qui en ont besoin.

    Deuxième aller-retour vers la VM : la date de dernier déclenchement du
    timer, injectée dans les propriétés, et les dernières fins d'exécution du
    journal, renvoyées telles quelles. Il n'a lieu que pour les units dont
    l'état est muet — tant qu'un job a tourné depuis le dernier boot, son état
    suffit et la lecture ne coûte rien.
    """
    commands = [_trigger_command(timer_units)]
    commands += [
        f"echo {quote(_UNIT_MARKER + unit)}; "
        f"journalctl -u {quote(_service_for(unit))} -o short-unix --no-pager -q "
        f"-n {_JOURNAL_LINES} -g {quote(_JOURNAL_PATTERN)} 2>/dev/null"
        for unit in timer_units
    ]
    blocks, triggers, _ = _split_blocks(run("; ".join(commands), allow_failure=True))

    # Les dates sont appariées par position : au moindre écart — `date` en
    # échec, timer disparu entre les deux lectures — on préfère s'en passer
    # plutôt que de prêter à un job la date d'un autre.
    dates = [line.strip() for line in triggers if line.strip()]
    if len(dates) == len(timer_units):
        for unit, moment in zip(timer_units, dates):
            if unit in units:
                units[unit][_LAST_TRIGGER_PROPERTY] = moment

    return {unit: [line for line in logs if line.strip()] for unit, logs in blocks.items()}


def _parse_show(output: str) -> dict[str, str]:
    """Parse une sortie `systemctl show -p Key=Value`."""
    properties: dict[str, str] = {}
    for line in output.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            properties[key.strip()] = value.strip()
    return properties


def _moment(timestamp: str) -> datetime | None:
    """
    Convertit un horodatage systemd en datetime.

    Les units sont interrogées avec `--timestamp=unix`, qui rend les dates sous
    la forme `@1787156198` (secondes epoch) au lieu du texte localisé
    `Wed 2026-08-19 16:16:38 UTC` : c'est la seule forme analysable sans
    dépendre du fuseau ni de la langue de la VM. Une unit qui n'a jamais tourné
    renvoie une valeur vide.
    """
    if not timestamp:
        return None
    try:
        seconds = int(timestamp.lstrip("@"))
    except (TypeError, ValueError):
        return None
    if seconds <= 0:
        return None
    return datetime.fromtimestamp(seconds, tz=timezone.utc)


def _hours_since(moment: datetime | None) -> int | None:
    """Heures écoulées depuis un instant donné."""
    if moment is None:
        return None
    return max(int((datetime.now(timezone.utc) - moment).total_seconds() // 3600), 0)


def _journal_verdict(logs: list[str]) -> tuple[str | None, datetime | None]:
    """
    Issue et date de la dernière exécution d'après le journal, `None` si inconnues.

    Sert quand l'état du service a été perdu au redémarrage : systemd ne garde
    pas l'issue d'une exécution d'un boot à l'autre, alors que le journal —
    persistant sur la VM — conserve les messages qui la closent.

    `journalctl -n` ne rend pas ses lignes triées : on retient la plus récente
    plutôt que la dernière affichée, et l'échec l'emporte à horodatage égal.
    """
    latest: float | None = None
    verdict: str | None = None

    for line in logs:
        stamp, _, message = line.partition(" ")
        try:
            moment = float(stamp)
        except ValueError:
            continue

        if _JOURNAL_FAILURE in message:
            current = "failed"
        elif any(marker in message for marker in _JOURNAL_SUCCESS):
            current = "success"
        else:
            continue

        if latest is None or moment > latest or (moment == latest and current == "failed"):
            latest, verdict = moment, current

    return verdict, datetime.fromtimestamp(latest, tz=timezone.utc) if latest else None


def _job_from_properties(
    timer_unit: str,
    properties: dict[str, str],
    logs: list[str],
    expected_interval_hours: int | None = None,
) -> dict:
    result = properties.get("Result", "")
    active_state = properties.get("ActiveState", "")
    sub_state = properties.get("SubState", "")

    # systemd renvoie `Result=success` sur une unit qui n'a jamais démarré :
    # seul l'horodatage de démarrage distingue « jamais lancé » de « a réussi ».
    # Sans ce test, un job planifié mais jamais exécuté s'afficherait comme
    # une sauvegarde réussie.
    started_at = _moment(properties.get("ExecMainStartTimestamp", ""))
    # Ce que le timer, lui, a retenu du dernier déclenchement. Contrairement à
    # l'état du service, cette date survit à un redémarrage de la VM.
    triggered_at = _moment(properties.get(_LAST_TRIGGER_PROPERTY, ""))
    last_start = started_at

    if active_state == "activating" or sub_state == "running":
        status = "running"
    elif started_at is not None:
        status = "success" if result == "success" else "failed"
    else:
        # Ici l'état du service ne dit rien : soit le job n'a jamais tourné,
        # soit la VM a redémarré depuis son dernier passage — `Result` a alors
        # été remis à `success` et ne parle plus de cette exécution.
        #
        # Le timer donne la date de son dernier déclenchement, le journal
        # l'issue de la dernière exécution ; une relance manuelle
        # (`systemctl start`) n'avançant pas LastTriggerUSec, on retient la
        # plus récente des deux dates.
        verdict, verdict_at = _journal_verdict(logs)
        last_start = max(filter(None, (triggered_at, verdict_at)), default=None)

        if last_start is None:
            status = "scheduled"
        else:
            # Sans verdict — journal tronqué, exécution très ancienne — on
            # n'invente pas un échec : le job ressortira comme périmé via
            # `hours_since_last_success` si sa date le justifie.
            status = verdict or "success"

    hours_since_run = _hours_since(last_start)
    # systemd n'expose pas la date du dernier succès distincte du dernier run :
    # elle n'est connue que si ce dernier run a réussi. 0 signifie "inconnu",
    # ce que les seuils de health.py traitent comme non alarmant.
    hours_since_success = hours_since_run if status == "success" and hours_since_run else 0

    # `ExecMainExitTimestamp` disparaît lui aussi au redémarrage : la date
    # reconstituée ci-dessus est alors le meilleur repère pour l'interface.
    finished_at = _moment(properties.get("ExecMainExitTimestamp", "")) or last_start

    return {
        "job_id": timer_unit,
        "target": properties.get("Description") or _service_for(timer_unit),
        "status": status,
        "last_run": finished_at.isoformat() if finished_at else None,
        "hours_since_last_success": hours_since_success,
        # Heures entre deux exécutions prévues par le calendrier du timer.
        # None quand il n'en a pas (timer monotone) ou qu'il n'a pas pu être
        # lu : les seuils retombent alors sur leur valeur par défaut.
        "expected_interval_hours": expected_interval_hours,
        # `Result` n'est repris que s'il porte sur l'exécution en question :
        # après un reboot il vaut `success` alors que le journal dit l'échec.
        "error_code": result if status == "failed" and started_at is not None else None,
    }


_SHOW_PROPERTIES = (
    "Description,ActiveState,SubState,Result,FragmentPath,"
    "ExecMainStartTimestamp,ExecMainExitTimestamp"
)


def list_backups(target: str | None = None) -> dict:
    """
    Liste les jobs de sauvegarde réellement définis sur la VM.

    `configured: False` signifie qu'aucun timer de sauvegarde n'existe encore —
    ce n'est pas une erreur, juste une VM sur laquelle rien n'a été mis en place.
    """
    try:
        listing = run("systemctl list-timers --all --no-pager --no-legend", allow_failure=True)
        timer_units = _parse_timer_units(listing)

        if not timer_units:
            return {"jobs": [], "configured": False}

        raw, periods = _show_units(timer_units)
    except StorageVMError as error:
        return {"error": str(error), "jobs": []}

    units = {
        unit: properties
        for unit, properties in raw.items()
        if _is_storage_backup(unit, properties)
    }

    incomplete = [unit for unit, properties in units.items() if _state_was_lost(properties)]
    logs: dict[str, list[str]] = {}
    if incomplete:
        try:
            logs = _complete_units(units, incomplete)
        except StorageVMError:
            # Ce complément reste un complément : s'il échoue, les jobs sont
            # rendus avec ce que l'état des services disait déjà.
            logs = {}

    jobs = [
        _job_from_properties(unit, properties, logs.get(unit, []), periods.get(unit))
        for unit, properties in units.items()
    ]

    # Tous les timers retenus par le nom étaient des units système : du point
    # de vue du stockage, aucun job n'est configuré.
    if not jobs:
        return {"jobs": [], "configured": False}

    if target:
        jobs = [job for job in jobs if target in (job["job_id"], job["target"])]
        if not jobs:
            return {"error": f"No backup job named '{target}' on the VM", "jobs": []}

    return {"jobs": jobs, "configured": True}


def get_backup_job_status(target: str | None = None) -> dict:
    """Alias détaillé de list_backups — même source, même format."""
    return list_backups(target)


def run_backup(target: str) -> dict:
    """
    Déclenche immédiatement un job de sauvegarde existant.
    Action non destructive (ajout de données), pas de confirmation requise.
    """
    service = _service_for(target) if target.endswith(".timer") else target
    try:
        run(f"systemctl start {quote(service)}")
    except StorageVMError as error:
        return {"error": str(error), "action": "backup_failed", "target": target}

    return {"action": "backup_started", "target": service, "status": "running"}


def get_backup_logs(job_id: str, lines: int = 20) -> dict:
    """Dernières lignes de journal du job, lues via journalctl."""
    service = _service_for(job_id) if job_id.endswith(".timer") else job_id
    try:
        output = run(
            f"journalctl -u {quote(service)} -n {int(lines)} --no-pager -o short-iso",
            allow_failure=True,
        )
    except StorageVMError as error:
        return {"error": str(error), "job_id": job_id, "logs": []}

    return {
        "job_id": service,
        "logs": [{"line": line} for line in output.strip().splitlines() if line.strip()],
    }
