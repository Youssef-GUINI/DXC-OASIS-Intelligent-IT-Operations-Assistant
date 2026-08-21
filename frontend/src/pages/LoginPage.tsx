import { useState, type FormEvent } from 'react';
import { Navigate } from 'react-router-dom';
import { AlertCircle, ShieldCheck } from 'lucide-react';
import { useAuth } from '@/auth/AuthContext';
import { Logo } from '@/components/Logo';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';

export default function LoginPage() {
  const { user, signIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to="/storage/dashboard" replace />;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await signIn(email, password, remember);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Sign in failed.');
      setSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen lg:grid-cols-[1fr_460px]">
      {/* Panneau de présentation, masqué sur petits écrans. */}
      <div className="relative hidden flex-col justify-between overflow-hidden bg-canvas p-12 lg:flex">
        {/*
          Visuel de fond. Les deux halos flous restent dessous : si le fichier
          est absent, le panneau garde son apparence d'origine au lieu de
          tomber sur un aplat vide.
        */}
        <div
          aria-hidden="true"
          className="absolute -left-32 top-1/4 h-[440px] w-[440px] rounded-full bg-brand-200/40 blur-3xl"
        />
        <div
          aria-hidden="true"
          className="absolute -bottom-24 right-0 h-[380px] w-[380px] rounded-full bg-accent-200/40 blur-3xl"
        />
        <img
          src="/login-background.png"
          alt=""
          aria-hidden="true"
          // onError : une image manquante afficherait l'icône de vignette
          // cassée par-dessus le panneau. On la retire plutôt du flux.
          onError={(event) => {
            event.currentTarget.style.display = 'none';
          }}
          className="pointer-events-none absolute inset-0 h-full w-full select-none object-cover opacity-90"
        />
        {/*
          Voile clair : le texte sombre du panneau doit rester lisible
          par-dessus les zones saturées du dégradé.
        */}
        <div aria-hidden="true" className="absolute inset-0 bg-canvas/45" />

        {/*
          `relative` indispensable : sans lui, le logo reste en flux statique
          et l'image de fond, positionnée en absolu et déclarée après, se
          peint par-dessus.
        */}
        <div className="relative">
          <Logo size={30} withWordmark subtitle="Intelligent IT Operations Assistant" />
        </div>

        <div className="relative max-w-md">
          {/*
            Instrument Serif n'a qu'une graisse : pas de font-semibold ici,
            qui déclencherait une graisse synthétique épaissie par le
            navigateur et abîmerait le contraste des empattements. La présence
            se joue sur la taille, pas sur le gras.
          */}
          <h1 className="font-display text-[44px] leading-[1.1] tracking-[-0.01em] text-ink-900">
            A calm, intelligent workspace for storage operations.
          </h1>
          <p className="mt-4 text-[15px] leading-relaxed text-ink-500">
            Capacity, backups, performance and incidents in one place — with OASIS watching for the
            things that need you before they become outages.
          </p>
        </div>

        <p className="relative text-[13px] text-ink-400">
          DXC OASIS · Storage Operations workspace
        </p>
      </div>

      {/* Formulaire */}
      <div className="flex items-center justify-center bg-white px-6 py-12">
        <div className="w-full max-w-sm">
          <div className="lg:hidden">
            <Logo size={22} withWordmark />
          </div>

          <h2 className="mt-8 text-2xl font-semibold text-ink-900 lg:mt-0">Sign in</h2>
          <p className="mt-1.5 text-sm text-ink-500">
            Welcome back. Sign in to reach your storage environment.
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-4" noValidate>
            <TextField
              label="Email"
              type="email"
              autoComplete="username"
              required
              placeholder="you@company.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />

            <TextField
              label="Password"
              type="password"
              autoComplete="current-password"
              required
              placeholder="••••••••"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />

            <div className="flex items-center justify-between pt-1">
              <label className="flex cursor-pointer items-center gap-2 text-[13px] text-ink-700">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(event) => setRemember(event.target.checked)}
                  className="h-4 w-4 rounded border-line text-brand-500 focus:ring-brand-400"
                />
                Remember me
              </label>
              <a href="#" className="text-[13px] font-medium text-brand-600 hover:text-brand-700">
                Forgot password?
              </a>
            </div>

            {error && (
              <div
                role="alert"
                className="flex items-start gap-2 rounded-lg border border-danger-200 bg-danger-50 px-3 py-2.5 text-[13px] text-danger-600"
              >
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <Button type="submit" variant="primary" loading={submitting} className="w-full">
              Sign in
            </Button>
          </form>

          <p className="mt-8 flex items-center justify-center gap-1.5 text-[12px] text-ink-400">
            <ShieldCheck className="h-3.5 w-3.5" />
            Secure enterprise access
          </p>
        </div>
      </div>
    </main>
  );
}
