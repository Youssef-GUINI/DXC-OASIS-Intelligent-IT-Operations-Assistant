import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { api, setUnauthorizedHandler, tokenStore } from '@/lib/api';
import type { CurrentUser } from '@/lib/types';

type AuthContextValue = {
  user: CurrentUser | null;
  /** Vrai tant qu'on n'a pas déterminé si un jeton existant est encore valide. */
  initializing: boolean;
  signIn: (email: string, password: string, remember: boolean) => Promise<void>;
  signOut: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [initializing, setInitializing] = useState(true);

  const signOut = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(signOut);
  }, [signOut]);

  // Reprend la session au chargement : un jeton en stockage ne suffit pas,
  // il faut que le backend le reconnaisse encore.
  useEffect(() => {
    if (!tokenStore.get()) {
      setInitializing(false);
      return;
    }
    api
      .get<CurrentUser>('/auth/me')
      .then(setUser)
      .catch(() => tokenStore.clear())
      .finally(() => setInitializing(false));
  }, []);

  const signIn = useCallback(async (email: string, password: string, remember: boolean) => {
    const { access_token } = await api.post<{ access_token: string }>('/auth/login', {
      email,
      password,
    });
    tokenStore.set(access_token, remember);
    try {
      setUser(await api.get<CurrentUser>('/auth/me'));
    } catch (error) {
      tokenStore.clear();
      throw error;
    }
  }, []);

  const value = useMemo(
    () => ({ user, initializing, signIn, signOut }),
    [user, initializing, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside AuthProvider');
  return context;
}
