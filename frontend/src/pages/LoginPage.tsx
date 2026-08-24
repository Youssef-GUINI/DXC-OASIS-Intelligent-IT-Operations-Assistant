import { useId, useState, type FormEvent } from 'react';
import { Navigate } from 'react-router-dom';
import { AlertCircle, Eye, EyeOff, ShieldCheck } from 'lucide-react';
import { useAuth } from '@/auth/AuthContext';
import { ApiError } from '@/lib/api';
import { Logo } from '@/components/Logo';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { cn } from '@/lib/cn';

const CONTROL =
  'w-full rounded-lg border border-line bg-white px-3 text-sm text-ink-900 placeholder:text-ink-400 transition-colors focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50';

/** Champ mot de passe avec bouton afficher/masquer, meme style visuel que TextField. */
function PasswordField({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const id = useId();
  const [visible, setVisible] = useState(false);

  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-[13px] font-medium text-ink-700">
        Password
      </label>
      <div className="relative">
        <input
          id={id}
          type={visible ? 'text' : 'password'}
          autoComplete="current-password"
          required
          placeholder="********"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className={cn(CONTROL, 'h-10 pr-10')}
        />
        <button
          type="button"
          onClick={() => setVisible((current) => !current)}
          aria-label={visible ? 'Hide password' : 'Show password'}
          className="focus-ring absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-ink-400 hover:text-ink-700"
        >
          {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );
}

export default function LoginPage() {
  const { user, signIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Un administrator atterrit dans son propre workspace, jamais dans /linux.
  if (user) {
    return <Navigate to={user.role === 'administrator' ? '/admin/dashboard' : '/linux/dashboard'} replace />;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await signIn(email, password, remember);
    } catch (caught) {
      // Volontairement generique : on ne dit jamais si c'est l'email ou le
      // mot de passe qui est faux (evite de reveler a un attaquant qu'un
      // compte existe). Les autres erreurs (reseau, serveur down) restent
      // affichees telles quelles, car ce n'est pas un probleme de securite.
      if (caught instanceof ApiError && (caught.status === 401 || caught.status === 400)) {
        setError('Email or password is incorrect.');
      } else {
        setError(caught instanceof Error ? caught.message : 'Sign in failed.');
      }
      setSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen lg:grid-cols-[1fr_460px]">
      <div className="relative hidden flex-col justify-between overflow-hidden bg-canvas p-12 lg:flex">
        <div
          aria-hidden="true"
          className="absolute -left-32 top-1/4 h-[440px] w-[440px] rounded-full bg-brand-200/40 blur-3xl"
        />
        <div
          aria-hidden="true"
          className="absolute -bottom-24 right-0 h-[380px] w-[380px] rounded-full bg-accent-200/40 blur-3xl"
        />

        <Logo size={40} withWordmark subtitle="Intelligent IT Operations Assistant" />

        <div className="relative max-w-md">
          <h1 className="text-[32px] font-semibold leading-tight tracking-tight text-ink-900">
            A calm, intelligent workspace for IT operations.
          </h1>
          <p className="mt-4 text-[15px] leading-relaxed text-ink-500">
            Incidents, access requests and platform oversight in one place, with OASIS ready to
            guide your team through each one.
          </p>
        </div>

        <p className="relative text-[13px] text-ink-400">
          DXC OASIS · Intelligent IT Operations Assistant
        </p>
      </div>

      <div className="flex items-center justify-center bg-white px-6 py-12">
        <div className="w-full max-w-sm">
          <div className="lg:hidden">
            <Logo size={36} withWordmark />
          </div>

          <h2 className="mt-8 text-2xl font-semibold text-ink-900 lg:mt-0">Sign in</h2>
          <p className="mt-1.5 text-sm text-ink-500">
            Welcome back. Sign in to reach your workspace.
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-4" noValidate>
            <TextField
              label="Email"
              type="email"
              autoComplete="username"
              required
              placeholder="you@oasis.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />

            <PasswordField value={password} onChange={setPassword} />

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