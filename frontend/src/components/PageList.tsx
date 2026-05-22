/**
 * Left-rail page navigation: lists every page in a project, shows the
 * OCR status badge, and highlights the active page.
 */

import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { queries } from "@/lib/queries";
import type { Page } from "@/lib/types";
import { cn } from "@/lib/utils";

const STATUS_LABEL: Record<Page["ocr_status"], string> = {
  ausstehend: "pending",
  in_review: "in review",
  go: "approved",
  go_with_warning: "approved with warning",
  no_go: "blocked",
};

const STATUS_TONE: Record<Page["ocr_status"], string> = {
  ausstehend: "text-muted-foreground",
  in_review: "text-blue-700",
  go: "text-emerald-700",
  go_with_warning: "text-amber-700",
  no_go: "text-destructive",
};

export interface PageListProps {
  projectUuid: string;
  activePageUuid?: string;
}

export function PageList({ projectUuid, activePageUuid }: PageListProps): JSX.Element {
  const q = useQuery(queries.projectPages(projectUuid));
  const pages = dedupePagesByIndex(q.data ?? []);

  if (q.isLoading) {
    return <p className="text-sm text-muted-foreground p-3">Loading pages…</p>;
  }
  if (q.isError) {
    return <p className="text-sm text-destructive p-3">Failed to load pages.</p>;
  }
  if (pages.length === 0) {
    return (
      <p className="text-sm text-muted-foreground p-3">
        No pages yet. Upload a PDF to get started.
      </p>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="shrink-0 border-b border-border/70 bg-card/95 px-3 py-2">
        <div className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
          Pages
        </div>
        <div className="text-xs text-muted-foreground">
          {pages.length} page{pages.length === 1 ? "" : "s"}
        </div>
      </div>
      <ul className="min-h-0 flex-1 space-y-1 overflow-y-auto px-2 py-2">
      {pages.map((p) => {
        const isActive = p.page_uuid === activePageUuid;
        return (
          <li key={p.page_uuid}>
            <Link
              to={`/projects/${projectUuid}/pages/${p.page_uuid}`}
              className={cn(
                "block rounded-xl border border-transparent px-2.5 py-2 text-sm transition hover:border-border/70 hover:bg-accent/40",
                isActive && "border-border/80 bg-accent/50 shadow-sm",
              )}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium">Page {p.page_index}</span>
                <span className={cn("text-[11px] font-medium", STATUS_TONE[p.ocr_status])}>
                  {STATUS_LABEL[p.ocr_status]}
                </span>
              </div>
            </Link>
          </li>
        );
      })}
      </ul>
    </div>
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
