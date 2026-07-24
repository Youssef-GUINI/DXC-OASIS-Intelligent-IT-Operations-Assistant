# Administration Docker

## Verification de l'etat

Verifier que le daemon Docker est actif :

    sudo systemctl status docker

Verifier la version :

    docker --version
    docker info

## Gestion des conteneurs

Lister les conteneurs actifs :

    docker ps

Lister tous les conteneurs (actifs et arretes) :

    docker ps -a

Arreter un conteneur :

    docker stop &lt;container_id&gt;

Supprimer un conteneur :

    docker rm &lt;container_id&gt;

Forcer l'arret et la suppression :

    docker rm -f &lt;container_id&gt;

## Gestion des images

Lister les images :

    docker images

Supprimer une image :

    docker rmi &lt;image_id&gt;

Nettoyer les images non utilisees :

    docker image prune -a

## Logs d'un conteneur

Afficher les logs :

    docker logs &lt;container_id&gt;

Suivre les logs en temps reel :

    docker logs -f &lt;container_id&gt;

Afficher les dernieres lignes :

    docker logs --tail 100 &lt;container_id&gt;

## Ressources et performances

Stats en temps reel :

    docker stats

Utilisation du disque par Docker :

    docker system df

Nettoyer completement (conteneurs arretes, reseaux inutilises, images dangling) :

    docker system prune -a

## Docker Compose

Verifier la configuration :

    docker-compose config

Lancer les services :

    docker-compose up -d

Voir les logs :

    docker-compose logs -f

Redemarrer un service specifique :

    docker-compose restart &lt;service&gt;

## Actions correctives

1. Verifier que le daemon tourne : `systemctl status docker`
2. Consulter les logs du conteneur : `docker logs`
3. Verifier les ressources : `docker stats`
4. Nettoyer regulierement avec `docker system prune`
5. Si un conteneur redemarre en boucle : verifier `docker inspect` pour l'Exit Code