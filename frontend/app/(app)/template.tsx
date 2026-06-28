"use client";

/** Route transition: a gentle cross-fade on every navigation within the app (template.tsx re-mounts per
 *  route). Opacity-only, so it composes with each page's own slide-in entrances without double-translating. */
export default function Template({ children }: { children: React.ReactNode }) {
  return <div className="route-in">{children}</div>;
}
