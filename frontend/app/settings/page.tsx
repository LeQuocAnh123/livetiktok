import { SettingsForm } from "@/components/settings/SettingsForm";
import { TestReply } from "@/components/settings/TestReply";
import { BackupRestore } from "@/components/settings/BackupRestore";
import { Separator } from "@/components/ui/separator";

export default function SettingsPage() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold">Settings</h2>
        <p className="text-sm text-muted-foreground">Configure bot behavior and test replies.</p>
      </div>

      <div>
        <h3 className="text-lg font-semibold mb-4">Bot Configuration</h3>
        <SettingsForm />
      </div>

      <Separator />

      <div>
        <h3 className="text-lg font-semibold mb-1">Test Reply</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Preview how the bot would respond to a comment. Does not send to TikTok.
        </p>
        <TestReply />
      </div>

      <Separator />

      <div>
        <h3 className="text-lg font-semibold mb-1">Backup & Restore</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Tải về bản sao database hoặc khôi phục từ file backup (.db).
        </p>
        <BackupRestore />
      </div>
    </div>
  );
}
