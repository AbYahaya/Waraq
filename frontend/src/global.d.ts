/**
 * Global namespace shims so `JSX.Element` works with React 19's new JSX
 * runtime under tsc strict (React 19 dropped the global JSX namespace by
 * default; we re-expose it via the React JSX namespace).
 */

import type { JSX as ReactJSX } from "react";

declare global {
  namespace JSX {
    type Element = ReactJSX.Element;
    type IntrinsicElements = ReactJSX.IntrinsicElements;
  }
}

export {};
