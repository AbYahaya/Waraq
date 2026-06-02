import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { LayoutDashboard } from "lucide-react";

import { DeleteProjectDialog } from "@/components/DeleteProjectDialog";
import { DifficultyBadge } from "@/components/DifficultyBadge";
import { GuidedReviewPanel } from "@/components/GuidedReviewPanel";
import { OcrAutoRunPanel } from "@/components/OcrAutoRunPanel";
import { OcrExportDialog } from "@/components/OcrExportDialog";
import { PageList } from "@/components/PageList";
import { ReleaseGatePanel } from "@/components/ReleaseGatePanel";
import { TranslationExportDialog } from "@/components/TranslationExportDialog";
import { UploadPdfDialog } from "@/components/UploadPdfDialog";
import { Button } from "@/components/ui/button";
import { queries } from "@/lib/queries";
import type { Page } from "@/lib/types";
import { cn } from "@/lib/utils";

export interface ProjectWorkspaceSidebarProps {
  projectUuid: string;
  activePageUuid?: string;
  tone?: "dark" | "light";
  className?: string;
}

export function ProjectWorkspaceSidebar({
  projectUuid,
  activePageUuid,
  tone = "light",
  className,
}: ProjectWorkspaceSidebarProps): JSX.Element {
  const projectQ = useQuery(queries.project(projectUuid));
  const pagesQ = useQuery(queries.projectPages(projectUuid));
  const logicalPages = useMemo(() => dedupePagesByIndex(pagesQ.data ?? []), [pagesQ.data]);

  const [uploadOpen, setUploadOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [translateExportOpen, setTranslateExportOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const isDark = tone === "dark";

  return (
    <>
      <div
        className={cn(
          "flex min-h-0 flex-1 flex-col overflow-y-auto overscroll-contain",
          isDark
            ? "text-white"
            : "rounded-[2rem] border border-border/80 bg-card/95 shadow-sm",
          className,
        )}
      >
        <div
          className={cn(
            "shrink-0 px-3 py-3",
            isDark ? "border-b border-white/10" : "border-b border-border/80",
          )}
        >
          <div
            className={cn(
              "text-[10px] uppercase tracking-[0.22em]",
              isDark ? "text-white/55" : "text-muted-foreground",
            )}
          >
            Project
          </div>
          <div
            className={cn(
              "mt-1 truncate text-base font-semibold",
              isDark ? "text-white" : "text-[#1d221d]",
            )}
          >
            {projectQ.data?.name ?? "Loading…"}
          </div>
          <div className="mt-2">
            <DifficultyBadge scope="project" uuid={projectUuid} projectUuid={projectUuid} />
          </div>
          <Button
            size="sm"
            variant="outline"
            className={cn(
              "mt-3 w-full justify-start gap-2 rounded-xl px-2 text-xs",
              isDark && "bg-white text-foreground hover:bg-white/90",
            )}
            asChild
          >
            <Link to="/">
              <LayoutDashboard className="h-4 w-4" />
              Dashboard
            </Link>
          </Button>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <Button
              size="sm"
              variant="outline"
              className={cn(
                "min-w-0 rounded-xl px-2 text-xs",
                isDark && "bg-white text-foreground hover:bg-white/90",
              )}
              onClick={() => setUploadOpen(true)}
            >
              Upload
            </Button>
            <Button
              size="sm"
              variant="outline"
              className={cn(
                "min-w-0 rounded-xl px-2 text-xs",
                isDark && "bg-white text-foreground hover:bg-white/90",
              )}
              onClick={() => setExportOpen(true)}
            >
              OCR text
            </Button>
            <Button
              size="sm"
              className="col-span-2 min-w-0 rounded-xl px-2 text-xs"
              onClick={() => setTranslateExportOpen(true)}
            >
              Translate &amp; export
            </Button>
            <Button
              size="sm"
              variant="outline"
              className={cn(
                "min-w-0 rounded-xl px-2 text-xs",
                isDark && "bg-white text-foreground hover:bg-white/90",
              )}
              asChild
            >
              <Link to={`/projects/${projectUuid}/audit`}>Audit</Link>
            </Button>
            <Button
              size="sm"
              variant="outline"
              className={cn(
                "min-w-0 rounded-xl px-2 text-xs",
                isDark
                  ? "bg-white text-destructive hover:bg-white/90"
                  : "text-destructive border-destructive/40 hover:bg-destructive/10",
              )}
              onClick={() => setDeleteOpen(true)}
              title="Hide this project from your projects list. Server-side this is inactivation (H-5); data is preserved."
            >
              Delete
            </Button>
          </div>
          <div
            className={cn(
              "mt-2 rounded-2xl p-2",
              isDark ? "bg-white/95 text-foreground" : "bg-transparent p-0",
            )}
          >
            <OcrAutoRunPanel projectUuid={projectUuid} />
          </div>
        </div>

        <div className={cn("shrink-0", isDark && "bg-white/95 text-foreground")}>
          <ReleaseGatePanel projectUuid={projectUuid} />
        </div>
        <div className={cn("shrink-0", isDark && "bg-white/95 text-foreground")}>
          <GuidedReviewPanel projectUuid={projectUuid} />
        </div>
        <div
          className={cn(
            "min-h-[12rem] flex-1 overflow-hidden",
            isDark ? "border-t border-white/10 bg-white/95 text-foreground" : "border-t border-border/80",
          )}
        >
          <PageList projectUuid={projectUuid} activePageUuid={activePageUuid} />
        </div>
      </div>

      <UploadPdfDialog
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        projectUuid={projectUuid}
      />
      <OcrExportDialog
        open={exportOpen}
        onOpenChange={setExportOpen}
        projectUuid={projectUuid}
        defaultPageRange={logicalPages.map((p) => p.page_index)}
      />
      <TranslationExportDialog
        open={translateExportOpen}
        onOpenChange={setTranslateExportOpen}
        projectUuid={projectUuid}
        projectName={projectQ.data?.name ?? "Waraq Export"}
      />
      <DeleteProjectDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        projectUuid={projectUuid}
        projectName={projectQ.data?.name ?? "this project"}
      />
    </>
  );
}

function dedupePagesByIndex(pages: Page[]): Page[] {
  const seen = new Set<number>();
  return pages.filter((page) => {
    if (seen.has(page.page_index)) return false;
    seen.add(page.page_index);
    return true;
  });
}
