import { redirect } from "next/navigation";

// Picking is switched off for 2026 (see PICKS_ENABLED in ui/picks-page.tsx);
// the same page now lives at /schedule.
export default function Page() {
  redirect("/schedule");
}
