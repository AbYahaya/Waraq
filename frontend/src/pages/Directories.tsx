import { Link } from "react-router-dom";
import {
  BookMarked,
  Languages,
  Library,
  ListChecks,
  Palette,
  Quote,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const directories = [
  {
    title: "Glossary",
    icon: Languages,
    status: "Active in translation context",
    body:
      "Confirmed terminology is injected into translation prompts and exposed through diagnostics until a full glossary editor is added.",
    action: "Open diagnostics",
    to: "/diagnostics",
  },
  {
    title: "Terminology",
    icon: ListChecks,
    status: "Connected to style and consistency checks",
    body:
      "Project terminology, repeated source forms, and canon-backed decisions feed consistency review and export readiness.",
    action: "Review audit tools",
    to: "/diagnostics",
  },
  {
    title: "Religious formulas",
    icon: Quote,
    status: "Verification-backed",
    body:
      "Quran, hadith, and religious formula handling uses the reference stack so protected passages can show sources rather than becoming anonymous LLM output.",
    action: "Check references",
    to: "/diagnostics",
  },
  {
    title: "Reference / entity system",
    icon: BookMarked,
    status: "Available through review surfaces",
    body:
      "Named references, provenance objects, and source links are preserved for hover/click source disclosure in the workspace and exports.",
    action: "Open diagnostics",
    to: "/diagnostics",
  },
  {
    title: "Style Profile Option B",
    icon: Palette,
    status: "Project-level profile enabled",
    body:
      "Workspace, Book Preview, DOCX, and PDF export now read from the saved project style profile instead of disconnected one-off controls.",
    action: "Open a project",
    to: "/",
  },
];

export function DirectoriesPage(): JSX.Element {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <section className="rounded-[2rem] border border-border/80 bg-card p-6 shadow-sm">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#efe6d2] text-primary">
            <Library className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
              Canon archives
            </p>
            <h2 className="mt-2 text-3xl font-semibold text-[#1d221d]">
              Directories
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
              A single landing page for the reference systems that shape OCR,
              translation, review, and export. These are not mock panels: each
              card points to the current working surface while dedicated editors
              mature.
            </p>
          </div>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        {directories.map((item) => (
          <Card key={item.title} className="rounded-[1.75rem] border-border/80">
            <CardHeader>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <CardTitle className="text-xl text-[#1d221d]">{item.title}</CardTitle>
                  <p className="mt-2 text-xs font-medium uppercase tracking-[0.18em] text-primary">
                    {item.status}
                  </p>
                </div>
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#f3eee4] text-primary">
                  <item.icon className="h-5 w-5" />
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm leading-6 text-muted-foreground">{item.body}</p>
              <Button asChild variant="outline" className="rounded-xl">
                <Link to={item.to}>{item.action}</Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
