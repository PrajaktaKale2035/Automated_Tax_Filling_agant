import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Eye } from "lucide-vue-next";
import { useSdui } from "@/composables/useSdui";
import { useAuthStore } from "@/stores/authStore";

export type Mode = "Novice" | "Intermediate" | "Expert" | "Accessibility";

interface ModeSwitcherProps {
  mode: Mode;
  onChange: (mode: Mode) => void;
}

const API_BASE = (import.meta as any).env?.VITE_API_BASE || "http://localhost:8000";

const ModeSwitcher = ({ mode, onChange }: ModeSwitcherProps) => {
  const { fetchFormSchema } = useSdui();
  const authStore = useAuthStore();

  const handleModeChange = async (newMode: Mode) => {
    // Update Pinia store
    authStore.setMode(newMode);
    // Notify parent
    onChange(newMode);
    // Persist to backend (fire-and-forget)
    try {
      await fetch(`${API_BASE}/api/users/profile`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preferred_mode: newMode }),
      });
    } catch {
      // Non-critical — ignore silently
    }
    // Refresh SDUI schema for new mode
    await fetchFormSchema();
  };

  return (
    <div className="flex items-center gap-3">
      <Label htmlFor="mode">Mode</Label>
      <Select value={mode} onValueChange={(v) => handleModeChange(v as Mode)}>
        <SelectTrigger id="mode" className="w-40">
          <SelectValue placeholder="Select mode" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="Novice">Novice</SelectItem>
          <SelectItem value="Intermediate">Intermediate</SelectItem>
          <SelectItem value="Expert">Expert</SelectItem>
          <SelectItem value="Accessibility">Accessibility-First</SelectItem>
        </SelectContent>
      </Select>
      <button
        onClick={() => handleModeChange("Accessibility")}
        class={`mode-btn ${mode === "Accessibility" ? "active" : ""}`}
        title="Accessibility Mode"
        aria-label="Switch to Accessibility Mode"
        aria-pressed={mode === "Accessibility"}
        style={{ display: "inline-flex", alignItems: "center", gap: "4px", padding: "4px 8px", borderRadius: "4px", border: "1px solid currentColor", cursor: "pointer" }}
      >
        <Eye size={16} aria-hidden="true" />
        <span>Access.</span>
      </button>
    </div>
  );
};

export default ModeSwitcher;
