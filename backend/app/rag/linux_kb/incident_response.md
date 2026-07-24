# Procedure de Reponse aux Incidents Linux

## Classification de l'incident

- P1 (Critical) : Service down, perte de donnees, securite compromise
- P2 (High) : Degradation majeure, performances critiques impactees  
- P3 (Medium) : Incident partiel, contournement disponible
- P4 (Low) : Question informative, amelioration

## Checklist P1 — Premieres 15 minutes

1. [ ] Identifier le scope : un serveur, un cluster, ou global ?
2. [ ] Verifier l'alerte source (monitoring, ticket, appel)
3. [ ] Collecter les metriques : CPU, RAM, Disk, Network
4. [ ] Consulter les logs : `journalctl -b`, `/var/log/`
5. [ ] Identifier le dernier changement (deployment, config)
6. [ ] Communiquer au lead et ouvrir un bridge/war room
7. [ ] Ne PAS redemarrer sans diagnostic prealable

## Escalade

- Si disque plein → Escalader Storage Team (cross-domain)
- Si perte de donnees → Escalader Backup Team + Security
- Si attaque suspecte → Escalader SOC + ne pas toucher aux logs

## Post-incident

- Generer un rapport RCA (Root Cause Analysis)
- Mettre a jour la documentation si nouvelle cause identifiee
- Planifier l'action corrective preventive