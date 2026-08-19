import { LogOut } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardBody, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { useAuth } from '@/auth/AuthContext';
import { humanize } from '@/lib/format';

export default function SettingsPage() {
  const { user, signOut } = useAuth();

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title="Settings" subtitle="Your account and workspace details." />

      <Card>
        <CardHeader title="Account" subtitle="Managed by your administrator." />
        <CardBody className="pt-4">
          <dl className="grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-[12px] text-ink-500">Name</dt>
              <dd className="mt-0.5 text-[13px] font-medium text-ink-900">{user?.full_name}</dd>
            </div>
            <div>
              <dt className="text-[12px] text-ink-500">Email</dt>
              <dd className="mt-0.5 text-[13px] font-medium text-ink-900">{user?.email}</dd>
            </div>
            <div>
              <dt className="text-[12px] text-ink-500">Role</dt>
              <dd className="mt-0.5 text-[13px] font-medium text-ink-900">
                {humanize(user?.role ?? '')}
              </dd>
            </div>
            <div>
              <dt className="text-[12px] text-ink-500">Workspace</dt>
              <dd className="mt-0.5 text-[13px] font-medium text-ink-900">Storage Operations</dd>
            </div>
          </dl>
        </CardBody>
      </Card>

      <Card className="mt-4">
        <CardHeader
          title="Session"
          subtitle="Signing out clears your token from this browser."
        />
        <CardBody className="pt-4">
          <Button icon={<LogOut className="h-4 w-4" />} onClick={signOut}>
            Sign out
          </Button>
        </CardBody>
      </Card>
    </div>
  );
}
