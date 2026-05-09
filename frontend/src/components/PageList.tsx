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
  ausstehend: "ausstehend",
  in_review: "in review",
  go: "go",
  go_with_warning: "go (warning)",
  no_go: "no-go",
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

  if (q.isLoading) {
    return <p className="text-sm text-muted-foreground p-3">Loading pages…</p>;
  }
  if (q.isError) {
    return <p className="text-sm text-destructive p-3">Failed to load pages.</p>;
  }
  if (!q.data || q.data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground p-3">
        No pages yet. Upload a PDF to get started.
      </p>
    );
  }

  return (
    <ul className="divide-y">
      {q.data.map((p) => {
        const isActive = p.page_uuid === activePageUuid;
        return (
          <li key={p.page_uuid}>
            <Link
              to={`/projects/${projectUuid}/pages/${p.page_uuid}`}
              className={cn(
                "block px-3 py-2 text-sm hover:bg-accent",
                isActive && "bg-accent",
              )}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium">Page {p.page_index}</span>
                <span className={cn("text-xs", STATUS_TONE[p.ocr_status])}>
                  {STATUS_LABEL[p.ocr_status]}
                </span>
              </div>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
