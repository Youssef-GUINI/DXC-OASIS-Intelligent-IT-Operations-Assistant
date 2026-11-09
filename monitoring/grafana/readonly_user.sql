-- monitoring/grafana/readonly_user.sql
--
-- Utilisateur PostgreSQL dédié à Grafana, en LECTURE SEULE.
--
-- Pourquoi un utilisateur à part ? Grafana n'a besoin que de lire. S'il se
-- connectait avec le compte de l'application, une requête mal écrite (ou un
-- compte Grafana compromis) pourrait modifier ou supprimer des tickets et
-- l'audit. Principe du moindre privilège : chacun n'a que les droits dont il
-- a besoin.
--
-- Il ne voit que les tables utiles aux tableaux de bord. La table `users`
-- (emails, mots de passe hachés) lui reste inaccessible.
--
-- À lancer UNE fois, après les migrations Alembic (les tables doivent exister) :
--   docker exec -i oasis_postgres psql -U <POSTGRES_USER> -d <POSTGRES_DB> \
--     -v db=<POSTGRES_DB> -v grafana_password=<GRAFANA_DB_PASSWORD> \
--     < monitoring/grafana/readonly_user.sql

CREATE ROLE grafana_ro LOGIN PASSWORD :'grafana_password';

GRANT CONNECT ON DATABASE :"db" TO grafana_ro;
GRANT USAGE ON SCHEMA public TO grafana_ro;

GRANT SELECT ON
    incident_tickets,
    action_requests,
    mcp_calls,
    disk_metrics,
    audit_logs
TO grafana_ro;

-- Garde-fou supplémentaire : même si un droit d'écriture était accordé par
-- erreur plus tard, toute transaction de ce compte reste en lecture seule.
ALTER ROLE grafana_ro SET default_transaction_read_only = on;
