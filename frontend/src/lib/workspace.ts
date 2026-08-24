import { useLocation } from 'react-router-dom';

/**
 * Detecte le workspace actif a partir de l'URL ('linux' ou 'admin').
 * Permet aux composants partages entre les deux workspaces (Dashboard,
 * Chat, Incidents...) de construire leurs liens internes dynamiquement
 * (ex: `/${workspace}/chat`) plutot que de coder `/linux/...` en dur -
 * ce qui ferait sortir un admin de son workspace par erreur.
 */
export type Workspace = 'linux' | 'admin';

export function useWorkspaceBase(): Workspace {
  const location = useLocation();
  return location.pathname.startsWith('/admin') ? 'admin' : 'linux';
}