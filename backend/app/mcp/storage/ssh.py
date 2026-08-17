"""
app/mcp/storage/ssh.py

Accès SSH unique vers la VM Storage. Tous les tools passent par ici : la
logique de connexion, les timeouts et le traitement des erreurs sont écrits
une seule fois.

Aucun tool ne renvoie de données inventées. Quand la VM est injoignable ou
qu'une commande échoue, on remonte une erreur explicite et l'interface
l'affiche telle quelle plutôt que de combler le vide.
"""

from __future__ import annotations

import shlex

import paramiko

from app.core.config import settings

CONNECT_TIMEOUT_SECONDS = 5
COMMAND_TIMEOUT_SECONDS = 15


class StorageVMError(RuntimeError):
    """VM injoignable, mal configurée, ou commande en échec."""


def _client() -> paramiko.SSHClient:
    missing = [
        name
        for name, value in (
            ("STORAGE_VM_HOST", settings.storage_vm_host),
            ("STORAGE_VM_USER", settings.storage_vm_user),
            ("STORAGE_VM_SSH_KEY_PATH", settings.storage_vm_ssh_key_path),
        )
        if not value
    ]
    # Ces messages sont affichés tels quels dans l'interface, qui est en
    # anglais : ils restent en anglais, contrairement aux commentaires.
    if missing:
        raise StorageVMError(
            f"SSH settings are incomplete in .env: {', '.join(missing)}."
        )

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=settings.storage_vm_host,
            port=settings.storage_vm_port,
            username=settings.storage_vm_user,
            key_filename=settings.storage_vm_ssh_key_path,
            timeout=CONNECT_TIMEOUT_SECONDS,
        )
    except Exception as error:  # noqa: BLE001 -- timeout, auth, DNS…
        raise StorageVMError(
            f"Could not reach {settings.storage_vm_host}: {error}."
        ) from error
    return client


def run(command: str, *, allow_failure: bool = False) -> str:
    """
    Exécute une commande sur la VM et renvoie sa sortie standard.

    `allow_failure` sert aux commandes dont un code de retour non nul est une
    réponse valide (systemctl sur une unit en échec, par exemple).
    """
    client = _client()
    try:
        _, stdout, stderr = client.exec_command(command, timeout=COMMAND_TIMEOUT_SECONDS)
        output = stdout.read().decode(errors="replace")
        exit_status = stdout.channel.recv_exit_status()
        errors = stderr.read().decode(errors="replace").strip()
    except StorageVMError:
        raise
    except Exception as error:  # noqa: BLE001
        raise StorageVMError(f"Command failed on the VM: {error}.") from error
    finally:
        client.close()

    if exit_status != 0 and not allow_failure:
        detail = errors or f"exit status {exit_status}"
        raise StorageVMError(f"`{command.split()[0]}` failed on the VM: {detail}")

    return output


def run_many(commands: dict[str, str], *, allow_failure: bool = True) -> dict[str, str]:
    """
    Exécute plusieurs commandes sur une seule connexion SSH.

    Ouvrir une session par commande coûte cher : les tools qui ont besoin de
    plusieurs lectures (capacité + montages, timers + statuts…) passent par ici.
    """
    client = _client()
    results: dict[str, str] = {}
    try:
        for key, command in commands.items():
            _, stdout, stderr = client.exec_command(command, timeout=COMMAND_TIMEOUT_SECONDS)
            output = stdout.read().decode(errors="replace")
            exit_status = stdout.channel.recv_exit_status()
            errors = stderr.read().decode(errors="replace").strip()

            if exit_status != 0 and not allow_failure:
                raise StorageVMError(
                    f"`{command.split()[0]}` failed on the VM: {errors or exit_status}"
                )
            results[key] = output
    except StorageVMError:
        raise
    except Exception as error:  # noqa: BLE001
        raise StorageVMError(f"Command failed on the VM: {error}.") from error
    finally:
        client.close()

    return results


def quote(value: str) -> str:
    """Échappe un argument venant de l'utilisateur ou du LLM avant de l'injecter."""
    return shlex.quote(value)
