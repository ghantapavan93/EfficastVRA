"use client";

import { CheckCircle2, Lightbulb, XCircle } from "lucide-react";
import { useKnowledge, useMe, useReviewKnowledge } from "@/lib/hooks";
import { Badge, Button, Chip } from "@/components/forge/primitives";
import { EmptyState, ErrorState, LoadingState } from "@/components/forge/states";
import type { KnowledgeCandidate } from "@/lib/types";

export default function KnowledgePage() {
  const { data, isLoading, isError, refetch } = useKnowledge(5000);
  const { data: me } = useMe();
  const review = useReviewKnowledge();

  if (isLoading) return <LoadingState label="Loading institutional knowledge" />;
  if (isError || !data) return <div className="p-6"><ErrorState message="Knowledge unavailable." onRetry={() => refetch()} /></div>;

  const canReview = me?.role === "quality_engineer" || me?.role === "plant_admin";
  const pending = data.knowledge.filter((k) => k.status === "PENDING_REVIEW");
  const curated = data.knowledge.filter((k) => k.status !== "PENDING_REVIEW");

  return (
    <div className="mx-auto max-w-3xl px-6 py-7">
      <div className="flex items-center gap-2">
        <Lightbulb className="h-5 w-5 text-agent" aria-hidden />
        <h1 className="text-2xl font-semibold tracking-tight text-ink-hi">Knowledge</h1>
        {data.pending > 0 && <Badge tone="pending">{data.pending} to review</Badge>}
      </div>
      <p className="mt-1 text-sm text-ink-mut">
        Lessons the agent captured from verified recoveries. A reviewer curates each one into
        institutional knowledge — turning a one-off fix into something the next shift (and sibling
        machines) can use. Only curated lessons appear as authoritative in Troubleshoot.
      </p>

      {data.knowledge.length === 0 ? (
        <div className="mt-6"><EmptyState title="No knowledge yet" description="When a recovery is verified, the agent drafts a candidate lesson here for review." icon={Lightbulb} /></div>
      ) : (
        <>
          {pending.length > 0 && (
            <section className="mt-6">
              <div className="label mb-2">Pending review</div>
              <div className="space-y-3">
                {pending.map((k) => (
                  <Card key={k.id} k={k}>
                    {canReview ? (
                      <div className="mt-3 flex items-center gap-2">
                        <Button size="sm" variant="approval" disabled={review.isPending}
                          onClick={() => review.mutate({ id: k.id, decision: "approve", reason: "validated for the fleet" })}>
                          <CheckCircle2 className="h-3.5 w-3.5" aria-hidden /> Approve
                        </Button>
                        <Button size="sm" variant="ghost" disabled={review.isPending}
                          onClick={() => review.mutate({ id: k.id, decision: "reject", reason: "not generalisable" })}>
                          <XCircle className="h-3.5 w-3.5" aria-hidden /> Reject
                        </Button>
                        <span className="text-[11px] text-ink-mut">You are curating this into authoritative guidance.</span>
                      </div>
                    ) : (
                      <p className="mt-3 text-[11px] text-ink-mut">Requires a {k.reviewer_role.replace(/_/g, " ")} to curate.</p>
                    )}
                  </Card>
                ))}
              </div>
            </section>
          )}

          {curated.length > 0 && (
            <section className="mt-6">
              <div className="label mb-2">Curated</div>
              <div className="space-y-3">
                {curated.map((k) => <Card key={k.id} k={k} />)}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}

function Card({ k, children }: { k: KnowledgeCandidate; children?: React.ReactNode }) {
  const tone = k.status === "APPROVED" ? "verified" : k.status === "REJECTED" ? "failure" : "pending";
  return (
    <div className="rounded-xl border border-line bg-surface-1 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-ink">{k.title}</span>
        <Badge tone={tone}>{k.status.replace(/_/g, " ").toLowerCase()}</Badge>
        {k.applicable_models?.map((m) => <Chip key={m}>{m}</Chip>)}
      </div>
      <p className="mt-1.5 text-sm text-ink">{k.lesson}</p>
      <div className="mt-2 grid gap-1 text-xs text-ink-mut sm:grid-cols-2">
        {k.failed_intervention && <span>Failed: {k.failed_intervention}</span>}
        {k.successful_intervention && <span>Worked: {k.successful_intervention}</span>}
      </div>
      {k.reviewed_by && (
        <p className="mt-2 text-[11px] text-ink-mut">
          Curated by {k.reviewed_by}{k.review_reason ? ` — “${k.review_reason}”` : ""}
        </p>
      )}
      {children}
    </div>
  );
}
