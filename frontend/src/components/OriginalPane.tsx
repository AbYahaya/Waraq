/**
 * §3.7 mode 1/2/4 left pane — the source PDF scan.
 *
 * Thin wrapper around `<ScanViewer>` so the multi-pane primitive
 * receives a uniform `<X>Pane>` shape. Scan-pane click-to-jump is not
 * meaningful (PDFs aren't sentence-segmented in the viewer) so this
 * pane is a passive participant in the sync — it doesn't emit jump
 * events and it doesn't react to incoming jumps.
 */

import { ScanViewer, type ScanViewerProps } from "@/components/ScanViewer";

export function OriginalPane(props: ScanViewerProps): JSX.Element {
  return <ScanViewer {...props} />;
}
