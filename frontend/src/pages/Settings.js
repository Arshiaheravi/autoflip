import { useState, useEffect } from 'react';
import { useAppStore } from '@/lib/store';
import { settingsApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import {
  Save, Bell, MessageSquare, Mail, Phone, Wrench, DollarSign,
  RefreshCw, TestTube, Shield, SlidersHorizontal,
} from 'lucide-react';

export default function SettingsPage() {
  const { settings, setSettings } = useAppStore();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [form, setForm] = useState({});

  useEffect(() => { fetchSettings(); }, []);

  const fetchSettings = async () => {
    try {
      const res = await settingsApi.get();
      setSettings(res.data);
      setForm(res.data);
    } catch (e) {
      console.error('Failed to fetch settings', e);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await settingsApi.update(form);
      setSettings(res.data);
      toast.success('Settings saved');
    } catch (e) {
      toast.error('Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const handleTestNotify = async () => {
    setTesting(true);
    try {
      const res = await settingsApi.testNotify();
      const results = res.data;
      const msgs = Object.entries(results).map(([ch, status]) => `${ch}: ${status}`);
      toast.info(msgs.join(' | '));
    } catch (e) {
      toast.error('Test failed');
    } finally {
      setTesting(false);
    }
  };

  const updateField = (field, value) => setForm({ ...form, [field]: value });
  const updateFilter = (field, value) => setForm({ ...form, alert_filters: { ...form.alert_filters, [field]: value } });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="settings-loading">
        <RefreshCw className="h-8 w-8 text-primary animate-spin" />
      </div>
    );
  }

  const filters = form.alert_filters || {};

  return (
    <div className="max-w-2xl space-y-8 animate-fade-in" data-testid="settings-page">
      {/* Alert Filters */}
      <Section icon={SlidersHorizontal} title="Alert Filters">
        <div className="grid grid-cols-2 gap-4">
          <FieldGroup label="Max Price ($)">
            <Input type="number" value={filters.max_price || ''} onChange={(e) => updateFilter('max_price', parseInt(e.target.value) || 0)} className="bg-background border-border/50" data-testid="setting-max-price" />
          </FieldGroup>
          <FieldGroup label="Max Mileage (km)">
            <Input type="number" value={filters.max_mileage || ''} onChange={(e) => updateFilter('max_mileage', parseInt(e.target.value) || 0)} className="bg-background border-border/50" data-testid="setting-max-mileage" />
          </FieldGroup>
          <FieldGroup label="Min Deal Score">
            <Input type="number" value={filters.min_deal_score || ''} onChange={(e) => updateFilter('min_deal_score', parseInt(e.target.value) || 0)} className="bg-background border-border/50" data-testid="setting-min-score" />
          </FieldGroup>
          <FieldGroup label="Min Profit ($)">
            <Input type="number" value={filters.min_profit_threshold || ''} onChange={(e) => updateFilter('min_profit_threshold', parseInt(e.target.value) || 0)} className="bg-background border-border/50" data-testid="setting-min-profit" />
          </FieldGroup>
        </div>
      </Section>

      {/* Notification Channels */}
      <Section icon={Bell} title="Notification Channels">
        <div className="space-y-4">
          <ToggleRow icon={MessageSquare} label="Telegram Notifications" checked={form.notifications_telegram || false} onChange={(v) => updateField('notifications_telegram', v)} testId="toggle-telegram" />
          <ToggleRow icon={Phone} label="SMS Notifications (Twilio)" checked={form.notifications_sms || false} onChange={(v) => updateField('notifications_sms', v)} testId="toggle-sms" />
          <ToggleRow icon={Mail} label="Email Notifications (SendGrid)" checked={form.notifications_email || false} onChange={(v) => updateField('notifications_email', v)} testId="toggle-email" />
        </div>
      </Section>

      {/* Telegram Config */}
      <Section icon={MessageSquare} title="Telegram Configuration">
        <div className="grid grid-cols-2 gap-4">
          <FieldGroup label="Bot Token">
            <Input type="password" value={form.telegram_bot_token || ''} onChange={(e) => updateField('telegram_bot_token', e.target.value)} className="bg-background border-border/50" placeholder="123456:ABC-DEF..." data-testid="setting-telegram-token" />
          </FieldGroup>
          <FieldGroup label="Chat ID">
            <Input value={form.telegram_chat_id || ''} onChange={(e) => updateField('telegram_chat_id', e.target.value)} className="bg-background border-border/50" placeholder="-1001234567890" data-testid="setting-telegram-chat-id" />
          </FieldGroup>
        </div>
      </Section>

      {/* Twilio Config */}
      <Section icon={Phone} title="Twilio SMS Configuration">
        <div className="grid grid-cols-2 gap-4">
          <FieldGroup label="Account SID">
            <Input type="password" value={form.twilio_sid || ''} onChange={(e) => updateField('twilio_sid', e.target.value)} className="bg-background border-border/50" data-testid="setting-twilio-sid" />
          </FieldGroup>
          <FieldGroup label="Auth Token">
            <Input type="password" value={form.twilio_token || ''} onChange={(e) => updateField('twilio_token', e.target.value)} className="bg-background border-border/50" data-testid="setting-twilio-token" />
          </FieldGroup>
          <FieldGroup label="From Number">
            <Input value={form.twilio_from || ''} onChange={(e) => updateField('twilio_from', e.target.value)} className="bg-background border-border/50" placeholder="+1234567890" data-testid="setting-twilio-from" />
          </FieldGroup>
          <FieldGroup label="To Number">
            <Input value={form.twilio_to || ''} onChange={(e) => updateField('twilio_to', e.target.value)} className="bg-background border-border/50" placeholder="+1234567890" data-testid="setting-twilio-to" />
          </FieldGroup>
        </div>
      </Section>

      {/* SendGrid Config */}
      <Section icon={Mail} title="SendGrid Email Configuration">
        <div className="grid grid-cols-2 gap-4">
          <FieldGroup label="API Key">
            <Input type="password" value={form.sendgrid_key || ''} onChange={(e) => updateField('sendgrid_key', e.target.value)} className="bg-background border-border/50" data-testid="setting-sendgrid-key" />
          </FieldGroup>
          <FieldGroup label="Recipient Email">
            <Input type="email" value={form.sendgrid_to_email || ''} onChange={(e) => updateField('sendgrid_to_email', e.target.value)} className="bg-background border-border/50" data-testid="setting-sendgrid-email" />
          </FieldGroup>
        </div>
      </Section>

      {/* Calculation Settings */}
      <Section icon={Wrench} title="Calculation Settings">
        <div className="space-y-4">
          <ToggleRow icon={Wrench} label="DIY Mode (zero labor cost)" checked={form.diy_mode || false} onChange={(v) => updateField('diy_mode', v)} testId="toggle-diy" />
          <div className="grid grid-cols-2 gap-4">
            <FieldGroup label="Shop Rate ($/hr)">
              <Input type="number" value={form.shop_rate || ''} onChange={(e) => updateField('shop_rate', parseFloat(e.target.value) || 110)} className="bg-background border-border/50" data-testid="setting-shop-rate" />
            </FieldGroup>
            <FieldGroup label="Available Capital ($)">
              <Input type="number" value={form.available_capital || ''} onChange={(e) => updateField('available_capital', parseFloat(e.target.value) || 0)} className="bg-background border-border/50" data-testid="setting-capital" />
            </FieldGroup>
          </div>
        </div>
      </Section>

      {/* Actions */}
      <div className="flex gap-3 pt-4 border-t border-border/30">
        <Button onClick={handleSave} disabled={saving} data-testid="save-settings-btn">
          {saving ? <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
          Save Settings
        </Button>
        <Button variant="outline" onClick={handleTestNotify} disabled={testing} className="border-border/50" data-testid="test-notify-btn">
          {testing ? <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> : <TestTube className="h-4 w-4 mr-2" />}
          Test Notifications
        </Button>
      </div>
    </div>
  );
}

function Section({ icon: Icon, title, children }) {
  return (
    <div className="space-y-4">
      <h3 className="text-base font-bold tracking-tight uppercase flex items-center gap-2" style={{ fontFamily: 'Barlow Condensed' }}>
        <Icon className="h-4 w-4 text-primary" />
        {title}
      </h3>
      <div className="bg-card border border-border/50 rounded-sm p-4">
        {children}
      </div>
    </div>
  );
}

function FieldGroup({ label, children }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs text-muted-foreground uppercase tracking-wider">{label}</Label>
      {children}
    </div>
  );
}

function ToggleRow({ icon: Icon, label, checked, onChange, testId }) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm">{label}</span>
      </div>
      <Switch checked={checked} onCheckedChange={onChange} data-testid={testId} />
    </div>
  );
}
